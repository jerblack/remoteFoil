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
import sys, time, json
from req.utils import nones, bools, print_table
from airfoil import OFF, ON, MIDDLE
from airfoil_finder import AirfoilFinder
args = [arg.lstrip('-\/\\').lower() for arg in sys.argv]

DEFAULT_TIMEOUT = 3
DEFAULT_SECONDS = 3
DEFAULT_TICKS = 10
DEFAULT_UNMUTE_VOLUME = 1.0
ACTION_LOG_WIDTH = 45

HELP = ['help', 'h', '?']
WAIT = ['sleep', 'wait']
PLAY = ['play', 'pause', 'play_pause', 'unpause']
NEXT = ['skip', 'next', 'next_track']
LAST = ['prev', 'last', 'back', 'prev_track', 'last_track']
CURR_SOURCE = ['source', 'current_source', 'current', 'src']
SOURCES = ['sources', 'all_sources', 'srcs']

CONNECT = ['on', 'yes', 'true', 'connect', 'enable', 'enabled']
DISCONNECT = ['off', 'no', 'false', 'disconnect', 'disable', 'disabled']
TOGGLE = ['toggle', 'reset', 'cycle']
MUTE = ['mute', 'silence', 'silent', 'quiet']
UNMUTE = ['unmute']
VOLUME = ['volume', 'level', 'vol']
FADE = ['fade', 'ramp', 'transition', 'timed']
ALL_SPEAKERS = ['speakers', 'all']
TIMEOUT = ['timeout', 't', 'limit']
INCLUDE_DISCONNECTED = ['id', 'include_disconnected', 'disconnected']

TABLE = ['table', 'grid']
JSON = ['json']
LIST = ['list', 'sequence']

AIRFOIL_NAME = ['name', 'n']
AIRFOIL_IP = ['ip', 'i']
ALL_ARGS = HELP + PLAY + NEXT + LAST + CURR_SOURCE + SOURCES + CONNECT + DISCONNECT + TOGGLE + TIMEOUT + \
           MUTE + UNMUTE + VOLUME + FADE + ALL_SPEAKERS + AIRFOIL_IP + AIRFOIL_NAME + WAIT
ALL_ACTIONS = PLAY + NEXT + LAST + CURR_SOURCE + SOURCES + CONNECT + DISCONNECT + TOGGLE + MUTE + \
              UNMUTE + VOLUME + FADE + WAIT

help_text = {
     'fade':
        'usage fade: fade <volume> [<seconds: default 3.0> [<ticks: default 10>]]\n'
        '\t# current volume does not matter. fade will transition from whatever the current level is to\n'
        '\t#  the volume level you specify, even between multiple speakers at differing start volumes. \n'
        '\t# fade speakers to 0.2 over 3 seconds in 10 ticks\n'
        '\t  fade 0.2\n'
        '\t# fade speakers to 0.95 over 10 seconds in 10 ticks \n'
        '\t  fade 0.95 10\n'
        '\t# fade speakers to 0.5 over 15.25 seconds in 50 ticks\n'
        '\t  fade 50% 15.25 50\n',
     'speakers_cmds':
        '{} can be used with one, more than one, or all speakers\n'
        ' # Set speaker named \'Bedroom speaker\ to 50% volume\n'
        f'  {args[0]} bedroom_speaker volume 50%\n'
        ' #   volume in particular does not need to be called with the volume action\n'
        f'    {args[0]} \'living room home\' 20%\n' 
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
        '\t   home_living mute\n',
     'specifying_speaker':
        'for any command that operates on speakers you can specify either 1, more than 1, or all speakers.\n'
        '- commands and speaker names are not case sensitive\n'
        '- when specifying a speaker name with spaces you can keep them or replace them with underscores.\n'
        '  you can use any of the following to indicate a speaker named \'Office Speaker\'\n'
        '  "office speaker", office\ speaker, office_speaker, speaker_office, office, speaker'
        '- you only need to specify as many words as are required to uniquely identify the speaker from \n'
        '  other speakers. The first speaker to match the given keywords will be returned, and there are no\n'
        '  guarantees on which one will be returned first if there are multiple matches.\n'
        '  word order does not matter.\n'
        f'- you can also specify a speaker by its id, which you can see by running \'{args[0]} all table\''
        f''
}


