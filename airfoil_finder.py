from airfoil import Airfoil
from zeroconf import ServiceBrowser, Zeroconf
import time


class AirfoilFinder(object):
    domain = "_slipstreamrem._tcp.local."

    def __init__(self, on_add=None, on_remove=None):
        self.zeroconf = Zeroconf()
        self.browser = ServiceBrowser(self.zeroconf, self.domain, self)
        self.airfoils = {}
        self.on_add = on_add
        self.on_remove = on_remove

    def remove_service(self, zeroconf, type, name):
        print(f"Service {name} removed")
        print(f'type: {type}')
        if name in self.airfoils:
            del self.airfoils[name]
        if self.on_remove:
            self.on_remove(name)

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        ip = '.'.join(str(i) for i in info.address)
        port = info.port
        name = name.split('.')[0].lower()
        airfoil = Airfoil(ip, port, name)
        self.airfoils[name] = airfoil
        print(f"Airfoil instance '{name}' found at {ip}:{port}")
        if self.on_add:
            self.on_add(name, ip, port)

    def close(self):
        self.zeroconf.close()

    @staticmethod
    def get_first_airfoil(timeout=10) -> Airfoil:
        """
        find and return an instance of Airfoil on the network.
            the first instance that is found will be returned.
        timeout defaults to 10 seconds but you can pass a longer timeout value or set timeout=None to disable.
        :param timeout: None or int number of seconds to wait before timing out
        :return: instance of Airfoil
        """
        finder = AirfoilFinder()
        if timeout is not None:
            while not finder.airfoils:
                timeout -= 0.25
                time.sleep(0.25 if timeout >= 0.25 else timeout)
                if timeout <= 0:
                    finder.close()
                    raise TimeoutError('timed out looking for Airfoil instances on the network'
                                    '\n\t\t\t  set a longer timeout or set timeout=None to avoid this.')
        for airfoil in finder.airfoils.values():
            finder.close()
            return airfoil

    @staticmethod
    def get_airfoil_by_name(name, timeout=10):
        """
        find and return an instance of Airfoil on the network that matches the given name.
        timeout defaults to 10 seconds but you can pass a longer timeout value or set timeout=None to disable.
        :param name: name is usually the hostname of the computer.
        :param timeout: None or int number of seconds to wait before timing out
        :return:
        """
        finder = AirfoilFinder()
        while name not in finder.airfoils:
            time.sleep(0.25 if timeout >= 0.25 else timeout)
            if timeout is not None:
                timeout -= 0.25
                if timeout <= 0:
                    finder.close()
                    raise TimeoutError('timed out looking for Airfoil instances on the network'
                                    '\n\t\t\t  set a longer timeout or set timeout=None to avoid this.')
        finder.close()
        return finder.airfoils[name]

    @staticmethod
    def get_airfoil_by_ip(ip, timeout=10):
        """
        find and return an instance of Airfoil on the network that matches the given ipv4 address.
        timeout defaults to 10 seconds but you can pass a longer timeout value or set timeout=None to disable.
        :param ip: The ipv4 address as a string. (eg. '192.168.0.72')
        :param timeout: None or int number of seconds to wait before timing out
        :return:
        """
        finder = AirfoilFinder()
        while True:
            for airfoil in finder.airfoils.values():
                if airfoil.ip == ip:
                    finder.close()
                    return airfoil

            time.sleep(0.25 if timeout >= 0.25 else timeout)
            if timeout is not None:
                timeout -= 0.25
                if timeout <= 0:
                    finder.close()
                    raise TimeoutError('timed out looking for Airfoil instances on the network'
                                    '\n\t\t\t  set a longer timeout or set timeout=None to avoid this.')



# a = AirfoilFinder.get_airfoil_by_ip('192.168.0.51')
a = AirfoilFinder.get_first_airfoil()
# a = AirfoilFinder.get_airfoil_by_name('server')
# a.fade_all(0.3, 4)
# time.sleep(2)
# a.fade_all(1.0, 6)
# print(a.play_pause())