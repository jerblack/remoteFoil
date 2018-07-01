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
import sys, time, re, json
from airfoil import nones, bools, print_table, OFF, ON, MIDDLE
from airfoil_finder import AirfoilFinder
args = [re.sub(r'^[-\/\\]*', '', arg).lower() for arg in sys.argv]
args = [re.sub(r'[\'\"]', '', arg) for arg in args]

HELP = ['help', 'h', '?']
PLAY = ['play', 'pause', 'play_pause', 'unpause']
NEXT = ['skip', 'next', 'next_track']
LAST = ['prev', 'last', 'back', 'prev_track', 'last_track']
CURR_SOURCE = ['source', 'current_source', 'current', 'src', 'sauce']

CONNECT = ['on', 'yes', 'true', 'connect', 'enable', 'enabled']
DISCONNECT = ['off', 'no', 'false', 'disconnect', 'disable', 'disabled']
TOGGLE = ['toggle', 'reset', 'cycle']
MUTE = ['mute', 'silence', 'silent', 'quiet']
UNMUTE = ['unmute']
VOLUME = ['volume', 'level']
FADE = ['fade', 'ramp', 'transition', 'timed']
ALL_SPEAKERS = ['speakers', 'all']
TIMEOUT = ['timeout', 't', 'wait', 'limit']
TABLE = ['table', 'grid']

AIRFOIL_NAME = ['name', 'n']
AIRFOIL_IP = ['ip', 'i']
ALL_CMDS = HELP + PLAY + NEXT + LAST + CURR_SOURCE + CONNECT + DISCONNECT + TOGGLE + TIMEOUT + \
           MUTE + UNMUTE + VOLUME + FADE + ALL_SPEAKERS + AIRFOIL_IP + AIRFOIL_NAME


help_text = {'fade':
                'usage fade: fade <volume> [<seconds: default 3.0> [<ticks: default 10>]]\n'
                '\t# current volume does not matter. fade will transition from whatever the current level is to'
                '\t#  the volume level you specify, even between multiple speakers at differing start volumes. '
                '\t# fade speakers to 0.2 over 3 seconds in 10 ticks\n'
                '\t  fade 0.2\n'
                '\t# fade speakers to 0.95 over 10 seconds in 10 ticks \n'
                '\t  fade 0.95 10\n'
                '\t# fade speakers to 0.5 over 15.25 seconds in 50 ticks\n'
                '\t  fade 50% 15.25 50',
             'speakers_cmds':
                '{} can be used with one, more than one, or all speakers\n'
                ' # Set speaker named \'Bedroom speaker\ to 50% volume\n'
                f'  {args[0]} bedroom_speaker volume 50%\n'
                ' #   volume in particular does not need to be called with the volume action\n'
                f'    {args[0]} \'living room home\' 20%' 
                ' # Fade \'Bedroom speaker\' and \'Office speaker\' to 0.8 over 5 seconds\n'
                f'  {args[0]} bedroom_speaker,office_speaker fade 0.8 5\n'
                ' # Mute all connected speakers (all of these work)\n' 
                f'  {args[0]} mute\n'
                f'  {args[0]} all mute\n'
                f'  {args[0]} everywhere mute\n',
             'volume':
                'usage volume:volume <volume>\n'
                '             <volume>  # volume keyword is optional for volume action\n'
                '\t# Set speaker named \'Garage AirPlay\' to full volume\n'
                '\t   garage_airplay volume 1\n'
                '\t   \'Garage AIRPLAY\' 100%\n'
                '\t   \'airplay garage\' full\n',
             'volume_levels':
                '<volume> can be specified as any of the following:\n'
                '\t- a number from 0.0 to 1.0 with up to 8 digits of precision\n'
                '\t- a percentage from 0% to 100%\n'
                '\t- any of the following will set volume to 1.0\n'
                f"{ON}\n"
                '\t- any of the following will set volume to 0.0\n'
                f"{OFF}\n"
                '\t- any of the following will set volume to 0.5\n'
                f"{MIDDLE}\n"
                '\t- any volume between 1 and 100 will be treated as a percentage\n'
                '\t- any volume < 0 will be rounded up to 0\n'
                '\t- any volume > 100 will be rounded to 1\n',
             'mute':
                'usage mute: mute\n'
                '\t# mute speaker named \'Living Room Google Home\'\n'
                '\t   home_living mute',
             'specifying_speaker':
                'for any command that operates on speakers you can specify either 1, more than 1, or all speakers.\n'
                '- commands and speaker names are not case sensitive\n'
                '- when specifying a speaker name with spaces you can keep them or replace them with underscores.\n'
                '  you can use any of the following to indicate a speaker named \'Office Speaker\'\n'
                '  "office speaker", office\ speaker, office_speaker, speaker_office, office, speaker'
                '- you only need to specify as many words as are required to uniquely identify the speaker from \n'
                '  other speakers. The first speaker to match the given keywords will be returned, and there are no\n'
                '  guarantees on which one will be returned first if there are multiple matches.\n'
                '  word order does not matter.'
                f'- you can also specify a speaker by its id, which you can see by running \'{args[0]} all table\''
                f''




}


