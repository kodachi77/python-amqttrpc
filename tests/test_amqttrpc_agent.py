import asyncio
import logging
import os
from amqttrpc import AMQTTRPC, dispatcher

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('amqtt').setLevel(level=logging.INFO)


class TestAMQTTRPC(AMQTTRPC):
    @dispatcher.public
    async def test(name=''):
        print('Hello')
        return 'Hello, {}'.format(name)


loop = asyncio.get_event_loop()
server = TestAMQTTRPC(client_uid='test', loop=loop)
loop.run_until_complete(server.process_messages())
