import logging

logger = logging.getLogger(__name__)


class RPCProxy(object):

    def __init__(self, client, destination, one_way=False):
        self.client = client
        self.reply_topic = 'rpc/{}/{}/reply'.format(client.client_uid, destination)
        self.destination = destination
        self.one_way = one_way

    def __del__(self):
        if self.client._connected_state.is_set() and self.reply_topic in self.client.subscriptions:
            self.client.subscriptions.remove(self.reply_topic)
            self.client.loop.create_task(
                self.client.unsubscribe([self.reply_topic])
            )

    def __getattr__(self, name):
        proxy_func = lambda *args, **kwargs: self.client._call(
            self.destination,
            name,
            args,
            kwargs,
            one_way=self.one_way
        )

        return proxy_func