class AirfoilCli:
    def __init__(self):
        self.airfoil, self.airfoil_ip, self.airfoil_name, self.finder, self.source, self.speakers = nones(6)
        self.volume, self.json, self.table = nones(3)
        self.seconds, self.ticks = 3, 10
        self.timeout = 3
        result = self.parse_args()
        # print(result)

    def _level_error(self, action):
        print(action, 'requires an end volume in the following formats: A number between 0 and 1 inclusive',
              'with up to 8 digits after the decimal point, or a percentage. values greater than 1 or less than',
              '0 will be constrained to valid values. valid values for volume include 0, 1, 0.75432111, 35%, 100%')


    def get_airfoil(self, name=None, ip=None):
        if name:
            try:
                self.airfoil_name = args[name + 1]
                args.pop(name + 1)
                args.pop(name)
                self.airfoil = AirfoilFinder.get_airfoil_by_name(self.airfoil_name)
            except TimeoutError:
                print('Timed out waiting for airfoil instance with name "' + self.airfoil_name + '".')
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
                print('Timed out waiting for airfoil instance with ip "' + self.airfoil_ip + '".')
                sys.exit(1)
            except IndexError:
                print('Please specify an IPv4 address after -i|--ip')
                sys.exit(1)
        else:
            try:
                self.airfoil = AirfoilFinder.get_first_airfoil()
            except TimeoutError:
                print('Timed out waiting for an airfoil instance to appear on the network.')
                sys.exit(1)

    def show_airfoils(self):
        print('Looking for instances of Airfoil on the network. Press ctrl-c to exit.')
        self.finder = AirfoilFinder()
        timeout = self.timeout
        try:
            while True:
                if timeout:
                    timeout -= 1
                    if timeout <= 0:
                        sys.stdout.write('\r     \r')
                        sys.stdout.flush()
                        return
                    else:
                        if self.timeout > 4:
                            sys.stdout.write(f"\r{timeout} ")
                            sys.stdout.flush()

                time.sleep(1)
        except KeyboardInterrupt:
            return

    def play(self):
        return self.airfoil.play_pause()

    def next(self):
        return self.airfoil.next_track()

    def last(self):
        return self.airfoil.last_track()

    def current_source(self, source=None):
        s = source if source else self.airfoil.get_current_source()
        if self.json:
            print(json.dumps(dict(s._asdict())))
            return

        header = ['current source', 'supports remote control', 'has track data']
        sizes = [15, 23, 14]
        has_meta = any([s.track_title, s.track_artist, s.track_album])
        row = [s.source_name, bools(s.source_controllable), bools(s.source_has_track_metadata and has_meta)]
        if s.source_has_track_metadata and has_meta:
            header += ['track', 'artist', 'album']
            sizes += [20, 20, 20]
            title = s.track_title if s.track_title else ''
            artist = s.track_artist if s.track_artist else ''
            album = s.track_album if s.track_album else ''
            row += [title, artist, album]
        if self.table:
            print_table(header, row, sizes)
        else:
            for k, v in zip(header, row):
                print(f' {k}: {v}')

    def get_sources(self):
        # print all sources
        sources = self.airfoil.get_sources()
        if self.json:
            print(json.dumps([dict(s._asdict()) for s in sources]))
            return

        sizes = (3, 30, 60, 50)
        headers = ['#', 'name', 'keywords', 'id']
        rows = [(str(i+1).zfill(2), s.name, str(s.keywords), s.id) for i, s in enumerate(sources)]
        if self.table:
            print_table(headers, rows, sizes)
        else:
            for r in rows:
                print(f'(#{r[0]})\n'
                      f' name: {r[1]}\n'
                      f' keywords: {r[2]}\n'
                      f' id: {r[3]}')

    def set_source(self):
        result = self.airfoil.set_source(id=self.source.id)
        self.current_source(source=result)

    # def get_speakers(self):
    #     speakers = self.airfoil.get_speakers()
    #     if self.json:
    #         print(json.dumps([dict(s._asdict()) for s in speakers]))
    #         return
    #     print(speakers)

    def connect(self):
        if self.speakers in ALL_SPEAKERS:
            self.speakers = self.airfoil.connect_all()
        else:
            self.speakers = self.airfoil.connect_some(ids=[s.id for s in self.speakers])
        self.print_speakers()

    def disconnect(self):
        if self.speakers in ALL_SPEAKERS:
            self.speakers = self.airfoil.disconnect_all()
        else:
            self.speakers = self.airfoil.disconnect_some(ids=[s.id for s in self.speakers])
        self.print_speakers()

    def toggle(self):
        if self.speakers in ALL_SPEAKERS:
            self.speakers =self.airfoil.toggle_all()
        else:
            self.speakers = self.airfoil.toggle_some(ids=[s.id for s in self.speakers])
        self.print_speakers()

    def mute(self):
        if self.speakers in ALL_SPEAKERS:
            self.speakers = self.airfoil.mute_all()
        else:
            self.speakers = self.airfoil.mute_some(ids=[s.id for s in self.speakers])
        self.print_speakers()

    def unmute(self):
        if self.speakers in ALL_SPEAKERS:
            self.speakers = self.airfoil.unmute_all(
                                default_volume=self.volume if self.volume else 1.0)
        else:
            self.speakers = self.airfoil.unmute_some(
                                ids=[s.id for s in self.speakers],
                                default_volume=self.volume if self.volume else 1.0)
        self.print_speakers()

    def set_volume(self):
        if self.speakers in ALL_SPEAKERS:
            self.speakers = self.airfoil.set_volume_all(self.volume)
        else:
            self.speakers = self.airfoil.set_volume_some(
                                self.volume, ids=[s.id for s in self.speakers])
        self.print_speakers()

    def fade(self):
        if self.speakers in ALL_SPEAKERS:
            self.speakers = self.airfoil.fade_all(self.volume, seconds=self.seconds, ticks=self.ticks)
        else:
            self.speakers = self.airfoil.fade_some(self.volume, seconds=self.seconds, ticks=self.ticks,
                                                   ids=[s.id for s in self.speakers])
        self.print_speakers()


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
        if speaker in ALL_SPEAKERS:
            found = 'all'
        else:
            speaker = speaker.replace('_', ' ')
            speakers = speaker.split(',')
            found = [self.airfoil.find_speaker(unknown=s) for s in speakers if s]
            found = [f for f in found if f is not None]
        self.speakers = found
        return found

    def parse_volume(self, volume):
        self.volume = self.airfoil._parse_volume(volume)
        return self.volume

    def print_speakers(self):
        if self.json:
            print(json.dumps([s._asdict() for s in self.speakers]))
            return

        headers = ['#', 'name', 'type', 'volume', 'connected', 'password', 'keywords', 'id']
        sizes = (10, 30, 20, 6, 9, 10, 40, 30)
        fields = lambda n, s: [str(n+1), s.name, s.type, str(round(s.volume, 2)), bools(s.connected),
                               bools(s.password), str(s.keywords), s.id]
        rows = [fields(n, s) for n, s in enumerate(self.speakers)]
        if self.table:
            print_table(headers, rows, sizes)
        else:
            # TODO make table default output

            for row in rows:
                for h, r in zip(headers, row):
                    if h == headers[0]:
                        print(f'({h}{r})')
                    else:
                        print(f' {h}: {r}')




        # print(self.speakers)
        # for s in self.speakers()


    def help(self):
        print(__doc__)
        sys.exit(0)

    def parse_args(self):
        def in_args(check):
            for arg in args:
                if arg in check:
                    return args.index(arg)
            return None

        timeout = in_args(TIMEOUT)
        if timeout:
            try:
                self.timeout = int(args[timeout+1])
                args.pop(timeout+1)
                args.pop(timeout)
                if self.timeout:
                    print(f'Starting with timeout set: {self.timeout}')
                else:
                    print('Starting with timeout disabled.')
            except (IndexError, ValueError):
                print(f'Error: \'{args[timeout]}\' requires a positive number as an argument.')
                return False
        table = in_args(TABLE)
        json = in_args(['json'])
        if table and json:
            print('Can\'t ask for table and json at the same time. Showing json.')
            table = None
        if table:
            self.table = True
            args.pop(table)
        if json:
            self.json = True
            args.pop(json)

        if len(args) == 1:
            print('<Run with -h or --help to see usage.>')
            self.show_airfoils()
            return True

        self.get_airfoil(in_args(AIRFOIL_NAME), in_args(AIRFOIL_IP))

        if in_args(HELP):
            return self.help()
        if in_args(PLAY):
            return self.play()
        if in_args(NEXT):
            return self.next()
        if in_args(LAST):
            return self.last()

        action = args[1]
        if action in MUTE+UNMUTE+TOGGLE+CONNECT+DISCONNECT+VOLUME+FADE:
            self.speakers = 'all'
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

        self.parse_speaker(args[1])
        if self.speakers:
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
                if action in FADE:
                    try:
                        self.parse_volume(args[3])
                        try:
                            self.seconds = float(args[4])
                            try:
                                self.ticks = int(args[5])
                            except ValueError:
                                print(f'\'{args[5]}\' is an invalid number of ticks.')
                                sys.exit(1)
                            except IndexError:
                                pass
                        except ValueError:
                            print(f'\'{args[4]}\' is an invalid number of seconds. '
                                  f'Please provide a positive numeric value')
                            return
                        except IndexError:
                            pass
                        return self.fade()
                    except ValueError:
                        self._level_error('fade')
                        sys.exit(1)
                    except IndexError:
                        print(help_text['fade'])
                        return
            else:
                if self.speakers in ALL_SPEAKERS:
                    self.speakers = self.airfoil.get_speakers()
                self.print_speakers()
                return

        print(f'no action recognized with the name \'{args[1]}\'')


if __name__ == '__main__':
    a = AirfoilCli()
    # print(a.__dict__)
