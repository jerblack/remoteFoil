"""
    cli (<speaker name,id, or keywords> | speakers | all) ...speaker_cmd...
    cli speaker (<speaker name,id, or keywords> | speakers | all) ...speaker_cmd...
    cli speakers  <speaker_name>,<speaker_name>,<speaker_name> ...speaker_cmd...
    cli speakers  <speaker_id>,<speaker_id>,<speaker_id> ...speaker_cmd...
    cli speakers [<speaker_keywords>],[<speaker_keywords>],[<speaker_keywords>] ...speaker_cmd...


    cli <speaker> (connect | enable | on | true | yes) -> connect
    cli <speaker> (disconnect | disable | off | false | no) -> disconnect
    cli <speaker> (toggle | reset | cycle) -> toggle
    cli <speaker> (mute | silence | silent | quiet) -> mute
    cli <speaker> unmute VOL
        allowed_flags [-d|--default_volume VOL]
    cli <speaker> VOL
        allowed-flags: (volume | level) [-l|--level VOL]
    cli <speaker> (fade | ramp | transition) VOL
    cli <speaker> (fade | ramp | transition) VOL SEC
    cli <speaker> (fade | ramp | transition) VOL SEC TICKS
        [-l|--level VOL][-v|--volume VOL][-c|--sec SEC][-t|--ticks]



    cli <speaker> (play | pause | play_pause)
    cli (play | pause | play_pause)
    cli <speaker> (skip | next | next_track)
    cli (skip | next | next_track)
    cli <speaker> (prev, last, back, prev_track, last_track)
    cli (prev, last, back, prev_track, last_track)

    cli (source | current_source) -> get_current_source
    cli sources -> get all sources
    cli source (<source name, id, or keywords)
    -------------------------------------------
    cli ...cmd... --> act on first airfoil we find
    cli -n|--name airfoil_name ...cmd... --> act on airfoil by name
    cli -i|--ip airfoil_ip ...cmd... --> act on airfoil by ip
    flag value pair position in cmd does not matter as long as
    value follows flag


    cli (<speaker name,id, or keywords> | speakers | all | comma separated list of names, ids or
     [keywords])  -> return state of selected speakers
    cli (<speaker name,id, or keywords> | speakers | all | comma separated list of names, ids or
     [keywords]) ...speaker_cmd...
    cli speaker connect
    cli speaker disconnect
    cli speaker toggle
    cli speaker mute
    cli speaker unmute [DEFAULT_VOL]
    cli speaker VOL
    cli speaker volume VOL
    cli speaker fade VOL [SEC [TICKS]]
    cli (play | next | last)
    cli source
    cli sources
    cli source (name, id, or keywords of source)"
"""
import sys, time
from airfoil_finder import AirfoilFinder
args = [arg.lower() for arg in sys.argv]

PLAY = ['play', 'pause', 'play_pause']
NEXT = ['skip', 'next', 'next_track']
LAST = ['prev', 'last', 'back', 'prev_track', 'last_track']
CURR_SOURCE = ['source', 'current_source', 'current']

CONNECT = ['on', 'yes', 'true', 'connect', 'enable', 'enabled']
DISCONNECT = ['off', 'no', 'false', 'disconnect', 'disable', 'disabled']
TOGGLE = ['toggle', 'reset', 'cycle']
MUTE = ['mute', 'silence', 'silent', 'quiet']
UNMUTE = ['unmute']
VOLUME = ['volume', 'level']
FADE = ['fade', 'ramp', 'transition']
SPEAKERS = ['speakers', 'all']

AIRFOIL_NAME = ['--name', '-n', '-name', '--n']
AIRFOIL_IP = ['--ip', '-ip', '-i', '--i']


