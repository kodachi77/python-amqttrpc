import asyncio
import logging
from amqttrpc import AMQTTRPC, dispatcher

logging.basicConfig(level=logging.INFO)
logging.getLogger('amqtt').setLevel(level=logging.INFO)


class TestAMQTTRPC(AMQTTRPC):
    @dispatcher.public
    async def test(self, name):
        return 'Hello, {}'.format(name)

    async def run_test(self, name):
        await self._connected_state.wait()
        proxy = self.get_proxy_for('test')
        try:
            res = await proxy.test(name)
            print(res)
            return res
        except Exception as e:
            print(e)



loop = asyncio.get_event_loop()
server = TestAMQTTRPC(client_uid='test', loop=loop)
loop.create_task(server.process_messages())
assert 'Hello, World' == loop.run_until_complete(server.run_test('World'))
