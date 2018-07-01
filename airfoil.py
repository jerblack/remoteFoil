import socket, json, random, sys, time, copy
from collections import namedtuple

ON = ['full', 'on', 'unmute', 'enable', 'enabled', 'true']
OFF = ['none', 'off', 'mute', 'disable', 'disabled', 'false']
MIDDLE = ['half', 'mid', 'middle']

class Airfoil(object):
    def __init__(self, ip, port, name):
        self.ip = ip
        self.port = port
        self.name = name
        self.sources = []
        self.speakers = []
        self.muted_speakers = {}
        self.current_source = None

    def _connect(self, sock):
        hello = b"com.rogueamoeba.protocol.slipstreamremote\nmajorversion=1,minorversion=5\nOK\n"
        acceptable_version = "majorversion=1,minorversion=5"
        sock.connect((self.ip, self.port))
        sock.send(hello)
        data = sock.recv(128)
        return acceptable_version in data.decode()

    def _get_responses(self, cmd):
        max_bytes = 4096
        with socket.socket() as sock:
            if self._connect(sock):
                sock.send(cmd)
                while True:
                    num_bytes = ''
                    while True:
                        data = sock.recv(1)
                        data = data.decode()
                        if data == ';':
                            num_bytes = int(num_bytes)
                            break
                        if data.isdigit():
                            num_bytes += data
                    buffer = b''
                    while num_bytes > 1:
                        get_bytes = max_bytes if num_bytes > max_bytes else num_bytes - 1
                        data = sock.recv(get_bytes)
                        buffer += data
                        num_bytes = num_bytes - len(data)
                    buffer += b'}'
                    yield json.loads(buffer)

    def _create_cmd(self, base_cmd):
        request_id = str(random.randint(1, 1000))
        base_cmd['requestID'] = request_id
        cmd = str(base_cmd).replace(': ', ':').replace(', ', ',')
        byte_cmd = bytes(f'{len(cmd)};{cmd}\r\n', encoding='ascii')
        return request_id, byte_cmd

    def get_keywords(self, name):
        name = "".join([ch if ch.isalnum() else " " for ch in name])
        name = name.strip().lower()
        while '  ' in name:
            name = name.replace('  ', ' ')
        keywords = name.split(' ')
        return keywords

    def _get_result(self, base_cmd):
        request_id, cmd = self._create_cmd(base_cmd)
        for response in self._get_responses(cmd):
            if 'replyID' in response and response['replyID'] == request_id:
                return response['data']['success']

    def _parse_volume(self, vol):
        """parse volume percent or numeric input to valid value. numbers outside of valid range are constrained to valid values.
        possible inputs:
            0.0->1.0          - returned as-is
            '0.0->100.0%','0-100%' - return float(pct/100): 65% sets volume to 0.65
            ['full', 'on', 'unmute', 'enable', 'enabled'] -> 1.0
            ['none', 'off', 'mute', 'disable', 'disabled'] -> 0.0
            ['half', 'mid', 'middle'] -> 0.5

        :param vol:
        :return: parsed volume as float
        """
        def parse_num(n):
            if n < 0:
                return 0
            if 1 < n <= 100:
                return n/100
            if n > 100:
                return 1
            return n

        if type(vol) in [float, int]:
            return parse_num(vol)

        if type(vol) is str:
            if vol.lower() in ON:
                return 1.0
            if vol.lower() in OFF:
                return 0.0
            if vol.lower() in MIDDLE:
                return 0.5
            if '%' in vol:
                return parse_num(float(vol.replace('%', '')))
            else:
                return parse_num(float(vol))

    def find_speaker(self, id=None, name=None, keywords=[], unknown=None):
        caller = sys._getframe(1).f_code.co_name
        speakers = self.get_speakers()
        selected_speaker = None
        if not name and not id and not keywords and not unknown:
            raise ValueError(f'{caller} called with no parameters.'
                             '\n\t\t\tmust pass one of the following: id, name, or keywords')
        elif [bool(name), bool(id), bool(keywords), bool(unknown)].count(True) > 1:
            raise ValueError(f'only one keyword parameter can be passed to {caller}.'
                             '\n\t\t\tmust pass only one: id, name, or keywords')
        elif id:
            for speaker in speakers:
                if speaker.id.lower() == id.lower():
                    selected_speaker = speaker
            if not selected_speaker:
                raise ValueError(f'no speakers were found with the specified id:\n\t\t\t{id}')
        elif name:
            for speaker in speakers:
                if speaker.name.lower() == name.lower():
                    selected_speaker = speaker
            if not selected_speaker:
                raise ValueError(f'no speakers were found with the specified name:\n\t\t\t{name}')
        elif keywords:
            if type(keywords) is not list:
                raise ValueError('keywords parameter must be a list')
            for speaker in speakers:
                if all(kw.lower() in speaker.keywords for kw in keywords):
                    selected_speaker = speaker
            if not selected_speaker:
                raise ValueError(f'no speakers were found with the specified keywords:\n\t\t\t{keywords}')
        elif unknown:
            unknown = unknown.lower()
            try:
                return self.find_speaker(id=unknown)
            except ValueError:
                try:
                    return self.find_speaker(name=unknown)
                except ValueError:
                    keywords = self.get_keywords(unknown)
                    try:
                        return self.find_speaker(keywords=keywords)
                    except ValueError:
                        return None
        return selected_speaker

    def find_source(self, id=None, name=None, keywords=[]):
        caller = sys._getframe(1).f_code.co_name
        sources = self.get_sources()
        selected_source = None
        if not name and not id and not keywords:
            raise ValueError(f'{caller} called with no parameters.'
                             '\n\t\t\tmust pass one of the following: id, name, or keywords')
        elif [bool(name), bool(id), bool(keywords)].count(True) > 1:
            raise ValueError(f'only one keyword parameter can be passed to {caller}.'
                             '\n\t\t\tmust pass only one: id, name, or keywords')
        elif id:
            for source in sources:
                if source.id.lower() == id.lower():
                    selected_source = source
            if not selected_source:
                raise ValueError(f'no sources were found with the specified id:\n\t\t\t{id}')
        elif name:
            for source in sources:
                if source.name.lower() == name.lower():
                    selected_source = source
            if not selected_source:
                raise ValueError(f'no sources were found with the specified name:\n\t\t\t{name}')
        elif keywords:
            if type(keywords) is not list:
                keywords = [keywords]
                # raise ValueError('keywords parameter must be a list')
            for source in sources:
                if all(kw.lower() in source.keywords for kw in keywords):
                    selected_source = source
            if not selected_source:
                raise ValueError(f'no sources were found with the specified keywords:\n\t\t\t{keywords}')
        return selected_source

    def watch(self):
        base_cmd = {"request": "subscribe", "requestID": "-1", "data": {
            "notifications": ["sourceMetadataChanged", "remoteControlChangedRequest", "speakerConnectedChanged",
                              "speakerListChanged",  "speakerNameChanged", "speakerPasswordChanged",
                              "speakerVolumeChanged"]}}
        _, cmd = self._create_cmd(base_cmd)
        for response in self._get_responses(cmd):
            yield response

    def _media_cmd(self, kind):
        base_cmd = {"data": {"commandName": kind},
                    "_replyTypes": ["subscribe", "getSourceMetadata", "connectToSpeaker", "disconnectSpeaker",
                                    "setSpeakerVolume", "getSourceList", "remoteCommand", "selectSource"],
                    "request": "remoteCommand", "requestID": "-1"}
        return self._get_result(base_cmd)

    def play_pause(self):
        return self._media_cmd("PlayPause")

    def next_track(self):
        return self._media_cmd("NextTrack")

    def last_track(self):
        return self._media_cmd("PreviousTrack")

    def get_speakers(self, ids=[], names=[]):
        base_cmd = {"data": { "notifications":
            ["speakerListChanged", "speakerConnectedChanged", "speakerPasswordChanged",
             "speakerVolumeChanged", "speakerNameChanged", "remoteControlChangedRequest"]},
                    "_replyTypes": ["subscribe", "getSourceMetadata", "connectToSpeaker", "disconnectSpeaker",
                                    "setSpeakerVolume", "getSourceList", "remoteCommand", "selectSource"],
                    "request": "subscribe", "requestID": "-1"}
        speaker = namedtuple('speaker', ['name', 'type', 'id', 'volume', 'connected', 'password', 'keywords'])
        request_id, cmd = self._create_cmd(base_cmd)
        for response in self._get_responses(cmd):
            if 'data' in response:
                if 'speakers' in response['data']:
                    speakers = []
                    for s in response['data']['speakers']:
                        keywords = self.get_keywords(s.get('name'))
                        spk = speaker(s.get('name'), s.get('type'), s.get('longIdentifier'), s.get('volume'),
                                      s.get('connected'), s.get('password'), keywords)
                        if ids or names:
                            if spk.id in ids or spk.name in names:
                                speakers.append(spk)
                        else:
                            speakers.append(spk)
                    self.speakers = speakers
                    return speakers

    def connect_speaker(self, *, id=None, name=None, keywords=[]):
        base_cmd = {"request": "connectToSpeaker", "requestID": "-1",
                    "data": {"longIdentifier": None}}
        selected_speaker = self.find_speaker(id, name, keywords)
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        if selected_speaker.connected:
            print(f'speaker \'{selected_speaker.name}\' is already connected')
        else:
            self._get_result(base_cmd)
        return self.get_speakers(ids=[selected_speaker.id])

    def connect_speakers(self, *, ids=[], names=[]):
        self.get_speakers()
        to_change = []
        for speaker in self.speakers:
            if (ids and speaker.id.lower() in [id.lower() for id in ids]) or \
                    (names and speaker.name.lower() in [name.lower() for name in names]) or \
                    (not ids and not names):
                to_change.append(speaker.id)
        for id in to_change:
            self.connect_speaker(id=id)
        return self.get_speakers(ids=to_change)

    def connect_some(self, *, ids=[], names=[]):
        return self.connect_speakers(ids=ids, names=names)

    def connect_all(self):
        return self.connect_speakers()

    def disconnect_speaker(self, *, id=None, name=None, keywords=[]):
        base_cmd = {"request": "disconnectSpeaker", "requestID": "-1",
                    "data": {"longIdentifier": None}}
        selected_speaker = self.find_speaker(id, name, keywords)
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        if not selected_speaker.connected:
            print(f'speaker \'{selected_speaker.name}\' is already disconnected')
        else:
            self._get_result(base_cmd)
        return self.get_speakers(ids=[selected_speaker.id])

    def disconnect_speakers(self, *, ids=[], names=[]):
        self.get_speakers()
        to_change = []
        for speaker in self.speakers:
            if (ids and speaker.id.lower() in [id.lower() for id in ids]) or \
                    (names and speaker.name.lower() in [name.lower() for name in names]) or \
                    (not ids and not names):
                to_change.append(speaker.id)
        for id in to_change:
            self.disconnect_speaker(id=id)
        return self.get_speakers(ids=to_change)

    def disconnect_some(self, *, ids=[], names=[]):
        return self.disconnect_speakers(ids=ids, names=names)

    def disconnect_all(self):
        return self.disconnect_speakers()

    def toggle_speaker(self, *, id=None, name=None, keywords=[]):
        """Disconnect (if connected) and reconnect specified speaker.
        Solves problems when Airfoil gets in a bad state"""
        selected_speaker = self.find_speaker(id, name, keywords)
        result = True
        if selected_speaker.connected:
            result = self.disconnect_speaker(id=selected_speaker.id)
        if result:
            return self.connect_speaker(id=selected_speaker.id)
        else:
            return result

    def toggle_speakers(self, *, ids=[], names=[], include_disconnected=False):
        """Disconnect and reconnect selected speakers.
        Solves problems when Airfoil gets in a bad state"""
        self.get_speakers()
        to_change = []
        for speaker in self.speakers:
            if (ids and speaker.id.lower() in [id.lower() for id in ids]) or\
                (names and speaker.name.lower() in [name.lower() for name in names]) or\
                    (not ids and not names) and\
                    (include_disconnected or speaker.connected):
                to_change.append(speaker.id)
        for id in to_change:
            self.disconnect_speaker(id=id)
        for id in to_change:
            self.connect_speaker(id=id)
        return self.get_speakers(ids=to_change)

    def toggle_some(self, *, ids=[], names=[], include_disconnected=False):
        """alternate name for toggle_speakers"""
        return self.toggle_speakers(ids=ids, names=names, include_disconnected=include_disconnected)

    def toggle_all(self, include_disconnected=False):
        """Disconnect and reconnect all currently connected speakers.
        Solves problems when Airfoil gets in a bad state"""
        return self.toggle_speakers(include_disconnected=include_disconnected)

    def get_sources(self, source_icon=False):
        base_cmd = {"request": "getSourceList", "requestID": "-1",
                    "data": {"iconSize": 10, "scaleFactor": 1}}
        source = namedtuple('source', ['name', 'id', 'type', 'keywords', 'icon'])
        request_id, cmd = self._create_cmd(base_cmd)
        for response in self._get_responses(cmd):
            data = response['data']
            if 'audioDevices' in data or 'runningApplications' in data or\
               'recentApplications' in data or 'systemAudio' in data:
                sources = []
                def add_to_source(src, type):
                    icon = src.get('icon', '') if source_icon else ''
                    keywords = self.get_keywords(src['friendlyName'])
                    sources.append(source(src['friendlyName'], src['identifier'], type, keywords, icon))
                for src in data.get('audioDevices', []):
                    add_to_source(src, type='audio_device')
                for src in data.get('runningApplications', []):
                    add_to_source(src, type='running_apps')
                for src in data.get('recentApplications', []):
                    add_to_source(src, type='recent_apps')
                for src in data.get('systemAudio', []):
                    add_to_source(src, type='system_audio')
                self.sources = sources
                return sources

    def set_source(self, *, name=None, id=None, keywords=[]):
        '''
        connect to source
        if called without params, set source to system audio
        kind can be any one of [audio_device, running_apps, recent_apps, system_audio]
        name or id must match format returned by Airfoil.get_sources() if specified
        keywords is a list of lower-case substrings that appear in the name.
            You need only specify enough keywords to uniquely identify the source, meaning multiple sources don't
            share that set of keywords
            name: 'Microphone (Generic USB Audio Device   )'
            available keywords for this source:
                ['microphone', 'generic', 'usb', 'audio', 'device']

        All parameters provided are used to find the right source in the dict of sources returned
        from Airfoil.get_sources().
            The call to Airfoil will only use kind and id, so if those are specified,
            no further information is required.
            if both name and keywords are specified, an exception will be raised. Pick one.

        :param name:
        :param id:
        :param kind:
        :param keywords
        :return:
        '''
        types = {'audio_device': 'audioDevices', 'running_apps': 'runningApplications',
                 'recent_apps': 'recentApplications', 'system_audio': 'systemAudio'}
        base_cmd = {"request": "selectSource",
                    "requestID": "-1",
                    "data": {"type": '', "identifier": id}}
        if [bool(name), bool(id), bool(keywords)].count(True) > 1:
            raise ValueError('only one keyword parameter can be passed to set_source.'
                             '\n\tmust pass only one: name, id, or keywords,'
                             '\n\tor pass no parameters to select system audio.')
        if not self.sources:
            self.get_sources()
        self.get_current_source()
        selected_source = None
        if not name and not id and not keywords:
            for source in self.sources:
                if source.name == 'System Audio':
                    selected_source = source
        elif id:
            for source in self.sources:
                if source.id.lower() == id.lower():
                    selected_source = source
            if not selected_source:
                raise ValueError(f'no source with specified id was found: {id}')
        elif name:
            for source in self.sources:
                if source.name.lower() == name.lower():
                    selected_source = source
            if not selected_source:
                raise ValueError(f'no source with specified name was found: {name}')
        elif keywords:
            for source in self.sources:
                if all(kw.lower() in source.keywords for kw in keywords):
                    selected_source = source
            if not selected_source:
                raise ValueError(f'no source with specified keywords was found: {keywords}')

        print(f'setting airfoil source to {selected_source.name}')
        base_cmd['data']['type'] = types[selected_source.type]
        base_cmd['data']['identifier'] = selected_source.id
        request_id, cmd = self._create_cmd(base_cmd)
        for response in self._get_responses(cmd):
            if response.get('replyID', None) == request_id:
                return self.get_current_source()
                # try:
                #     return response['data']['success']
                # except KeyError as e:
                    # switching from playing source (tested system audio and spotify) to microphone always
                    # generates error 500 from airfoil
                    # {'replyID': '209', 'errorCode': 500, 'errExplanation':
                    # 'Object reference not set to an instance of an object.'}
                    # After getting this response, audio will not work after switching back to spotify
                    # until you disconnect/reconnect speakers. same behavior from airfoil satellite
                    # creating toggle speakers helper to do this automatically
                    # print(response)
                    # return False

    def get_current_source(self, machine_icon=False, album_art=False, source_icon=False, track_meta=False):
        base_cmd = {"data": {"scaleFactor": 2, "requestedData":
            {"machineIconAndScreenshot": 300, "albumArt": 300, "icon": 32, "artist": "true", "album": "true",
             "title": "true", "sourceName": "true", "bundleid": "true", "trackMetadataAvailable": "true",
             "remoteControlAvailable": "true"}},
             "_replyTypes": [ "subscribe", "getSourceMetadata", "connectToSpeaker", "disconnectSpeaker",
                              "setSpeakerVolume", "getSourceList", "remoteCommand", "selectSource"],
             "request": "getSourceMetadata", "requestID": "-1"}
        if not machine_icon:
            del base_cmd['data']['requestedData']['machineIconAndScreenshot']
        if not album_art:
            del base_cmd['data']['requestedData']['albumArt']
        if not source_icon:
            del base_cmd['data']['requestedData']['icon']
        if not track_meta:
            del base_cmd['data']['requestedData']['artist']
            del base_cmd['data']['requestedData']['title']
            del base_cmd['data']['requestedData']['album']
            base_cmd['data']['requestedData']['trackMetadataAvailable'] = "false"
        request_id, cmd = self._create_cmd(base_cmd)
        result_tuple = \
            namedtuple('current_source', ['source_name', 'source_has_track_metadata', 'source_controllable',
                                          'track_album', 'track_artist', 'track_title', 'track_album_art',
                                          'source_icon', 'system_icon'])

        for response in self._get_responses(cmd):
            data = response['data']
            if 'metadata' in data:
                meta = data['metadata']
                result = result_tuple(meta.get('sourceName'), meta.get('trackMetadataAvailable', False),
                                      meta.get('remoteControlAvailable', False), meta.get('album', None),
                                      meta.get('artist', None), meta.get('title', None),
                                      meta.get('albumArt', None), meta.get('icon', None),
                                      meta.get('machineIconAndScreenshot', None))
                self.current_source = result
                return result

    def set_volume(self, volume, *, id=None, name=None, keywords=[]):
        volume = self._parse_volume(volume)
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data":
                    {"longIdentifier": None, "volume": volume}}

        selected_speaker = self.find_speaker(id, name, keywords)
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        self._get_result(base_cmd)
        return self.get_speakers(ids=[selected_speaker.id])

    def set_volumes(self, volume, *, ids=[], names=[], include_disconnected=False):
        ids = [i.lower() for i in ids]
        names = [n.lower() for n in names]
        volume = self._parse_volume(volume)
        if type(ids) is not list:
            raise ValueError(f'ids must be a list of speaker ids, not \'{type(ids)}\'')
        if type(names) is not list:
            raise ValueError(f'names must be a list of speaker names, not \'{type(names)}\'')

        self.get_speakers()
        to_change = []
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data":
            {"longIdentifier": None, "volume": volume}}

        for speaker in self.speakers:
            if (ids and speaker.id.lower() in ids) or\
                    (names and speaker.name.lower() in names) or\
                    (not ids and not names and (speaker.connected or include_disconnected)):
                cmd = copy.deepcopy(base_cmd)
                cmd['data']['longIdentifier'] = speaker.id
                to_change.append(speaker.id)
                self._get_result(cmd)
        return self.get_speakers(ids=to_change)

    def set_volume_some(self, volume, *, ids=[], names=[], include_disconnected=False):
        return self.set_volumes(volume, ids=ids, names=names, include_disconnected=include_disconnected)

    def set_volume_all(self, volume, include_disconnected=False):
        return self.set_volumes(volume, include_disconnected=include_disconnected)

    def fade_volume(self, end_volume, seconds, *, ticks=10, id=None, name=None, keywords=[]):
        """
        Transition the volume of the specified speaker from it's current volume to the specified end volume over a
        period of time defined by the seconds parameter. By default, it will use 10 ticks, or 10 total changes to
        the volume over the specified number of seconds. You can specify a different number of ticks with the
        ticks parameter. The volume is on a scale from 0.0-1.0 with at least 6 digits of precision. All passed volume
        values are rounded down to 6 digits of precision before being passed to Airfoil. Specifying 100 ticks over 5
        seconds means we attempt 100 separate volume changes over that period until the end_volume is reached.
        Accomplishing tne entire volume change within the specified number of seconds is not guaranteed, and network
        round trip time and Airfoil response time are not accounted for in this calculation.
        :param end_volume: float or int
        :param seconds: float or int
        :param ticks: int
        :param id: id of speaker
        :param name: name of speaker
        :param keywords: keywords representing speaker
        :return:
        """
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data": {"longIdentifier": None, "volume": None}}
        end_volume = self._parse_volume(end_volume)

        if not type(seconds) in [float, int]:
            raise ValueError(f'seconds must be a \'float\' or \'int\', not \'{type(seconds)}\'')
        if type(ticks) is not int:
            raise ValueError(f'ticks must be an \'int\', not \'{type(ticks)}\'')

        selected_speaker = self.find_speaker(id, name, keywords)
        current_volume = selected_speaker.volume
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        wait = round(seconds / ticks, 4)
        increments = round((end_volume - current_volume)/ticks, 6)

        for i in range(0, ticks):
            current_volume += increments
            base_cmd['data']['volume'] = round(current_volume, 6)
            if i == ticks-1:
                base_cmd['data']['volume'] = end_volume
            self._get_result(base_cmd)
            time.sleep(wait)
        return self.get_speakers(ids=[selected_speaker.id])

    def fade_volumes(self, end_volume, seconds, *, ticks=10, ids=[], names=[], include_disconnected=False):
        """
        fade_volumes will change the volume of a collection of speakers simultaneously over a specified period of
        time
        :param end_volume
        :param seconds
        :param ticks
        :param ids
        :param names
        """
        end_volume = self._parse_volume(end_volume)
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data":
                    {"longIdentifier": None, "volume": end_volume}}

        if not type(seconds) in [float, int]:
            raise ValueError(f'seconds must be a \'float\' or \'int\', not \'{type(seconds)}\'')
        if type(ticks) is not int:
            raise ValueError(f'ticks must be an \'int\', not \'{type(ticks)}\'')
        if type(ids) is not list:
            raise ValueError(f'ids must be a list of speaker ids, not \'{type(ids)}\'')
        if type(names) is not list:
            raise ValueError(f'names must be a list of speaker names, not \'{type(names)}\'')

        self.get_speakers()
        speakers = []
        wait = round(seconds / ticks, 4)
        ids = [i.lower() for i in ids]
        names = [n.lower() for n in names]

        for speaker in self.speakers:
            if (ids and speaker.id.lower() in ids) \
                    or (names and speaker.name.lower() in names)\
                    or (not ids and not names and (speaker.connected or include_disconnected)):
                cmd = copy.deepcopy(base_cmd)
                cmd['data']['longIdentifier'] = speaker.id
                increments = round((end_volume - speaker.volume) / ticks, 6)
                speakers.append({'speaker': speaker,  'increments': increments,
                                 'cmd': cmd, 'volume': speaker.volume})
        if len(ids) != len(speakers):
            for id in ids:
                if not any([speaker['speaker'].id == id for speaker in speakers]):
                    raise ValueError(f'no speaker with id \'{id}\' was found')

        for i in range(0, ticks):
            for speaker in speakers:
                # print(speaker['speaker'].name)
                speaker['volume'] += speaker['increments']
                speaker['cmd']['data']['volume'] = round(speaker['volume'], 6)
                if i == ticks-1:
                    speaker['cmd']['data']['volume'] = end_volume
                # print(speaker['cmd'])
                self._get_result(speaker['cmd'])
            time.sleep(wait)
        return self.get_speakers(ids=[s['speaker'].id for s in speakers])

    def fade_some(self, end_volume, seconds, *, ticks=10, ids=[], names=[], include_disconnected=False):
        return self.fade_volumes(end_volume, seconds, ticks=ticks, ids=ids, names=names,
                                 include_disconnected=include_disconnected)

    def fade_all(self, end_volume, seconds, *, ticks=10, include_disconnected=False):
        return self.fade_volumes(end_volume, seconds, ticks=ticks, include_disconnected=include_disconnected)

    def mute(self, *, id=None, name=None, keywords=[]):
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data": {"longIdentifier": None, "volume": 0}}
        selected_speaker = self.find_speaker(id, name, keywords)
        if selected_speaker.volume:
            self.muted_speakers[selected_speaker.id] = selected_speaker
            base_cmd['data']['longIdentifier'] = selected_speaker.id
            self._get_result(base_cmd)
        return self.get_speakers(ids=[selected_speaker.id])

    def unmute(self, *, default_volume=1.0, id=None, name=None, keywords=[]):
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data": {"longIdentifier": None, "volume": None}}
        selected_speaker = self.find_speaker(id, name, keywords)
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        if not selected_speaker.volume:
            muted_speaker = self.muted_speakers.get(selected_speaker.id, None)
            if muted_speaker:
                base_cmd['data']['volume'] = muted_speaker.volume
                del self.muted_speakers[selected_speaker.id]
            else:
                base_cmd['data']['volume'] = self._parse_volume(default_volume)
            self._get_result(base_cmd)
        return self.get_speakers(ids=[selected_speaker.id])

    def mute_some(self, *, ids=[], names=[], include_disconnected=False):
        if type(ids) is not list:
            raise ValueError(f'ids must be a list of speaker ids, not \'{type(ids)}\'')
        if type(names) is not list:
            raise ValueError(f'names must be a list of speaker names, not \'{type(names)}\'')
        self.get_speakers()
        ids = [i.lower() for i in ids]
        names = [n.lower() for n in names]

        muted = []
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data": {"longIdentifier": None, "volume": 0}}
        for speaker in self.speakers:
            if (ids and speaker.id.lower() in ids) \
                    or (names and speaker.name.lower() in names) \
                    or (not ids and not names and (speaker.connected or include_disconnected)):
                if speaker.volume:
                    cmd = copy.deepcopy(base_cmd)
                    cmd['data']['longIdentifier'] = speaker.id
                    self.muted_speakers[speaker.id] = speaker
                    self._get_result(cmd)
                muted.append(speaker.id)
        return self.get_speakers(ids=muted)

    def unmute_some(self, *, ids=[], names=[], default_volume=1.0, include_disconnected=False):
        if type(ids) is not list:
            raise ValueError(f'ids must be a list of speaker ids, not \'{type(ids)}\'')
        if type(names) is not list:
            raise ValueError(f'names must be a list of speaker names, not \'{type(names)}\'')
        self.get_speakers()
        ids = [i.lower() for i in ids]
        names = [n.lower() for n in names]
        unmuted = []
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data": {"longIdentifier": None, "volume": 0}}
        for speaker in self.speakers:
            if (ids and speaker.id.lower() in ids) \
                    or (names and speaker.name.lower() in names) \
                    or (not ids and not names and (speaker.connected or include_disconnected)):
                if not speaker.volume:
                    cmd = copy.deepcopy(base_cmd)
                    cmd['data']['longIdentifier'] = speaker.id
                    if speaker.id in self.muted_speakers:
                        volume = self.muted_speakers[speaker.id].volume
                    else:
                        volume = self._parse_volume(default_volume)
                    cmd['data']['volume'] = volume
                    self._get_result(cmd)
                unmuted.append(speaker.id)
        return self.get_speakers(ids=unmuted)

    def mutes(self, *, ids=[], names=[], include_disconnected=False):
        return self.mute_some(ids=ids, names=[], include_disconnected=include_disconnected)

    def unmutes(self, *, ids=[], names=[], default_volume=1.0, include_disconnected=False):
        return self.unmute_some(ids=ids, names=[], default_volume=default_volume,
                                include_disconnected=include_disconnected)

    def mute_all(self, include_disconnected=False):
        return self.mute_some(include_disconnected=include_disconnected)

    def unmute_all(self, default_volume=1.0, include_disconnected=False):
        return self.unmute_some(default_volume=default_volume, include_disconnected=include_disconnected)
