import asyncio

class Airfoil(object):
    protocol_hello = b"com.rogueamoeba.protocol.slipstreamremote\n" \
                       b"majorversion=1,minorversion=5\n";
    protocol = "majorversion=1,minorversion=5"
    ok = "OK"
    subscribe = b"""212;{"request":"subscribe","requestID":"3","data":{"notifications":["remoteControlChangedRequest","speakerConnectedChanged","speakerListChanged","speakerNameChanged","speakerPasswordChanged","speakerVolumeChanged"]}}"""

    def __init__(self, ip=None, port=None):
        self.ip = "192.168.0.50"
        self.port = 52770
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.ensure_future(self.connect()))
        loop.close()

    async def connect(self):
        r, w = await asyncio.open_connection(self.ip, self.port)
        w.write(Airfoil.protocol_hello)
        result = await r.read(1024)
        result = result.decode("latin1")
        print(result)
        if Airfoil.protocol not in result:
            raise ValueError(f'Invalid protocol: {result}')
        result = await r.read(1024)
        result = result.decode("latin1")
        print(result)
        w.write(Airfoil.subscribe)
        result = await r.read(128)
        result = result.decode("latin1")
        print(result)





Airfoil()