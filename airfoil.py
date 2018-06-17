import socket, json, random, sys
from collections import namedtuple

class Airfoil(object):
    HELLO = b"com.rogueamoeba.protocol.slipstreamremote\nmajorversion=1,minorversion=5\nOK\n"
    ACCEPTABLE_VERSION = "majorversion=1,minorversion=5"

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.sources = {}
        self.speakers = {}
        self.current_source = None

    @classmethod
    def get_first_airfoil(cls):
        ip = "192.168.0.50"
        port = 62305
        return cls(ip, port)

    @classmethod
    def get_airfoil_by_name(cls, name):
        ip = "192.168.0.50"
        port = 62305
        return cls(ip, port)

    def _connect(self, sock):
        sock.connect((self.ip, self.port))
        sock.sendall(self.HELLO)
        data = sock.recv(128)
        return self.ACCEPTABLE_VERSION in data.decode()

    def _get_responses(self, sock):
        MAX_BYTES = 4096
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
                get_bytes = MAX_BYTES if num_bytes > MAX_BYTES else num_bytes - 1
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

    def _get_keywords(self, name):
        name = "".join([ch if ch.isalnum() else " " for ch in name])
        name = name.strip().lower()
        while '  ' in name:
            name = name.replace('  ', ' ')
        keywords = name.split(' ')
        return keywords

    def watch(self):
        base_cmd = {"request": "subscribe", "requestID": "-1", "data": {
            "notifications": ["remoteControlChangedRequest", "speakerConnectedChanged", "speakerListChanged",
                              "speakerNameChanged", "speakerPasswordChanged", "speakerVolumeChanged"]}}
        request_id, cmd = self._create_cmd(base_cmd)
        with socket.socket() as sock:
            if self._connect(sock):
                sock.send(cmd)
                for response in self._get_responses(sock):
                    print(response)

    def get_speakers(self):
        base_cmd = {"data": {
            "notifications": ["speakerListChanged", "speakerConnectedChanged", "speakerPasswordChanged",
                              "speakerVolumeChanged", "speakerNameChanged", "remoteControlChangedRequest"]},
                    "_replyTypes": ["subscribe", "getSourceMetadata", "connectToSpeaker", "disconnectSpeaker",
                                    "setSpeakerVolume", "getSourceList", "remoteCommand", "selectSource"],
                    "request": "subscribe", "requestID": "-1"}
        speaker = namedtuple('speaker', ['name', 'type', 'id', 'volume', 'connected', 'password', 'keywords'])
        request_id, cmd = self._create_cmd(base_cmd)
        with socket.socket() as sock:
            if self._connect(sock):
                sock.send(cmd)
                for response in self._get_responses(sock):
                    if 'data' in response:
                        if 'speakers' in response['data']:
                            speakers = {}
                            for s in response['data']['speakers']:
                                keywords = self._get_keywords(s.get('name'))
                                spk = speaker(s.get('name'), s.get('type'), s.get('longIdentifier'), s.get('volume'),
                                              s.get('connected'), s.get('password'), keywords)
                                speakers[spk.name] = spk
                            self.speakers = speakers
                            return speakers

    def connect_speaker(self, *, id=None, name=None, keywords=[]):
        base_cmd = {"request": "connectToSpeaker", "requestID": "-1",
                    "data": {"longIdentifier": None}}
        caller = 'connect_speaker'
        selected_speaker = self._find_speaker(id, name, keywords)
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        if selected_speaker.connected:
            print(f'speaker \'{selected_speaker.name}\' is already connected')
            return True
        return self._change_speaker_connected(base_cmd)

    def disconnect_speaker(self, *, id=None, name=None, keywords=[]):
        base_cmd = {"request": "disconnectSpeaker", "requestID": "-1",
                    "data": {"longIdentifier": None}}
        caller = 'disconnect_speaker'
        selected_speaker = self._find_speaker(id, name, keywords)
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        if not selected_speaker.connected:
            print(f'speaker \'{selected_speaker.name}\' is already disconnected')
            return True
        return self._change_speaker_connected(base_cmd)

    def _find_speaker(self, id=None, name=None, keywords=[]):
        caller = sys._getframe(1).f_code.co_name
        speakers = self.get_speakers()
        selected_speaker = None
        if not name and not id and not keywords:
            raise ValueError(f'{caller} called with no parameters.'
                             '\n\t\t\tmust pass one of the following: id, name, or keywords')
        elif [bool(name), bool(id), bool(keywords)].count(True) > 1:
            raise ValueError(f'only one keyword parameter can be passed to {caller}.'
                             '\n\t\t\tmust pass only one: id, name, or keywords')
        elif id:
            for speaker in speakers.values():
                if speaker.id.lower() == id.lower():
                    selected_speaker = speaker
            if not selected_speaker:
                raise ValueError(f'no speakers were found with the specified id:\n\t\t\t{id}')
        elif name:
            for speaker in speakers.values():
                if speaker.name.lower() == name.lower():
                    selected_speaker = speaker
            if not selected_speaker:
                raise ValueError(f'no speakers were found with the specified name:\n\t\t\t{name}')
        elif keywords:
            if type(keywords) is not list:
                raise ValueError('keywords parameter must be a list')
            for speaker in speakers.values():
                if all(kw.lower() in speaker.keywords for kw in keywords):
                    selected_speaker = speaker
            if not selected_speaker:
                raise ValueError(f'no speakers were found with the specified keywords:\n\t\t\t{keywords}')
        return selected_speaker

    def _change_speaker_connected(self, base_cmd):
        request_id, cmd = self._create_cmd(base_cmd)
        with socket.socket() as s:
            if self._connect(s):
                s.send(cmd)
                for response in self._get_responses(s):
                    if 'replyID' in response and response['replyID'] == request_id:
                        return response['data']['success']

    def toggle_speakers(self):
        """Disconnect and reconnect all currently connected speakers.
        Solves problems when Airfoil gets in a bad state"""
        all_speakers = self.get_speakers()
        connected = []
        for speaker in all_speakers.values():
            if speaker.connected:
                connected.append(speaker)
        for speaker in connected:
            self.disconnect_speaker(id=speaker.id)
        for speaker in connected:
            self.connect_speaker(id=speaker.id)
        

    def get_sources(self, audio_device=True, running_apps=True,
                    recent_apps=True, system_audio=True):
        base_cmd = {"request": "getSourceList", "requestID": "-1",
                    "data": {"iconSize": 16, "scaleFactor": 1}}
        source = namedtuple('source', ['name', 'id', 'type', 'keywords', 'icon_b64'])
        request_id, cmd = self._create_cmd(base_cmd)
        with socket.socket() as sock:
            if self._connect(sock):
                sock.send(cmd)
                for response in self._get_responses(sock):
                    data = response['data']
                    if 'audioDevices' in data or 'runningApplications' in data or\
                       'recentApplications' in data or 'systemAudio' in data:
                        sources = {}

                        def add_to_source(src, type):
                            keywords = self._get_keywords(src['friendlyName'])
                            sources[src['friendlyName']] = source(src['friendlyName'], src['identifier'],
                                                                  type, keywords, src.get('icon', ''))
                        if audio_device:
                            for src in data.get('audioDevices', []):
                                add_to_source(src, type='audio_device')
                        if running_apps:
                            for src in data.get('runningApplications', []):
                                add_to_source(src, type='running_apps')
                        if recent_apps:
                            for src in data.get('recentApplications', []):
                                add_to_source(src, type='recent_apps')
                        if system_audio:
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
            for source in self.sources.values():
                if source.name == 'System Audio':
                    selected_source = source
        elif id:
            for source in self.sources.values():
                if source.id.lower() == id.lower():
                    selected_source = source
            if not selected_source:
                raise ValueError(f'no source with specified id was found: {id}')
        elif name:
            for source in self.sources.values():
                if source.name.lower() == name.lower():
                    selected_source = source
            if not selected_source:
                raise ValueError(f'no source with specified name was found: {name}')
        elif keywords:
            for source in self.sources.values():
                if all(kw.lower() in source.keywords for kw in keywords):
                    selected_source = source
            if not selected_source:
                raise ValueError(f'no source with specified keywords was found: {keywords}')

        print(f'setting airfoil source to {selected_source.name}')
        base_cmd['data']['type'] = types[selected_source.type]
        base_cmd['data']['identifier'] = selected_source.id
        request_id, cmd = self._create_cmd(base_cmd)
        with socket.socket() as sock:
            if self._connect(sock):
                sock.send(cmd)
                for response in self._get_responses(sock):
                    if response.get('replyID', None) == request_id:
                        try:
                            return response['data']['success']
                        except KeyError as e:
                            # switching from playing source (tested system audio and spotify) to microphone always
                            # generates error 500 from airfoil
                            # {'replyID': '209', 'errorCode': 500, 'errExplanation':
                            # 'Object reference not set to an instance of an object.'}
                            # After getting this response, audio will not work after switching back to spotify
                            # until you disconnect/reconnect speakers. same behavior from airfoil satellite
                            # creating toggle speakers helper to do this automatically
                            print(response)
                            return False

    def get_current_source(self, machine_icon=False, album_art=False,
                           source_icon=False, track_meta=False):
        base_cmd = \
            {"data":
                {"scaleFactor": 2,
                 "requestedData":
                 {"machineIconAndScreenshot": 300, "albumArt": 300, "icon": 32,
                  "artist": "true", "album": "true", "title": "true",
                  "sourceName": "true", "bundleid": "true",
                  "trackMetadataAvailable": "true", "remoteControlAvailable": "true"}
                },
             "_replyTypes": [
                 "subscribe", "getSourceMetadata", "connectToSpeaker", "disconnectSpeaker",
                 "setSpeakerVolume", "getSourceList", "remoteCommand", "selectSource"],
             "request": "getSourceMetadata",
             "requestID": "-1"}
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
        with socket.socket() as sock:
            if self._connect(sock):
                sock.send(cmd)
                for response in self._get_responses(sock):
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

    def set_volume(self, speaker, volume):
        pass








a = Airfoil.get_first_airfoil()
# a.watch()
# src = a.get_current_source()
# print(src)
# a.set_source(id=r'C:\Users\jeremy\AppData\Roaming\Spotify\spotify.exe')
# for i in range(0, 4):
# a.set_source(keywords=['usb'])
# a.set_source(name='Spotify')
# a.set_source(name='System Audio')
print(a.get_speakers())
# a.disconnect_speaker(id='Chromecast-Audio-99130c3591fa2bbff26b770eda819eff@Bedroom speaker')
a.connect_speaker(keywords=['bedroom'])
# a.toggle_speakers()
# a.set_source()
# a.disconnect_speaker("SHIELD-Android-TV-fd75fa2dbc4e513427f5926062f037b3@Bedroom Shield")
# a._get_keywords("Microphone (Generic USB Audio Device   )")
# for k, v in a.get_sources().items():
#     print('name: ', k)
#     print('  id: ', v['id'])
