from zeroconf import ServiceBrowser, Zeroconf
import asyncio

# class Airfoil(object):
PROTOCOL_VERSION = b"com.rogueamoeba.protocol.slipstreamremote\nmajorversion=1,minorversion=5\n";
remote_protocol_ok = b"majorversion=1,minorversion=5"
remote_ok = b"OK\n$"
subscribe = b"212;{\"request\":\"subscribe\",\"requestID\":\"3\",\"data\":{\"notifications\":[\"remoteControlChangedRequest\",\"speakerConnectedChanged\",\"speakerListChanged\",\"speakerNameChanged\",\"speakerPasswordChanged\",\"speakerVolumeChanged\"]}}"

ip = "192.168.0.50"
port = 63336






class Listener(object):
    name = "_slipstreamrem._tcp.local."
    # name = "_http._tcp.local."

    def __init__(self):
        self.zeroconf = Zeroconf()
        self.browser = ServiceBrowser(self.zeroconf, self.name, self)
        self.airfoils = {}

    def remove_service(self, zeroconf, type, name):
        print(f"Service {name} removed")
        del self.airfoils[name]

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        ip = '.'.join(str(i) for i in info.address)
        port = info.port
        display_name = name.strip(self.name).lower()
        print(f"Service '{display_name}' added with ip {ip} and port {port}")
        # self.airfoils[name] = Airfoil(name, display_name, ip, port)

    def close(self):
        self.zeroconf.close()


listener = Listener()
try:
    input("Press enter to exit...\n\n")
finally:
    listener.close()