#
# from airfoil_finder import AirfoilFinder
# a = AirfoilFinder.get_first_airfoil()
# a.set_volumes(names=['Bedroom speaker', 'Office speaker'])

# print(a.mute(name='office speaker'))
# time.sleep(2)
# a.muted_speakers = {}
# a.unmute(name='office speaker')
# for s in a.get_speakers().values():
#     print(s.name)
#     print(s.id)
    # print(s.volume)
    # print('------')
# a.toggle_speaker(name='office speaker')
# result = a.mute_some(names=['Office speaker', 'Bedroom speaker'])
# print(result)
# a.muted_speakers = {}
# time.sleep(2)
# result = a.mute_some(names=['Office speaker', 'Bedroom speaker'])
# print(result)


# result = a.mute_some(ids=['Chromecast-Audio-20dcfed9e9bd8cf76a1ad34691dc32ad@Office speaker',
#                           'Chromecast-Audio-99130c3591fa2bbff26b770eda819eff@Bedroom speaker'])
# print(result)
# time.sleep(2)
# result = a.unmute_some(ids=['Chromecast-Audio-20dcfed9e9bd8cf76a1ad34691dc32ad@Office speaker',
#                             'Chromecast-Audio-99130c3591fa2bbff26b770eda819eff@Bedroom speaker'])
# print(result)