class AirfoilCli:
    def __init__(self):
        self.airfoil_name = None
        self.airfoil_ip = None
        self.source = None
        self.speakers = None
        self.volume = None
        self.seconds = None
        self.ticks = None
        self.airfoil = None
        self.finder = None
        result = self.parse_args()
        print(result)

    def _bools(self, bool_check):
        return 'yes' if bool_check else 'no'

    def _level_error(self, action):
        print(f'{action} requires an end volume in the following formats: A number between 0 and 1 inclusive '
              'with up to 8 digits after the decimal point, or a percentage. values greater than 1 or less than '
              '0 will be constrained to valid values. valid values for volume include 0, 1, 0.75432111, 35%, 100%')

    def _airfoil_cmd(self, name, cmd, speaker=None):
        caller = sys._getframe(1).f_code.co_name
        if self.airfoil:
            if not speaker:
                return cmd(self.airfoil)
            else:
                match = None
                try:
                    match = self.airfoil.find_speaker(id=speaker)
                except ValueError:
                    try:
                        match = self.airfoil.find_speaker(name=speaker)
                    except ValueError:
                        keywords = self.airfoil.get_keywords(speaker)
                        try:
                            match = self.airfoil.find_speaker(keywords=keywords)
                        except ValueError:
                            pass
                if match:
                    return cmd(self.airfoil, match)
                else:
                    print(name, caller, f'No speaker found with name, id, or keywords: \'{speaker}\'')
                    return False
        else:
            print(name, caller, f'No airfoil instance found with name \'{name}\'')
            return False

    def get_airfoil(self, name=None, ip=None):
        if name:
            try:
                self.airfoil_name = args[name + 1]
                args.pop(name + 1)
                args.pop(name)
                self.airfoil = AirfoilFinder.get_airfoil_by_name(self.airfoil_name)
            except TimeoutError:
                print(f'Timed out waiting for airfoil instance with name \'{self.airfoil_name}\'.')
                sys.exit(1)
            except IndexError:
                print('Please specify a name after -n|--name.')
                sys.exit(1)
        elif ip:
            try:
                self.airfoil_ip = args[ip + 1]
                args.pop(ip + 1)
                args.pop(ip)
                self.airfoil = AirfoilFinder.get_airfoil_by_ip(self.airfoil_ip)
            except TimeoutError:
                print(f'Timed out waiting for airfoil instance with ip \'{self.airfoil_ip}\'.')
                sys.exit(1)
            except IndexError:
                print('Please specify an IPv4 address after -i|--ip')
                sys.exit(1)
        else:
            try:
                self.airfoil = AirfoilFinder.get_first_airfoil()
            except TimeoutError:
                print(f'Timed out waiting for an airfoil instance to appear on the network.')
                sys.exit(1)

    def get_airfoils(self):
        print('Watching for instances of airfoil on the network. Press ctrl-c to exit.')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(0)

    def play(self):
        return self.airfoil.play_pause()

    def next(self):
        return self.airfoil.next_track()

    def last(self):
        return self.airfoil.last_track()

    def current_source(self):
        s = self.airfoil.get_current_source()
        print(f'[current source]\n'
              f' name: {s.source_name()}\n'
              f' supports remote control: {self._bools(s.source_controllable)}\n'
              f' has track information: {self._bools(s.source_has_track_metadata)}')
        if s.source_has_track_metadata:
            print(f'\n track: {s.track_title}\n'
                  f' artist: {s.track_artist}\n'
                  f' album: {s.track_album}')

    def get_sources(self):
        # return all sources
        sources = self.airfoil.get_sources()
        for i, s in enumerate(sources):
            i = str(i).zfill(2)
            print(f'[source {i}]\n'
                  f' name: {s.name}\n'
                  f' keywords: {s.keywords}\n'
                  f' id: {s.id}')


    def set_source(self):
        result = self.airfoil.set_source(id=self.source.id)
        print(result)

    def get_speakers(self):
        return self.airfoil.get_speakers()

    def connect(self):
        pass

    def disconnect(self):
        pass

    def toggle(self):
        pass

    def mute(self):
        pass

    def unmute(self):
        pass

    def set_volume(self):
        pass

    def parse_source(self, source):
        match = None
        try:
            match = self.airfoil.find_source(name=source)
        except ValueError:
            try:
                match = self.airfoil.find_source(id=source)
            except ValueError:
                keywords = self.airfoil.get_keywords(source)
                try:
                    match = self.airfoil.find_source(keywords=keywords)
                except ValueError:
                    pass
        if match:
            self.source = match
            return True
        return False

    def parse_speaker(self, speaker):
        self.speakers = speaker
        return True

    def parse_volume(self, volume):
        self.volume = self.airfoil._parse_volume(volume)
        return self.volume

    def parse_args(self):
        def in_args(check):
            for arg in args:
                if arg in check:
                    return args.index(arg)
            return None

        if len(args) == 1:
            print('Run with --help to see usage.')
            self.get_airfoils()
            sys.exit(1)

        self.get_airfoil(in_args(AIRFOIL_NAME), in_args(AIRFOIL_IP))

        if in_args(PLAY):
            return self.play()
        if in_args(NEXT):
            return self.next()
        if in_args(LAST):
            return self.last()

        action = args[1]
        if action in MUTE:
            return self.mute()
        if action in UNMUTE:
            return self.unmute()
        if action in TOGGLE:
            return self.toggle()
        if action in CONNECT:
            return self.connect()
        if action in DISCONNECT:
            return self.disconnect()

        if action in VOLUME:
            try:
                self.parse_volume(args[2])
                return self.set_volume()
            except IndexError or ValueError:
                self._level_error('volume')
                sys.exit(1)

        try:
            self.parse_volume(action)
            return self.set_volume()
        except ValueError:
            pass

        src_idx = in_args(CURR_SOURCE)
        if src_idx:
            try:
                if self.parse_source(args[src_idx + 1]):
                    return self.set_source()
            except IndexError:
                return self.current_source()
        if in_args(['sources']):
            return self.get_sources()

        speaker = self.parse_speaker(args[1])
        if speaker:
            if len(args) > 2:
                action = args[2]
                if action in TOGGLE:
                    return self.toggle()
                if action in CONNECT:
                    return self.connect()
                if action in DISCONNECT:
                    return self.disconnect()
                if action in MUTE:
                    return self.mute()
                if action in UNMUTE:
                    if len(args) > 3:  # default volume is optional
                        try:
                            self.parse_volume(args[3])
                        except ValueError:
                            self._level_error('unmute')
                            sys.exit(1)
                    return self.unmute()
                if action in VOLUME:
                    try:
                        self.parse_volume(args[3])
                        return self.set_volume()
                    except IndexError or ValueError:
                        self._level_error('volume')
                        sys.exit(1)
            else:
                return self.get_speakers()
        return f'no action recognized with the name \'{args[1]}\''


if __name__ == '__main__':
    a = AirfoilCli()
    print(a.__dict__)