class AirfoilCli:
    def __init__(self):
        self.airfoil, self.airfoil_ip, self.airfoil_name, self.finder, self.source, self.speakers = nones(6)
        self.volume, self.json, self.table, self.silent, self.help, self.wait_time = nones(6)
        self.print_mode = 'table'  # or 'list' or 'json'
        self.include_disconnected = False
        self.seconds, self.ticks = DEFAULT_SECONDS, DEFAULT_TICKS
        self.timeout = DEFAULT_TIMEOUT
        self.actions = []
        self.parse_cmd_line()
        self.send_cmds()

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
        print('  <Run with h or help to see usage information.>')
        print('Looking for instances of Airfoil on the network. Press ctrl-c to exit.')
        self.finder = AirfoilFinder()
        timeout = self.timeout
        try:
            while True:
                if timeout:
                    timeout -= 1
                    if timeout <= 0:
                        print('\r     \r', end='', flush=True)
                        return
                    else:
                        if self.timeout > 4:
                            print(f"\r{timeout} ", end='', flush=True)
                time.sleep(1)
        except KeyboardInterrupt:
            return

    def wait(self, verbose=True):
        if verbose:
            count = self.wait_time
            start = count = int(count) if not count % 1 else float(count)
            print('\r' + f'waiting {start} seconds: {count}'.ljust(ACTION_LOG_WIDTH),
                  end='', flush=True)
            while count > 0:
                wait = count if count < 1 else 1
                print('\r' + f'waiting {start} seconds: {int(count)}'.ljust(ACTION_LOG_WIDTH),
                      end='', flush=True)
                time.sleep(wait)
                count -= 1
            print('\r' + f'finished {start} second wait'.ljust(ACTION_LOG_WIDTH+1),
                  end='', flush=True)
        else:
            time.sleep(self.wait_time)

    def play(self):
        return self.airfoil.play_pause()

    def next(self):
        return self.airfoil.next_track()

    def last(self):
        return self.airfoil.last_track()

    def current_source(self, source=None):
        s = source if source else self.airfoil.get_current_source()
        if self.print_mode == 'json':
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
        if self.print_mode == 'table':
            print_table(header, row, sizes)
        else:
            for k, v in zip(header, row):
                print(f' {k}: {v}')

    def get_sources(self):
        # print all sources
        sources = self.airfoil.get_sources()
        if self.print_mode == 'json':
            print(json.dumps([dict(s._asdict()) for s in sources]))

        sizes = (3, 30, 60, 50)
        headers = ['#', 'name', 'keywords', 'id']
        rows = [(str(i+1).zfill(2), s.name, str(s.keywords), s.id) for i, s in enumerate(sources)]
        if self.print_mode == 'table':
            print_table(headers, rows, sizes)
        else:
            for r in rows:
                print(f'(#{r[0]})\n'
                      f' name: {r[1]}\n'
                      f' keywords: {r[2]}\n'
                      f' id: {r[3]}')

    def set_source(self):
        self.source = self.airfoil.set_source(id=self.source.id)

    def connect(self):
        self.speakers = self.airfoil.connect_some(ids=[s.id for s in self.speakers])

    def disconnect(self):
        self.speakers = self.airfoil.disconnect_some(ids=[s.id for s in self.speakers])

    def toggle(self):
        self.speakers = self.airfoil.toggle_some(ids=[s.id for s in self.speakers])

    def mute(self):
        self.speakers = self.airfoil.mute_some(ids=[s.id for s in self.speakers])

    def unmute(self):
        self.speakers = self.airfoil.unmute_some(ids=[s.id for s in self.speakers],
                                                 default_volume=self.volume if self.volume else 1.0)

    def set_volume(self):
        self.speakers = self.airfoil.set_volume_some(self.volume, ids=[s.id for s in self.speakers])

    def fade(self):
        self.speakers = self.airfoil.fade_some(self.volume, seconds=self.seconds, ticks=self.ticks,
                                               ids=[s.id for s in self.speakers])

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

    def get_param(self, index, default, num_params=1):
        params = []
        if type(default) not in [list, tuple]:
            default = [default]
        for i in range(num_params, 0, -1):
            try:
                params.append(args[index+i])
                args.pop(index + i)
            except IndexError:
                d = default[i-1]
                raise d if issubclass(type(d), Exception) else params.append(d)
        args.pop(index)
        return params[0] if len(params) == 1 else params[::-1]

    def parse_volume(self, volume):
        self.volume = self.airfoil._parse_volume(volume)
        return self.volume

    def print_speakers(self):
        if self.print_mode == 'json':
            print(json.dumps([s._asdict() for s in self.speakers]))
            return

        headers = ['#', 'name', 'type', 'volume', 'connected', 'password', 'keywords', 'id']
        sizes = (10, 30, 20, 6, 9, 10, 40, 70)
        fields = lambda n, s: [str(n+1), s.name, s.type, str(round(s.volume, 2)), bools(s.connected),
                               bools(s.password), str(s.keywords), s.id]
        rows = [fields(n, s) for n, s in enumerate(self.speakers)]
        if self.print_mode == 'table':
            print_table(headers, rows, sizes)
        else:
            for row in rows:
                for h, r in zip(headers, row):
                    if h == headers[0]:
                        print(f'({h}{r})')
                    else:
                        print(f' {h}: {r}')




        # print(self.speakers)
        # for s in self.speakers()

    def help(self, topics, status=0):
        if type(topics) is str:
            topics = [topics]
        for topic in topics:
            print(help_text[topic])
        sys.exit(status=status)

    def parse_cmd_line(self):
        """
        Parse flags, speakers, sources, and actions received in cmd line
        :return:
        """
        def in_args(check):
            for arg in args:
                if arg in check:
                    return args.index(arg)
            return None

        if in_args(HELP):   # if 'help' in cmd, show help topics for all actions specified in cmd
            topics = [arg for arg in args if arg in ALL_ACTIONS]
            return self.help(topics)

        if len(args) == 1:  # show airfoils on network with no arguments
            self.show_airfoils()
            return

        def get_timeout():
            timeout = in_args(TIMEOUT)
            if timeout:
                try:
                    self.timeout = int(self.get_param(timeout, [ValueError('timeout value is required')]))
                    if self.timeout:
                        print(f'Starting with timeout set: {self.timeout}')
                    else:
                        print('Starting with timeout disabled.')
                except ValueError:
                    print(f'Error: \'{args[timeout]}\' requires a positive number as an argument.')
                    return False
            else:
                self.timeout = DEFAULT_TIMEOUT

        def get_disconnected():
            include_disconnected = in_args(INCLUDE_DISCONNECTED)
            if include_disconnected:
                args.pop(include_disconnected)
                self.include_disconnected = True

        def get_airfoil():
            airfoil_name = in_args(AIRFOIL_NAME)
            if airfoil_name:
                try:
                    self.airfoil_name = self.get_param(airfoil_name, [ValueError('parameter requires name')])
                except ValueError:
                    print(f'Error: \'{args[airfoil_name]}\' requires a name.')

            airfoil_ip = in_args(AIRFOIL_IP)
            if airfoil_ip:
                try:
                    self.airfoil_ip = self.get_param(airfoil_ip, [ValueError('parameter requires ip')])
                except ValueError:
                    print(f'Error: \'{args[airfoil_ip]}\' requires an ip.')
            self.get_airfoil(in_args(AIRFOIL_NAME), in_args(AIRFOIL_IP))

        def get_print_mode():
            table = in_args(TABLE)
            json = in_args(JSON)
            list = in_args(LIST)
            if [bool(table), bool(json), bool(list)].count(True) > 1:  # fail usefully
                if table:
                    print('Specify only one print method from these options: table, list, json. Showing table.')
                    self.print_mode = 'table'
                    args.pop(table)
                elif list:
                    print('Specify only one print method from these options: table, list, json. Showing list.')
                    self.print_mode = 'list'

                if list:
                    args.pop(list)
                if json:
                    args.pop(json)
            else:
                if table:
                    self.print_mode = 'table'
                    args.pop(table)
                if json:
                    self.print_mode = 'json'
                    args.pop(json)
                if list:
                    self.print_mode = 'list'
                    args.pop(list)

        def get_speakers():
            requested_speakers = []
            for arg in args[1:]:
                if arg in ALL_ACTIONS:
                    break
                if arg in ALL_SPEAKERS:
                    self.speakers = 'all'
                try:
                    self.parse_volume(arg)
                    self.actions.append(['volume', float(self.volume)])
                    return
                except ValueError:
                    arg = arg.replace('_', ' ')
                    found = self.airfoil.find_speaker(unknown=arg)
                    if found:
                        requested_speakers.append(found)
                    elif arg not in ALL_SPEAKERS:
                        print(f'Error: \'{arg}\' is not a recognized speaker or action ')
                        sys.exit(1)
            if self.speakers in ALL_SPEAKERS:
                    speakers = self.airfoil.get_speakers()
                    self.speakers = [s for s in speakers if s.connected or self.include_disconnected]
                    if requested_speakers:
                        self.speakers += requested_speakers

        def get_actions():
            action = []
            for arg in args:
                if arg in ALL_ACTIONS:
                    if action:
                        self.actions.append(action)
                    action = [arg]
                elif action:
                    action.append(arg)
            self.actions.append(action) if action else None

        get_timeout()           # parse timeout flag from cmd
        get_disconnected()      # parse include_disconnected flag from cmd
        get_airfoil()           # parse airfoil name or ip flags from cmd
        get_print_mode()        # parse print mode from cmd
        get_speakers()          # parse target speakers from cmd
        get_actions()           # parse actions in cmd into separate actions

    def send_cmds(self):
        def too_many_params(action, max):
            if len(action) > max:
                print(f'Error: cmd \'{" ".join([str(a) for a in action])}\' '
                      f'has too many arguments')
                self.help(action[0])

        for action in self.actions:
            cmd = action[0]
            action_str = " ".join([str(a) for a in action])
            log_entry = f'Starting command: \'{action_str}\''.ljust(ACTION_LOG_WIDTH)
            print(log_entry, end='', flush=True)
            if cmd in WAIT:
                wait_error = f"{cmd} requires a positive numeric value to indicate number of" \
                             f" seconds to wait."
                if len(action) == 1:
                    print(wait_error)
                    self.help(cmd)
                try:
                    self.wait_time = float(action[1])
                except ValueError:
                    print(wait_error)
                    self.help(cmd)
                self.wait()
            if cmd in PLAY+NEXT+LAST+MUTE+CONNECT+DISCONNECT+TOGGLE:
                too_many_params(action, 1)
            if cmd in UNMUTE+VOLUME+CURR_SOURCE:
                too_many_params(action, 2)
            if cmd in PLAY+NEXT+LAST: # all return boolean
                if cmd in PLAY:
                    self.play()
                if cmd in NEXT:
                    self.next()
                if cmd in LAST:
                    self.last()
                self.current_source()
            if cmd in MUTE:
                self.mute()
            if cmd in UNMUTE:
                if len(action) > 1:
                    self.parse_volume(action[1])
                self.unmute()
            if cmd in TOGGLE:
                self.toggle()
            if cmd in CONNECT:
                self.connect()
            if cmd in DISCONNECT:
                self.disconnect()
            if cmd in VOLUME:
                if len(action) == 1:
                    self._level_error('volume')
                    self.help(cmd)
                self.parse_volume(action[1])
                self.set_volume()
            if cmd in CURR_SOURCE:
                if len(action) == 1:
                    self.current_source()
                else:
                    if self.parse_source(action[1]):
                        self.set_source()
                    else:
                        print(f'\'{action[1]}\' was not recognized as a source name')
                        self.help(cmd)
            if cmd in SOURCES:
                self.get_sources()
            if cmd in FADE:
                too_many_params(action, 4)
                if len(action) == 1:
                    self._level_error('fade')
                    self.help('fade')
                    sys.exit(1, status=1)
                try:
                    self.parse_volume(action[1])
                except ValueError:
                    print(f'Error in action: {action_str}\n'
                          f' \'{action[1]}\' is not a valid value for volume')
                    self.help(cmd, status=1)
                if len(action) > 2:
                    try:
                        self.seconds = abs(float(action[2]))
                    except ValueError:
                        print(f'Error in action: {action_str}\n'
                              f' \'{action[2]}\' is not a valid value for seconds parameter.')
                        self.help(cmd, status=1)
                if len(action) == 4:
                    try:
                        self.ticks = abs(int(action[3]))
                    except ValueError:
                        print(f'Error: \'{action[3]}\' is not a valid value for ticks parameter. '
                              f'Ticks must be a whole number.')
                        self.help(cmd, status=1)
                self.fade()
            print('[complete]')
        if self.source:
            self.current_source(source=self.source)
        if self.speakers:
            self.print_speakers()


if __name__ == '__main__':
    try:
        a = AirfoilCli()
    except KeyboardInterrupt:
        pass
    # print(a.__dict__)