# print(a.get_speakers())
# a.fade_volume(1, 5, ticks=100, name='office speaker')
# a.fade_volumes(1, 5, ticks=100, ids=['Chromecast-Audio-20dcfed9e9bd8cf76a1ad34691dc32ad@Office speaker',
#                                       'Chromecast-Audio-99130c3591fa2bbff26b770eda819eff@Bedroom speaker'])
# for event in a.watch(log=False):
#     print(event)
# src = a.get_sources()
# print(src)
# a.set_source(id=r'C:\Users\jeremy\AppData\Roaming\Spotify\spotify.exe')
# for i in range(0, 4):
# a.set_source(keywords=['usb'])
# a.set_source(name='Spotify')
# a.set_source(name='System Audio')
# a.disconnect_speaker(id='Chromecast-Audio-99130c3591fa2bbff26b770eda819eff@Bedroom speaker')
# a.connect_speaker(keywords=['bedroom'])
# a.toggle_speakers()
# a.set_source()
# a.disconnect_speaker("SHIELD-Android-TV-fd75fa2dbc4e513427f5926062f037b3@Bedroom Shield")
# a.get_keywords("Microphone (Generic USB Audio Device   )")
# for s in a.get_sources():
#     print('name: ', s.name)
#     print('  id: ', s.id)


