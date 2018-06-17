import asyncio, time
from collections import deque

class Airfoil(asyncio.Protocol):
    protocol_hello = b"com.rogueamoeba.protocol.slipstreamremote\nmajorversion=1,minorversion=5\nOK\n"
    protocol = "majorversion=1,minorversion=5"
    ok = "OK"
    subscribe = b"""212;{"request":"subscribe","requestID":"3","data":{"notifications":["remoteControlChangedRequest","speakerConnectedChanged","speakerListChanged","speakerNameChanged","speakerPasswordChanged","speakerVolumeChanged"]}}"""
    ip = "192.168.0.50"
    port = 53438

    def __init__(self, loop):
        self._buffer = bytearray()
        self.loop = loop
        self.loop.run_until_complete(asyncio.ensure_future(self.print_buffer()))
        # self.print_buffer()

    def print_buffer(self):
        while True:
            time.sleep(1)
            print(self._buffer[-128:])

    def connection_made(self, transport):
        transport.write(Airfoil.protocol_hello + Airfoil.subscribe)
        # self.handshake(transport)

    def data_received(self, data):
        self._buffer += data

    def connection_lost(self, exc):
        print('The server closed the connection')
        print('Stop the event loop')
        self.loop.stop()

def start():
    loop = asyncio.get_event_loop()
    try:
        coro = loop.create_connection(lambda: Airfoil(loop), Airfoil.ip, Airfoil.port)
        loop.run_until_complete(coro)
        # loop.run_forever()
    finally:
        loop.close()





# async def connect(loop):
    # coro = await
    # w.write(Airfoil.protocol_hello)
    # print('got here 1')
    # result = await r.read(1)
    # print('got here 2')
    # result = result.decode("latin1")
    # print(result)
    # w.close()
    # await result
    # if Airfoil.protocol not in result:
    #     raise ValueError(f'Invalid protocol: {result}')
    # result = await r.read(1024)
    # result = result.decode("latin1")
    # print(result)
    # w.write(Airfoil.subscribe)
    # result = await r.read(128)
    # result = result.decode("latin1")
    # print(result)


# def start():
#     loop = asyncio.get_event_loop()
#     coro = asyncio.open_connection(Airfoil.ip, Airfoil.port)
#     r, w = loop.run_until_complete(coro)
#     w.write(Airfoil.protocol_hello)
#     # w.write_eof()
#     msg = loop.run_until_complete(asyncio.ensure_future(r.read(128)))
#     print(msg.decode())
#     w.write(Airfoil.subscribe)
#     msg = loop.run_until_complete(asyncio.ensure_future(r.read(4096)))
#     print(msg.decode())
#
#     w.close()
#     coro.close()
#     loop.close()

if __name__ == '__main__':
    # pass
    start()

