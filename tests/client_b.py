import asyncio
from amqttrpc import AMQTTRPC, dispatcher


class ClientB(AMQTTRPC):
    @dispatcher.public
    async def hello(self, name):
        print('Got Hello request, sending back.')
        return 'Hello, {}'.format(name)


loop = asyncio.get_event_loop()
client_b = ClientB(client_uid='client_b')
print(
    loop.run_until_complete(
        client_b.process_messages()))