def nones(n):
    return [None for _ in range(n)]


def bools(bool_check):
    return 'yes' if bool_check else 'no'


def print_table(headers, rows, sizes):
    output = []
    template = ""

    if type(rows[0]) is str:
        rows = [rows, ]
    short_sizes = []

    # automatically shrink columns to the minimum required for the longest data if not longer than
    #   specified size
    for n, s in enumerate(sizes):
        max_size = s
        h_len = len(headers[n])
        size = h_len if h_len < max_size else max_size
        for r in rows:
            s_len = len(r[n])
            size = s_len if max_size > s_len > size else size
        short_sizes.append(size)

    for size in short_sizes:
        template += "{:<"+str(size)+"} "

    def process_row(row):
        while any(row):
            line = []
            rest = []
            for n, s in enumerate(row):
                line.append(s[:short_sizes[n]])
                rest.append(s[short_sizes[n]:])
            output.append(template.format(*line))
            row = rest

    process_row(headers)
    dashes = ['-'*s for s in short_sizes]
    process_row(dashes)


    for row in rows:
        process_row(row)

    for o in output:
        print(o)

#
# header = ['name','id','keywords']
# rows = [['aabcdefghijklmnopqrstuvwxyz','babcdefghijklmnopqrstuvwxyz','cabcdefghijklmnopqrstuvwxyz'],
#         ['dabcdefghijklmnopqrstuvwxyz', 'eabcdefghijklmnopqrstuvwxyz', 'fabcdefghijklmnopqrstuvwxyz'],
#         ['aabcdefghijklmnopqrstuvwxyz','babcdefghijklmnopqrstuvwxyz','cabcdefghijklmnopqrstuvwxyz'],
#         ['dabcdefghijklmnopqrstuvwxyz', 'eabcdefghijklmnopqrstuvwxyz', 'fabcdefghijklmnopqrstuvwxyz']]
# print_table(header, rows, (15, 10, 7))