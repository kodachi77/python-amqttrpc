# code was forked from https://github.com/litnimax/python-mqttrpc and updated to use amqttrpc
import asyncio
import json
import logging
import os
import re
import uuid
from asyncio import Queue
from asyncio.locks import Event

from amqtt.client import MQTTClient
from amqtt.mqtt.constants import QOS_2
from tinyrpc.exc import RPCError
from tinyrpc.protocols.jsonrpc import JSONRPCProtocol

from .dispatcher import AsyncRPCDispatcher
from .rpcproxy import RPCProxy

logger = logging.getLogger('amqtt_rpc')

dispatcher = AsyncRPCDispatcher()

MQTT_REPLY_TIMEOUT = float(os.environ.get('MQTT_REPLY_TIMEOUT', 5))
CLIENT_UID = os.environ.get('CLIENT_UID', str(uuid.getnode()))
MQTT_URL = os.environ.get('MQTT_URL', 'mqtt://localhost')


class AMQTTRPC(MQTTClient):
    client_uid = CLIENT_UID
    cleansession = True
    mqtt_reply_timeout = MQTT_REPLY_TIMEOUT
    mqtt_url = MQTT_URL
    request_count = 0
    rpc_replies = {}
    replied = Event()  # This event is triggered every time a new reply has come.
    subscriptions = []  # We hold a list of our subscriptions not to subscribe to

    # every request to the same client.

    def __init__(self, mqtt_url=None, client_uid=None, loop=None, config=None):
        if not loop:
            loop = asyncio.get_event_loop()
        self.loop = loop
        self.protocol = JSONRPCProtocol()
        self.dispatcher = dispatcher
        self.config = config
        if mqtt_url:
            self.mqtt_url = mqtt_url
        if client_uid:
            self.client_uid = client_uid
        super(AMQTTRPC, self).__init__(client_id=self.client_uid, loop=loop,
                                       config=self.config)
        if os.name != 'nt':
            import signal
            for signame in ('SIGINT', 'SIGTERM'):
                self.loop.add_signal_handler(getattr(signal, signame),
                                             lambda: asyncio.ensure_future(self.stop()))

        logger.info('Client {} initialized'.format(self.client_uid))

    async def stop(self):
        logger.info('Stopping mqttrpc...')
        # Check subscriptions
        if self._connected_state.is_set():
            await self.unsubscribe(self.subscriptions)
            await self.disconnect()
        tasks = [task for task in asyncio.Task.all_tasks() if task is not
                 asyncio.tasks.Task.current_task()]
        list(map(lambda task: task.cancel(), tasks))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug('Finished cancelling tasks, result: {}'.format(results))
        self.loop.stop()

    async def process_messages(self):
        self.mqtt_url = self.config.get('broker', {}).get('uri', self.mqtt_url)
        logger.info('Connecting to {}'.format(self.mqtt_url))
        await self.connect(self.mqtt_url, cleansession=self.cleansession)
        logger.info('Connected.')
        await self.subscribe([
            ('rpc/{}/+'.format(self.client_uid), QOS_2),
        ])
        logger.debug('Starting process messages.')
        while True:
            try:
                self.loop.create_task(self.process_message(
                    await self.deliver_message()))
            except asyncio.CancelledError:
                return

    async def process_message(self, message):
        logger.debug('Message at topic {}'.format(message.topic))

        if re.search(r"^rpc/(\w+)/(\w+)$", message.topic):
            # RPC request
            logger.debug('RPC request at {}'.format(message.topic))
            _, _, context = message.topic.split('/')
            data_str = message.data.decode()
            await self.receive_rpc_request(context, data_str)

        elif re.search(r"^rpc/(\w+)/(\w+)/reply$", message.topic):
            # RPC reply
            logger.debug('RPC reply at {}'.format(message.topic))
            _, _, context, _ = message.topic.split('/')
            data_str = message.data.decode()
            waiting_replies = self.rpc_replies.get(message.topic)
            if not waiting_replies:
                logger.warning(
                    'Got an unexpected RPC reply from {}: {}'.format(
                        message.topic, data_str))
            else:
                try:
                    data_js = json.loads(data_str)
                except json.decoder.JSONDecodeError:
                    logger.error('RPC reply bad json data: {}'.format(data_str))
                else:
                    request_id = data_js.get('id')
                    if request_id not in waiting_replies.keys():
                        logger.warning(
                            'Got a reply from {} to bad request id: {}'.format(
                                message.topic, data_str))
                    else:
                        # Finally matched the request by id
                        logger.debug(
                            'Waiting reply found for request {}'.format(
                                request_id))
                        await waiting_replies[request_id].put(data_str)
        else:
            logger.debug('Passing to on_message handler')
            await self.on_message(message)

    async def on_message(self, message):
        # Override it to implement other handlers.
        logger.debug('Not implemented')

    async def receive_rpc_request(self, context, data):
        logger.debug('Request: {}'.format(data))
        self.request_count += 1
        if type(data) != str:
            data = json.dumps(data)

        message = data

        async def handle_message(context, message):
            try:
                request = self.protocol.parse_request(message)
            except RPCError as e:
                response = e.error_respond()
            else:
                # Hack to add first params as self
                if self not in request.args:
                    request.args.insert(0, self)
                response = await self.dispatcher.dispatch(
                    request,
                    getattr(self.protocol, '_caller', None)
                )

                # send reply
            if response is not None:
                result = response.serialize()
                logger.debug('RPC reply to {}: {}'.format(context, result))
                self.loop.create_task(
                    self.publish('rpc/{}/{}/reply'.format(self.client_uid, context), result)
                )

        await handle_message(context, message)

    def get_proxy_for(self, destination, one_way=False):
        return RPCProxy(self, destination, one_way)

    async def _send_and_handle_reply(self, destination, req, one_way, no_exception=False):
        # Convert to bytes and send to destination
        if one_way:
            # We do not need a reply it's a notification call
            await self.publish(
                'rpc/{}/{}'.format(destination, self.client_uid),
                req.serialize().encode())
            return

        # We need a reply
        reply_topic = ('rpc/{}/{}/reply'.format(destination, self.client_uid))
        self.rpc_replies.setdefault(reply_topic, {})[req.unique_id] = Queue()
        if reply_topic not in self.subscriptions:
            logger.debug('Adding subscrption to reply topic {}'.format(reply_topic))
            self.subscriptions.append(reply_topic)
            await self.subscribe([(reply_topic, QOS_2)])
            logger.debug('Subscribed to reply topic {}'.format(reply_topic))
        else:
            logger.debug('Already subscribed for topic {}'.format(reply_topic))
        await self.publish('rpc/{}/{}'.format(destination, self.client_uid),
                           req.serialize())
        logger.debug(
            'Published request id {} to {}'.format(req.unique_id, destination))
        try:
            reply_data = await asyncio.wait_for(
                self.rpc_replies[reply_topic][req.unique_id].get(),
                self.mqtt_reply_timeout)
            self.rpc_replies[reply_topic][req.unique_id].task_done()

        except asyncio.TimeoutError:
            del self.rpc_replies[reply_topic][req.unique_id]
            raise RPCError(
                'Reply Timeout, topic {}, id {}, method {}, args {}, kwargs {}'.format(
                    reply_topic, req.unique_id, req.method, req.args, req.kwargs))

        else:
            # We got a reply, handle it.
            logger.debug('Got a reply for request id: {}'.format(
                req.unique_id))
            rpc_response = self.protocol.parse_reply(reply_data)
            del self.rpc_replies[reply_topic][req.unique_id]
            # Check that there is no RPC errors.
            if not no_exception and hasattr(rpc_response, 'error'):
                raise RPCError("Error calling remote procedure: %s" % rpc_response.error)
            return rpc_response

    async def _call(self, destination, method, args, kwargs, one_way=False):
        req = self.protocol.create_request(method, args, kwargs, one_way)
        rep = await self._send_and_handle_reply(destination, req, one_way)
        if one_way:
            return
        return getattr(rep, 'result', None)
