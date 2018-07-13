import socket, json, random, sys, time, copy
from collections import namedtuple

ON = ['full', 'on', 'unmute', 'enable', 'enabled', 'true', 'high', 'hi']
OFF = ['none', 'off', 'mute', 'disable', 'disabled', 'false', 'low', 'lo']
MIDDLE = ['half', 'mid', 'middle']

class Airfoil(object):
    speaker = namedtuple('speaker', ['name', 'type', 'id', 'volume', 'connected', 'password', 'keywords'])
    source = namedtuple('source', ['name', 'id', 'type', 'keywords', 'icon'])
    current_source = namedtuple('current_source', ['source_name',
        'source_has_track_metadata', 'source_controllable', 'track_album',
        'track_artist', 'track_title', 'track_album_art', 'source_icon',
        'system_icon'])

    def __init__(self, ip, port, name):
        self.ip = ip
        self.port = port
        self.name = name
        self.sources = []
        self.speakers = []
        self.muted_speakers = {}

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
        """
        Airfoil.get_keyword will parse a string into appropriate keywords by replacing all alphanumeric characters with
         a space, and then splitting the line into a list. keywords can be used when searching for speakers or sources
         in other methods.
        :param name:    string to get keywords for
        :return:        list of keywords for name parameter
        """
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
        """
            Airfoil._parse_volume will parse percent or numeric input to a valid value for Airfoil volume.
            numbers outside of the range of 0.0 to 1.0 are constrained to valid values.
            possible inputs:
                0.0->1.0          - returned as-is
                '0.0->100.0%','0-100%' - return float(pct/100): 65% sets volume to 0.65
                1-100   treated as percent like above
                <0      rounded to 0.0
                >100    rounded to 1.0
                ['full', 'on', 'unmute', 'enable', 'enabled'] -> 1.0
                ['none', 'off', 'mute', 'disable', 'disabled'] -> 0.0
                ['half', 'mid', 'middle'] -> 0.5

        :param vol:     can be int, float, number as str, percent as str, descriptor as str
        :return:        parsed volume as float from 0.0 to 1.0
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
        """
            Airfoil.find_speaker will find and return an Airfoil.speaker object matching the given parameters. None of the
            parameters are case-sensitive.
            - Passing id or name will return the speaker that matches the exact name or id that was given.
            - Passing keywords will return the first speaker to match all of the given keywords. If more than one
              speaker matches, there are no guarantees about which one will be returned. Be sure to use enough
              keywords to uniquely identify your speaker.
            - if no match is found for a parameter passed as name, id, or keywords, a ValueError will be raised.
            - Passing a parameter as unknown will attempt three searches.
                1. try with parameter as a name.
                2. try with parameter as an id
                3. turn parameter into keywords if it's not already a list and does a search by keywords.
              If no match is made using all three methods, None is returned


        :param id:          speaker id as string, not case-sensitive
        :param name:        speaker name as string, not case-sensitive
        :param keywords:    speaker keywords as list of strings, not case-sensitive
        :param unknown:     one of the above, not case-sensitive
        :return:            either an Airfoil.speaker object or None
        """
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
        """
            Airfoil.find_source will find and return an Airfoil.source object matching the given parameters. None of the
            parameters are case-sensitive.
            - Passing id or name will return the source that matches the exact name or id that was given.
            - Passing keywords will return the first source to match all of the given keywords. If more than one
              source matches, there are no guarantees about which one will be returned. Be sure to use enough
              keywords to uniquely identify your source.
            - if no match is found for a parameter passed as name, id, or keywords, a ValueError will be raised.

                :param id:          source id as string, not case-sensitive
                :param name:        source name as string, not case-sensitive
                :param keywords:    source keywords as list of strings, not case-sensitive
                :return:            an Airfoil.source object
                """
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
        """
            Airfoil.watch is a Python generator that will yield all activity that occurs from Airfoil as changes occur.
            The following categories of events will be yielded from this generator as they occur, regardless of where
            they were initiated from:
                "sourceMetadataChanged", "remoteControlChangedRequest", "speakerConnectedChanged",
                "speakerListChanged",  "speakerNameChanged", "speakerPasswordChanged", "speakerVolumeChanged"
        """
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
        """
            Airfoil.play_pause sends a play_pause command to Airfoil.
            If your current_source supports remote control and the command is successfully sent, True will be returned.
            Use Airfoil.get_current_source() to determine if current source supports remote control.
        :return: boolean value indicating Airfoil's success in controlling the current source.
        """
        return self._media_cmd("PlayPause")

    def next_track(self):
        """
            Airfoil.next_track sends a next_track command to Airfoil.
            If your current_source supports remote control and the command is successfully sent, True will be returned.
            Use Airfoil.get_current_source() to determine if current source supports remote control.
        :return: boolean value indicating Airfoil's success in controlling the current source.
        """
        return self._media_cmd("NextTrack")

    def last_track(self):
        """
            Airfoil.last_track sends a last_track command to Airfoil.
            If your current_source supports remote control and the command is successfully sent, True will be returned.
            Use Airfoil.get_current_source() to determine if current source supports remote control.
        :return: boolean value indicating Airfoil's success in controlling the current source.
        """
        return self._media_cmd("PreviousTrack")

    def get_speakers(self, ids=[], names=[]):
        """
            Airfoil.get_speakers returns a list of Airfoil.speaker objects matching any ids or names that were passed
            as parameters. You can call this method with zero, one, or both parameters.
            -  passing no parameters returns all speakers
            -  passing one or both parameters returns all matching speakers.
            -  no checks are performed to ensure that all ids and names match, so verify that the number of speakers
               returned matches what you expected.
            -  list of returned speakers is also saved to self.speakers
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :return:        list of Airfoil.speaker objects matching request
        """
        base_cmd = {"data": { "notifications":
            ["speakerListChanged", "speakerConnectedChanged", "speakerPasswordChanged",
             "speakerVolumeChanged", "speakerNameChanged", "remoteControlChangedRequest"]},
                    "_replyTypes": ["subscribe", "getSourceMetadata", "connectToSpeaker", "disconnectSpeaker",
                                    "setSpeakerVolume", "getSourceList", "remoteCommand", "selectSource"],
                    "request": "subscribe", "requestID": "-1"}

        request_id, cmd = self._create_cmd(base_cmd)
        for response in self._get_responses(cmd):
            if 'data' in response:
                if 'speakers' in response['data']:
                    speakers = []
                    for s in response['data']['speakers']:
                        keywords = self.get_keywords(s.get('name'))
                        spk = self.speaker(s.get('name'), s.get('type'), s.get('longIdentifier'), s.get('volume'),
                                           s.get('connected'), s.get('password'), keywords)
                        if ids or names:
                            if spk.id in ids or spk.name in names:
                                speakers.append(spk)
                        else:
                            speakers.append(spk)
                    self.speakers = speakers
                    return speakers

    def connect_speaker(self, *, id=None, name=None, keywords=[]):
        """
        Airfoil.connect_speaker will tell Airfoil to connect one speaker based on the id, name, or keywords given as a
         parameter. Only one parameter is required; passing multiple parameters here will raise a ValueError exception.
        - if the speaker is already connected, a message will be printed to the log, but no exception will be
          raised.
        :param id:          speaker id, string, not case-sensitive
        :param name:        speaker name, string, not case-sensitive
        :param keywords:    speaker keywords, list of strings, not case-sensitive
        :return:            list with Airfoil.speaker object representing the speaker that was connected.
        """
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
        """
        Airfoil.connect_speakers will tell Airfoil to connect multiple speakers based on the names or ids that are
        given as parameters. You can call this method with zero, one, or both parameters.
            -  passing no parameters disconnects all currently connected speakers.
            -  passing one or both parameters disconnects all matching speakers.
            -  no checks are performed to ensure that all ids and names match, so verify that the number of speakers
               returned matches what you expected.
            -  the list of affected speakers is also saved to self.speakers

        Note on group commands: All commands that work on a collection of speakers like this will parse the given
        parameters into a list of speakers, and then give Airfoil individual commands for each change to each
        speaker. Calling this method with 10 speaker ids will result in 10 separate commands sent to Airfoil, and the
        speakers will appear to connect sequentially. This may take some time, and the method will not return until
        all actions have completed. Check the list of speakers that is returned to ensure all its properties have the
        expected values, such as with:
            [speaker.id for speaker in Airfoil.speakers if not speaker.connected] -> list of speakers not connected
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :return:        list of Airfoil.speaker objects matching request
        """
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
        """
        Airfoil.connect_some is an alias for Airfoil.connect_speakers. See documentation for Airfoil.connect_speakers.
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :return:        list of Airfoil.speaker objects matching request
        """
        return self.connect_speakers(ids=ids, names=names)

    def connect_all(self):
        """
        Airfoil.connect_all is an alias for Airfoil.connect_speakers() called with no parameters. This method will tell
        Airfoil to connect every speaker that it can see. See documentation for Airfoil.connect_speakers.
        :return:        list of Airfoil.speaker objects matching request
        """
        return self.connect_speakers()

    def disconnect_speaker(self, *, id=None, name=None, keywords=[]):
        """
        Airfoil.disconnect_speaker will tell Airfoil to disconnect one speaker based on the id, name, or keywords given
         as a parameter. Only one parameter is required; passing multiple parameters will raise a ValueError exception.
        - if the speaker is already connected, a message will be printed, but no exception will be raised.
        :param id:          speaker id, string, not case-sensitive
        :param name:        speaker name, string, not case-sensitive
        :param keywords:    speaker keywords, list of strings, not case-sensitive
        :return:            list with Airfoil.speaker object representing the speaker that was connected.
        """
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
        """
            Airfoil.disconnect_speakers will tell Airfoil to disconnect multiple speakers based on the names or ids that
            are given as parameters. You can call this method with zero, one, or both parameters.
                -  passing no parameters connects all speakers that Airfoil can see.
                -  passing one or both parameters connects all matching speakers.
                -  no checks are performed to ensure that all ids and names match, so verify that the number of speakers
                   returned matches what you expected.
                -  the list of affected speakers is also saved to self.speakers

            Note on group commands: All commands that work on a collection of speakers like this will parse the given
            parameters into a list of speakers, and then give Airfoil individual commands for each change to each
            speaker. Calling this method with 10 speaker ids will result in 10 separate commands sent to Airfoil, and the
            speakers will appear to connect sequentially. This may take some time, and the method will not return until
            all actions have completed. Check the list of speakers that is returned to ensure all its properties have the
            expected values, such as with:
                [speaker.id for speaker in Airfoil.speakers if speaker.connected] -> list of speakers still connected
            :param ids:     list of speaker ids, not case-sensitive
            :param names:   list of speaker names, not case-sensitive
            :return:        list of Airfoil.speaker objects matching request
            """
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
        """
        Airfoil.disconnect_some is an alias for Airfoil.disconnect_speakers.
         See documentation for Airfoil.disconnect_speakers.
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :return:        list of Airfoil.speaker objects matching request
        """
        return self.disconnect_speakers(ids=ids, names=names)

    def disconnect_all(self):
        """
        Airfoil.disconnect_all is an alias for Airfoil.disconnect_speakers() called with no parameters. This method will
         tell Airfoil to disconnect all currently connected speakers. See documentation for Airfoil.disconnect_speakers.
        :return:        list of Airfoil.speaker objects matching request
        """
        return self.disconnect_speakers()

    def toggle_speaker(self, *, id=None, name=None, keywords=[]):
        """
        Airfoil.toggle_speaker will tell Airfoil to disconnect and then reconnect one speaker based on the id, name, or
         keywords given as a parameter. This is useful for scenarios where the the sound stops working after changing a
         source, or some other playback problem occurs. Only one parameter is required; passing multiple parameters will
         raise a ValueError exception.
        - if the speaker is already disconnected, the speaker will just be connected.
        :param id:          speaker id, string, not case-sensitive
        :param name:        speaker name, string, not case-sensitive
        :param keywords:    speaker keywords, list of strings, not case-sensitive
        :return:            list with Airfoil.speaker object representing the speaker that was toggled.
        """
        selected_speaker = self.find_speaker(id, name, keywords)
        result = None
        if selected_speaker.connected:
            result = self.disconnect_speaker(id=selected_speaker.id)[0]
        if result and not result.connected or not selected_speaker.connected:
            return self.connect_speaker(id=selected_speaker.id)
        else:
            return []

    def toggle_speakers(self, *, ids=[], names=[], include_disconnected=False):
        """
            Airfoil.toggle_speakers will disconnect and then reconnect multiple speakers based on the
            names or ids that are given as parameters. You can call this method with zero, one, or both ids and names
            parameters.
                -  passing neither ids nor names toggles all currently connected speakers.
                    - If you want to disconnect all currently connected speakers, and then connect all speakers (not
                      just the speakers that were connected at the beginning of the action), set
                      include_disconnected=True.
                -  passing one or both parameters connects all matching speakers.
                -  no checks are performed to ensure that all ids and names match, so verify that the number of speakers
                   returned matches what you expected.
                -  the list of affected speakers is also saved to self.speakers

            Note on group commands: All commands that work on a collection of speakers like this will parse the given
            parameters into a list of speakers, and then give Airfoil individual commands for each change to each
            speaker. Calling this method with 10 speaker ids will result in 20 separate commands sent to Airfoil, with
            all the currently connected speakers disconnected sequentially, and then all speakers will be reconnected
            sequentially . This may take some time, and the method will not return until all actions have completed.
            Check the list of speakers that is returned to ensure all its properties have the expected values, such as
            with:
                [speaker.id for speaker in Airfoil.speakers if not speaker.connected] -> list of speakers that did not
                disconnect, representing a failure to toggle the speakers for some reason.
            :param ids:     list of speaker ids, not case-sensitive
            :param names:   list of speaker names, not case-sensitive
            :param include_disconnected:    boolean, default False, also toggle speakers that are disconnected
            :return:        list of Airfoil.speaker objects showing their state after your request
            """
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
        """
        Airfoil.toggle_some is an alias for Airfoil.toggle_speakers.
         See documentation for Airfoil.toggle_speakers.
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :param include_disconnected:    boolean, default False, also toggle speakers that are disconnected
        :return:        list of Airfoil.speaker objects showing their state after your request"""
        return self.toggle_speakers(ids=ids, names=names, include_disconnected=include_disconnected)

    def toggle_all(self, include_disconnected=False):
        """
        Airfoil.toggle_all is an alias for Airfoil.toggle_speakers called with no ids or names. This method will toggle
        all currently connected speakers. See documentation for Airfoil.toggle_speakers.
        :param include_disconnected:    boolean, default False, also toggle speakers that are disconnected
        :return:        list of Airfoil.speaker objects showing their state after your request
        """
        return self.toggle_speakers(include_disconnected=include_disconnected)

    def get_sources(self, source_icon=False):
        """
        Airfoil.get_sources will return all of the current sources that Airfoil can see as a list of Airfoil.source
        objects. By default, the source_icon for sources is not returned, but if you set source_icon=True, a base64
        encoded image will be included in the Airfoil.source objects.
        :param source_icon:
        :return: list of Airfoil.source objects representing a
        """
        base_cmd = {"request": "getSourceList", "requestID": "-1",
                    "data": {"iconSize": 10, "scaleFactor": 1}}
        request_id, cmd = self._create_cmd(base_cmd)
        for response in self._get_responses(cmd):
            data = response['data']
            if 'audioDevices' in data or 'runningApplications' in data or\
               'recentApplications' in data or 'systemAudio' in data:
                sources = []
                def add_to_source(src, type):
                    icon = src.get('icon', '') if source_icon else ''
                    keywords = self.get_keywords(src['friendlyName'])
                    sources.append(self.source(src['friendlyName'], src['identifier'], type, keywords, icon))
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
        """
        Airfoil.set_source with set the current source to the source matching the id, name, or keywords given as a
        parameter. Only one parameter is required; passing multiple parameters here will raise a ValueError
        exception. If no match is found for the given parameter, a ValueError exception will be raised.
        :param name:        source id, string, not case-sensitive
        :param id:          source name, string, not case-sensitive
        :param keywords:    source keywords, string, not case-sensitive
        :return:            Airfoil.current_source object representing current source after sending command to Airfoil.
        """
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

    def get_current_source(self, machine_icon=False, album_art=False, source_icon=False, track_meta=False):
        """
        Airfoil.get_current_source returns the currently selected source in Airfoil as an Airfoil.current_source object.
        You can also optionally retrieve base64-encoded images for machine_icon, source_icon, and album_art, as well as
        track metadata if available.
        :param machine_icon: boolean, default False, include b64-encoded machine icon in current_source object
        :param source_icon:  boolean, default False, include b64-encoded source icon in current_source object
        :param album_art:    boolean, default False, include b64-encoded album art in current_source object if available
        :param track_meta:   boolean, default False, include track metadata in current_source object if available
        :return:             Airfoil.current_source object
        """
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

        for response in self._get_responses(cmd):
            data = response['data']
            if 'metadata' in data:
                meta = data['metadata']
                result = self.current_source(meta.get('sourceName'), meta.get('trackMetadataAvailable', False),
                                             meta.get('remoteControlAvailable', False), meta.get('album', None),
                                             meta.get('artist', None), meta.get('title', None),
                                             meta.get('albumArt', None), meta.get('icon', None),
                                             meta.get('machineIconAndScreenshot', None))
                return result

    def set_volume(self, volume, *, id=None, name=None, keywords=[]):
        """
        Airfoil.set_volume will set the volume level for one speaker based on the id, name, or
         keywords given as a parameter. Only one parameter is required; passing multiple parameters will
         raise a ValueError exception.
        :param volume:      any valid value for volume is accepted
        :param id:          speaker id, string, not case-sensitive
        :param name:        speaker name, string, not case-sensitive
        :param keywords:    speaker keywords, list of strings, not case-sensitive
        :return:            list with Airfoil.speaker object showing the speaker state after the command was sent
        """
        volume = self._parse_volume(volume)
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data":
                    {"longIdentifier": None, "volume": volume}}

        selected_speaker = self.find_speaker(id, name, keywords)
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        self._get_result(base_cmd)
        return self.get_speakers(ids=[selected_speaker.id])

    def set_volumes(self, volume, *, ids=[], names=[], include_disconnected=False):
        """
        Airfoil.set_volumes will set the volume on a group of speakers based on the names and ids that are given as
         parameters, You can call this method with zero, one, or both ids and names parameters.
         -  passing neither ids nor names sets the volume on all currently connected speakers.
            - If you want to set the volume on speakers even if they are disconnected, pass include_disconnected=True.
         -  passing one or both parameters sets the volume all matching speakers.
         -  no checks are performed to ensure that all ids and names matched, so verify that the number of speakers
            returned matches what you expected.
         -  the list of affected speakers is also saved to Airfoil.speakers

        Note on group commands: All commands that work on a collection of speakers like this will parse the given
        parameters into a list of speakers, and then give Airfoil individual commands for each change to each
        speaker. Calling this method with 10 speaker ids will result in 10 separate commands sent to Airfoil, with
        all affected speakers changing volumes sequentially. This may take some time, and the method will not return
        until all actions have completed. Check the list of speakers that is returned (or Airfoil.speakers) to ensure
        all properties have the expected values, such as with:
            # list of tuples with name and volume of all affected speakers.
            [(speaker.name, speaker.volume) for speaker in Airfoil.speakers]
        :param volume:  any valid value for volume is accepted
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :param include_disconnected:    boolean, default False, also set volume on speakers that are disconnected
        :return:        list of affected Airfoil.speaker objects showing their state after your request
        """
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
        """
        Airfoil.set_volume_some is an alias for Airfoil.set_volumes. See documentation for Airfoil.set_volume_some.
        :param volume:  any valid value for volume is accepted
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :param include_disconnected:    boolean, default False, also set volume on speakers that are disconnected
        :return:        list of affected Airfoil.speaker objects showing their state after your request
        """
        return self.set_volumes(volume, ids=ids, names=names, include_disconnected=include_disconnected)

    def set_volume_all(self, volume, include_disconnected=False):
        """
        Airfoil.set_volume_all is an alias for Airfoil.set_volumes called with no names or ids. This method will set the
        volume on all currently connected speakers See documentation for Airfoil.set_volume_some.
        :param volume:  any valid value for volume is accepted
        :param include_disconnected:    boolean, default False, also set volume on speakers that are disconnected
        :return:        list of affected Airfoil.speaker objects showing their state after your request
        """
        return self.set_volumes(volume, include_disconnected=include_disconnected)

    def fade_volume(self, end_volume, seconds, *, ticks=10, id=None, name=None, keywords=[]):
        """
        Airfoil.fade_volume will transition the volume of the specified speaker from it's current volume to the
        specified end volume over a period of time defined by the seconds parameter.
        - By default, it will use 10 ticks, or 10 total changes to the volume over the specified number of seconds.
          You can specify a different number of ticks with the ticks parameter.
        - Specifying 100 ticks over 5 seconds means we attempt 100 separate volume changes per speaker over that period
          until the end_volume is reached.
        - Accomplishing tne entire volume change within the specified number of seconds is not guaranteed, as network
          round trip time and Airfoil response time are not accounted for in this calculation. Asking for 1000 ticks to
          be performed in 1 second will result in a an operation that takes much longer than 1 second to complete, but
          all requested ticks will be performed. It is possible to overload Airfoil with these requests, with
          unpredictable results.
        - The total time of a fade_volume action will be:
                seconds + (ticks * [number of speakers] * ([network round trip time] + [airfoil response time]))
        :param end_volume:  any valid value for volume is accepted
        :param seconds:     float, length of time to change to take to change volume
        :param ticks:       int, number of increments between current volume and end volume.
        :param id:          string, speaker id
        :param name:        string, speaker name
        :param keywords:    list of strings, sufficient keywords to uniquely identify speaker
        :return:    list with affected Airfoil.speaker object showing its state after your request
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
        Airfoil.fade_volumes will transition the volume of a collection of speakers from their current volume to the
        specified end volume over a period of time defined by the seconds parameter. You can call this method with zero,
        one, or both ids and names parameters.
         -  passing neither ids nor names changes the volume on all currently connected speakers.
            - If you want to change the volume on speakers even if they are disconnected, pass include_disconnected=True.
         -  passing one or both parameters changes the volume on all matching speakers.
         -  no checks are performed to ensure that all ids and names matched, so verify that the number of speakers
            returned matches what you expected.
         -  the list of affected speakers is also saved to Airfoil.speakers
        See documentation for Airfoil.fade_volume

        Note on group commands: All commands that work on a collection of speakers like this will parse the given
        parameters into a list of speakers, and then give Airfoil individual commands for each change to each
        speaker. Calling this method with 10 speaker ids with the default 10 ticks will result in 100 separate commands
        sent to Airfoil, with all affected speakers changing volumes sequentially. This may take some time, and the
        method will not return until all actions have completed. Check the list of speakers that is returned (or
        Airfoil.speakers) to ensure all properties have the expected values, such as with:
            # list of tuples with name and volume of all affected speakers.
            [(speaker.name, speaker.volume) for speaker in Airfoil.speakers]

        :param end_volume:  any valid value for volume is accepted
        :param seconds:     positive float, length of time to change to take to change volume
        :param ticks:       int, number of increments between current volume and end volume.
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :param include_disconnected:    boolean, default False, also set volume on speakers that are disconnected
        :return:        list of affected Airfoil.speaker objects showing their state after your request
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
        """
        Airfoil.fade_some is an alias for Airfoil.fade_volumes.
        See documentation for Airfoil.fade_some
        :param end_volume:  any valid value for volume is accepted
        :param seconds:     positive float, length of time to change to take to change volume
        :param ticks:       int, number of increments between current volume and end volume.
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :param include_disconnected:    boolean, default False, also set volume on speakers that are disconnected
        :return:        list of affected Airfoil.speaker objects showing their state after your request
        """
        return self.fade_volumes(end_volume, seconds, ticks=ticks, ids=ids, names=names,
                                 include_disconnected=include_disconnected)

    def fade_all(self, end_volume, seconds, *, ticks=10, include_disconnected=False):
        """
        Airfoil.fade_all is an alias for Airfoil.fade_volumes called with no parameters. This method will change
        the volume on all currently connected speakers See documentation for Airfoil.fade_volumes.
        :param end_volume:  any valid value for volume is accepted
        :param seconds:     positive float, length of time to change to take to change volume
        :param ticks:       int, number of increments between current volume and end volume.
        :param include_disconnected:    boolean, default False, also set volume on speakers that are disconnected
        :return:        list of affected Airfoil.speaker objects showing their state after your request
         """
        return self.fade_volumes(end_volume, seconds, ticks=ticks, include_disconnected=include_disconnected)

    def mute(self, *, id=None, name=None, keywords=[]):
        """
        Airfoil.mute will mute one speaker based on the id, name, or keywords given as a parameter. Muting a speaker
        sets the current volume to 0, but before doing so saves the current Airfoil.speaker object so it can be
        referenced when unmute is called.
            Airfoil.muted_speakers[speaker.id] = Airfoil.speaker object before mute; volume property has prior volume
        Only one parameter is required; passing multiple parameters will raise a ValueError exception.

        :param id:          speaker id, string, not case-sensitive
        :param name:        speaker name, string, not case-sensitive
        :param keywords:    speaker keywords, list of strings, not case-sensitive
        :return:            list with Airfoil.speaker object showing the speaker state after the command was sent
        """
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data": {"longIdentifier": None, "volume": 0}}
        selected_speaker = self.find_speaker(id, name, keywords)
        if selected_speaker.volume:
            self.muted_speakers[selected_speaker.id] = selected_speaker
            base_cmd['data']['longIdentifier'] = selected_speaker.id
            self._get_result(base_cmd)
        return self.get_speakers(ids=[selected_speaker.id])

    def unmute(self, *, default_volume=1.0, id=None, name=None, keywords=[]):
        """
        Airfoil.unmute will unmute one speaker based on the id, name, or keywords given as a parameter.
        - A request to unmute a speaker that is not muted (volume=0) will be ignored
        - If a speaker is unmuted, and an Airfoil.speaker object exists in Airfoil.muted_speakers, the volume will be
          returned to the previous volume for that speaker.
            Airfoil.muted_speakers[speaker.id] = Airfoil.speaker object before mute; volume property has prior volume
        - If a speaker is unmuted, and no Airfoil.speaker object exists in Airfoil.muted_speakers for that speaker, the
          volume will be set to the default_volume parameter, which defaults to 1.0 (full volume)

        Only one parameter is required; passing multiple parameters will raise a ValueError exception.

        :param id:          speaker id, string, not case-sensitive
        :param name:        speaker name, string, not case-sensitive
        :param keywords:    speaker keywords, list of strings, not case-sensitive
        :return:            list with Airfoil.speaker object showing the speaker state after the command was sent
        """
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
        """
        Airfoil.mute_some will tell Airfoil to mute multiple speakers based on the names or ids that are
        given as parameters. You can call this method with zero, one, or both parameters.
            -  passing no parameters mutes all currently connected speakers.
            -  passing one or both parameters mutes all matching speakers.
            -  no checks are performed to ensure that all ids and names match, so verify that the number of speakers
               returned matches what you expected.
            -  the list of affected speakers is also saved to self.speakers
        Also see documentation for Airfoil.mute

        Note on group commands: All commands that work on a collection of speakers like this will parse the given
        parameters into a list of speakers, and then give Airfoil individual commands for each change to each
        speaker. Calling this method with 10 speaker ids will result in 10 separate commands sent to Airfoil, and the
        speakers will appear to mute sequentially. This may take some time, and the method will not return until
        all actions have completed. Check the list of speakers that is returned to ensure all its properties have the
        expected values, such as with:
            # list of tuples with name and volume of all affected speakers.
            [(speaker.name, speaker.volume) for speaker in Airfoil.speakers]
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :param include_disconnected:
        :return:        list of Airfoil.speaker objects matching request
        """
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
        """
        Airfoil.unmute_some will tell Airfoil to unmute multiple speakers based on the names or ids that are
        given as parameters. You can call this method with zero, one, or both parameters.
            -  passing no parameters mutes all currently connected speakers.
            -  passing one or both parameters mutes all matching speakers.
            -  no checks are performed to ensure that all ids and names match, so verify that the number of
               speakers returned matches what you expected.
            -  the list of affected speakers is also saved to self.speakers
        Also see documentation for Airfoil.unmute

        Note on group commands: All commands that work on a collection of speakers like this will parse the given
        parameters into a list of speakers, and then give Airfoil individual commands for each change to each
        speaker. Calling this method with 10 speaker ids will result in 10 separate commands sent to Airfoil, and the
        speakers will appear to mute sequentially. This may take some time, and the method will not return until
        all actions have completed. Check the list of speakers that is returned to ensure all its properties have the
        expected values, such as with:
            # list of tuples with name and volume of all affected speakers.
            [(speaker.name, speaker.volume) for speaker in Airfoil.speakers]
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :param include_disconnected:  boolean, default False, also unmute speakers that are disconnected
        :return:        list of Airfoil.speaker objects matching request
        """
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
        """
        Airfoil.mutes is an alias for Airfoil.mute_some.
         See documentation for Airfoil.mute_some.
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :param include_disconnected:   boolean, default False, also mute speakers that are disconnected
        :return:        list of Airfoil.speaker objects matching request
        """
        return self.mute_some(ids=ids, names=names, include_disconnected=include_disconnected)

    def unmutes(self, *, ids=[], names=[], default_volume=1.0, include_disconnected=False):
        """
        Airfoil.unmutes is an alias for Airfoil.unmute_some.
         See documentation for Airfoil.unmute_some.
        :param ids:     list of speaker ids, not case-sensitive
        :param names:   list of speaker names, not case-sensitive
        :param include_disconnected:    boolean, default False, also unmute speakers that are disconnected
        :return:                        list of Airfoil.speaker objects matching request
        """
        return self.unmute_some(ids=ids, names=names, default_volume=default_volume,
                                include_disconnected=include_disconnected)

    def mute_all(self, include_disconnected=False):
        """
        Airfoil.mute_all is an alias for Airfoil.mute_some called with no parameters
         See documentation for Airfoil.mute_some
        :param include_disconnected:    boolean, default False, also mute speakers that are disconnected
        :return:                        list of Airfoil.speaker objects matching request
        """
        return self.mute_some(include_disconnected=include_disconnected)

    def unmute_all(self, default_volume=1.0, include_disconnected=False):
        """
        Airfoil.unmute_all is an alias for Airfoil.unmute_some called with no parameters
         See documentation for Airfoil.unmute_some
        :param include_disconnected:    boolean, default False, also unmute speakers that are disconnected
        :return:                        list of Airfoil.speaker objects matching request
        """
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
