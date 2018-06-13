PROTOCOL_VERSION = b"com.rogueamoeba.protocol.slipstreamremote\nmajorversion=1,minorversion=5\n";
remote_protocol_ok = b"majorversion=1,minorversion=5"
remote_ok = b"OK\n$"
subscribe = b"""212;{"request":"subscribe","requestID":"3","data":{"notifications":["remoteControlChangedRequest","speakerConnectedChanged","speakerListChanged","speakerNameChanged","speakerPasswordChanged","speakerVolumeChanged"]}}"""

ip = "192.168.0.50"
port=52770

import nclib
nc = nclib.Netcat((ip, port), verbose=True)
nc.send(PROTOCOL_VERSION)
if remote_protocol_ok in nc.recv():
    nc.send(remote_ok)
    if remote_ok in nc.recv():
        nc.send(subscribe)
        print(nc.recv())