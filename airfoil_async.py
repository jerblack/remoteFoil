import asyncio, json, sys, copy, random
from collections import namedtuple


class AirfoilAsync(object):

    def __init__(self, ip, port, name, loop=None):
        self.loop = loop if loop else asyncio.get_event_loop()
        self.ip = ip
        self.port = port
        self.name = name
        self.sources = []
        self.speakers = []
        self.muted_speakers = {}
        self.current_source = None

    # def run_in_loop(self, task):
    #     return self.loop.run_until_complete(asyncio.ensure_future(task, loop=self.loop))

    def run_in_loop(self, task):
        try:
            response = self.loop.run_until_complete(asyncio.ensure_future(task, loop=self.loop))
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()
        return response

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

    async def _connect(self, sock):
        hello = b"com.rogueamoeba.protocol.slipstreamremote\nmajorversion=1,minorversion=5\nOK\n"
        acceptable_version = "majorversion=1,minorversion=5"
        reader, writer = sock
        writer.write(hello)
        response = await reader.read(128)
        return acceptable_version in response.decode()

    async def _get_responses(self, cmd):
        max_bytes = 4096
        reader, writer = await asyncio.open_connection(self.ip, self.port, loop=self.loop)
        self.reader, self.writer = reader, writer
        if await self._connect((reader, writer)):
            writer.write(cmd)
            while True:
                data = await reader.readuntil(b';')
                # b'OK\n2211;' -> 2211
                num_bytes = int(''.join([n for n in data.decode() if n.isdigit()]))
                buffer = b''
                while num_bytes > 1:
                    get_bytes = max_bytes if num_bytes > max_bytes else num_bytes
                    data = await reader.read(get_bytes)
                    buffer += data
                    num_bytes = num_bytes - len(data)
                yield json.loads(buffer)

    async def _get_result(self, base_cmd):
        request_id, cmd = self._create_cmd(base_cmd)
        async for response in self._get_responses(cmd):
            if 'replyID' in response and response['replyID'] == request_id:
                return response['data']['success']

    async def find_speaker(self, id=None, name=None, keywords=[]):
        caller = sys._getframe(1).f_code.co_name
        speakers = await self.get_speakers()
        selected_speaker = None
        if not name and not id and not keywords:
            raise ValueError(f'{caller} called with no parameters.'
                             '\n\t\t\tmust pass one of the following: id, name, or keywords')
        elif [bool(name), bool(id), bool(keywords)].count(True) > 1:
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
        return selected_speaker

    async def watch(self):
        base_cmd = {"request": "subscribe", "requestID": "-1", "data": {
            "notifications": ["sourceMetadataChanged", "remoteControlChangedRequest", "speakerConnectedChanged",
                              "speakerListChanged",  "speakerNameChanged", "speakerPasswordChanged",
                              "speakerVolumeChanged"]}}
        _, cmd = self._create_cmd(base_cmd)
        async for response in self._get_responses(cmd):
            yield response

    async def _media_cmd(self, kind):
        base_cmd = {"data": {"commandName": kind},  "_replyTypes":
            ["subscribe", "getSourceMetadata", "connectToSpeaker", "disconnectSpeaker",
             "setSpeakerVolume", "getSourceList", "remoteCommand", "selectSource"],
             "request": "remoteCommand", "requestID": "-1"}
        return await self._get_result(base_cmd)

    async def play_pause(self):
        return await self._media_cmd("PlayPause")

    async def next_track(self):
        return await self._media_cmd("NextTrack")

    async def last_track(self):
        return await self._media_cmd("PreviousTrack")

    async def get_speakers(self):
        base_cmd = {"data": { "notifications":
            ["speakerListChanged", "speakerConnectedChanged", "speakerPasswordChanged",
             "speakerVolumeChanged", "speakerNameChanged", "remoteControlChangedRequest"]},
                    "_replyTypes": ["subscribe", "getSourceMetadata", "connectToSpeaker", "disconnectSpeaker",
                                    "setSpeakerVolume", "getSourceList", "remoteCommand", "selectSource"],
                    "request": "subscribe", "requestID": "-1"}
        speaker = namedtuple('speaker', ['name', 'type', 'id', 'volume', 'connected', 'password', 'keywords'])
        request_id, cmd = self._create_cmd(base_cmd)
        async for response in self._get_responses(cmd):
            if 'data' in response:
                if 'speakers' in response['data']:
                    speakers = []
                    for s in response['data']['speakers']:
                        keywords = self.get_keywords(s.get('name'))
                        spk = speaker(s.get('name'), s.get('type'), s.get('longIdentifier'), s.get('volume'),
                                      s.get('connected'), s.get('password'), keywords)
                        speakers.append(spk)
                    self.speakers = speakers
                    return speakers

    async def connect_speaker(self, *, id=None, name=None, keywords=[]):
        base_cmd = {"request": "connectToSpeaker", "requestID": "-1",
                    "data": {"longIdentifier": None}}
        selected_speaker = await self.find_speaker(id, name, keywords)
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        if selected_speaker.connected:
            print(f'speaker \'{selected_speaker.name}\' is already connected')
            return True
        return await self._get_result(base_cmd)

    async def disconnect_speaker(self, *, id=None, name=None, keywords=[]):
        base_cmd = {"request": "disconnectSpeaker", "requestID": "-1",
                    "data": {"longIdentifier": None}}
        selected_speaker = await self.find_speaker(id, name, keywords)
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        if not selected_speaker.connected:
            print(f'speaker \'{selected_speaker.name}\' is already disconnected')
            return True
        return await self._get_result(base_cmd)

    async def toggle_speaker(self, *, id=None, name=None, keywords=[]):
        """Disconnect (if connected) and reconnect specified speaker.
        Solves problems when Airfoil gets in a bad state"""
        selected_speaker = await self.find_speaker(id, name, keywords)
        result = True
        if selected_speaker.connected:
            result = await self.disconnect_speaker(id=selected_speaker.id)
        if result:
            return await self.connect_speaker(id=selected_speaker.id)
        else:
            return result

    async def toggle_speakers(self):
        """Disconnect and reconnect all currently connected speakers.
        Solves problems when Airfoil gets in a bad state"""
        all_speakers = await self.get_speakers()
        connected = []
        for speaker in all_speakers:
            if speaker.connected:
                connected.append(speaker)
        for speaker in connected:
            await self.disconnect_speaker(id=speaker.id)
        for speaker in connected:
            await self.connect_speaker(id=speaker.id)
        return True

    async def get_sources(self, source_icon=False):
        base_cmd = {"request": "getSourceList", "requestID": "-1",
                    "data": {"iconSize": 10, "scaleFactor": 1}}
        source = namedtuple('source', ['name', 'id', 'type', 'keywords', 'icon'])
        request_id, cmd = self._create_cmd(base_cmd)
        async for response in self._get_responses(cmd):
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

    async def set_source(self, *, name=None, id=None, keywords=[]):
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
            await self.get_sources()
        await self.get_current_source()
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
        async for response in self._get_responses(cmd):
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

    async def get_current_source(self, machine_icon=False, album_art=False, source_icon=False, track_meta=False):
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

        async for response in self._get_responses(cmd):
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

    async def set_volume(self, volume, *, id=None, name=None, keywords=[]):
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data": {"longIdentifier": None, "volume": None}}
        if type(volume) in [float, int]:
            if volume > 1 or volume < 0:
                raise ValueError('volume must a float or int from 0.0 to 1.0')
            base_cmd['data']['volume'] = volume
        else:
            raise ValueError(f'volume must be a \'float\', not \'{type(volume)}\'')
        selected_speaker = await self.find_speaker(id, name, keywords)
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        return await self._get_result(base_cmd)

    async def fade_volume(self, end_volume, seconds, *, ticks=10, id=None, name=None, keywords=[]):
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
        if not type(end_volume) in [float, int]:
            raise ValueError(f'volume must be a \'float\' or \'int\', not \'{type(end_volume)}\'')
        if not type(seconds) in [float, int]:
            raise ValueError(f'seconds must be a \'float\' or \'int\', not \'{type(seconds)}\'')
        if type(ticks) is not int:
            raise ValueError(f'ticks must be an \'int\', not \'{type(ticks)}\'')
        if end_volume > 1 or end_volume < 0:
            raise ValueError('volume must a float or int from 0.0 to 1.0')

        selected_speaker = await self.find_speaker(id, name, keywords)
        current_volume = selected_speaker.volume
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        wait = round(seconds / ticks, 4)
        increments = round((end_volume - current_volume)/ticks, 6)

        for i in range(0, ticks):
            current_volume += increments
            base_cmd['data']['volume'] = round(current_volume, 6)
            if i == ticks-1:
                base_cmd['data']['volume'] = end_volume
            await self._get_result(base_cmd)
            await asyncio.sleep(wait)

    async def fade_some(self, end_volume, seconds, *, ticks=10, ids=[], names=[]):
        """
        fade_volumes will change the volume of a collection of speakers simultaneously over a specified period of
        time
        :param end_volume
        :param seconds
        :param ticks
        :param ids
        :param names
        """
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data": {"longIdentifier": None, "volume": None}}
        if not type(end_volume) in [float, int]:
            raise ValueError(f'volume must be a \'float\' or \'int\', not \'{type(end_volume)}\'')
        if not type(seconds) in [float, int]:
            raise ValueError(f'seconds must be a \'float\' or \'int\', not \'{type(seconds)}\'')
        if type(ticks) is not int:
            raise ValueError(f'ticks must be an \'int\', not \'{type(ticks)}\'')
        if end_volume > 1 or end_volume < 0:
            raise ValueError('volume must a float or int from 0.0 to 1.0')
        if type(ids) is not list:
            raise ValueError(f'ids must be a list of speaker ids, not \'{type(ids)}\'')
        if type(names) is not list:
            raise ValueError(f'names must be a list of speaker names, not \'{type(names)}\'')
        if (not ids and not names) or (ids and names):
            raise ValueError('fade_volumes must be called with either a list of speaker ids or a list of speaker names'
                             '\n\t\t\tprovide one or the other, but not both.')
        await self.get_speakers()
        speakers = []
        wait = round(seconds / ticks, 4)

        for speaker in self.speakers:
            if (ids and speaker.id in ids) or (names and speaker.name in names):
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
                await self._get_result(speaker['cmd'])
            await asyncio.sleep(wait)

    async def fade_all(self, end_volume, seconds, *, ticks=10):
        await self.get_speakers()
        await self.fade_some(end_volume, seconds, ticks=ticks,
                             ids=[speaker.id for speaker in self.speakers if speaker.connected])

    async def mute(self, *, id=None, name=None, keywords=[]):
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data": {"longIdentifier": None, "volume": 0}}
        selected_speaker = await self.find_speaker(id, name, keywords)
        if selected_speaker.volume:
            self.muted_speakers[selected_speaker.id] = selected_speaker
            base_cmd['data']['longIdentifier'] = selected_speaker.id
            await self._get_result(base_cmd)
            return selected_speaker.volume
        return 0.0

    async def unmute(self, *, default_volume=1.0, id=None, name=None, keywords=[]):
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data": {"longIdentifier": None, "volume": None}}
        selected_speaker = await self.find_speaker(id, name, keywords)
        base_cmd['data']['longIdentifier'] = selected_speaker.id
        if not selected_speaker.volume:
            muted_speaker = self.muted_speakers.get(selected_speaker.id, None)
            if muted_speaker:
                base_cmd['data']['volume'] = muted_speaker.volume
                del self.muted_speakers[selected_speaker.id]
            else:
                base_cmd['data']['volume'] = default_volume
            await self._get_result(base_cmd)
            return base_cmd['data']['volume']
        else:
            return selected_speaker.volume

    async def mute_some(self, *, ids=[], names=[]):
        if type(ids) is not list:
            raise ValueError(f'ids must be a list of speaker ids, not \'{type(ids)}\'')
        if type(names) is not list:
            raise ValueError(f'names must be a list of speaker names, not \'{type(names)}\'')
        if (not ids and not names) or (ids and names):
            raise ValueError('mute_some must be called with either a list of speaker ids or a list of speaker names'
                             '\n\t\t\tprovide one or the other, but not both.')
        await self.get_speakers()
        muted = {}
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data": {"longIdentifier": None, "volume": 0}}
        for speaker in self.speakers:
            if (ids and speaker.id in ids) or (names and speaker.name in names):
                if speaker.volume:
                    cmd = copy.deepcopy(base_cmd)
                    cmd['data']['longIdentifier'] = speaker.id
                    self.muted_speakers[speaker.id] = muted[speaker.id] = speaker
                    await self._get_result(cmd)
                else:
                    muted[speaker.id] = self.muted_speakers.get(speaker.id, speaker)
        return muted

    async def unmute_some(self, *, ids=[], names=[], default_volume=1.0):
        if type(ids) is not list:
            raise ValueError(f'ids must be a list of speaker ids, not \'{type(ids)}\'')
        if type(names) is not list:
            raise ValueError(f'names must be a list of speaker names, not \'{type(names)}\'')
        if (not ids and not names) or (ids and names):
            raise ValueError('unmute_some must be called with either a list of speaker ids or a list of speaker names'
                             '\n\t\t\tprovide one or the other, but not both.')
        await self.get_speakers()
        unmuted = {}
        base_cmd = {"request": "setSpeakerVolume", "requestID": "-1", "data": {"longIdentifier": None, "volume": 0}}
        for speaker in self.speakers:
            if (ids and speaker.id in ids) or (names and speaker.name in names):
                if not speaker.volume:
                    cmd = copy.deepcopy(base_cmd)
                    cmd['data']['longIdentifier'] = speaker.id
                    if speaker.id in self.muted_speakers:
                        volume = self.muted_speakers[speaker.id].volume
                    else:
                        volume = default_volume
                    cmd['data']['volume'] = volume
                    unmuted[speaker.id] = volume
                    await self._get_result(cmd)
                else:
                    unmuted[speaker.id] = speaker.volume
        return unmuted

    async def mute_all(self):
        await self.get_speakers()
        await self.mute_some(ids=[speaker.id for speaker in self.speakers if speaker.volume])
        return True

    async def unmute_all(self, default_volume=1.0):
        await self.get_speakers()
        await self.unmute_some(ids=[speaker.id for speaker in self.speakers if not speaker.volume],
                               default_volume=default_volume)
        return True

    async def test(self):
        try:
            print(await self.mute_all())
            await asyncio.sleep(1)
            print(await self.unmute_all())
        finally:
            self.writer.close()

# a = AirfoilAsync('192.168.0.50', 56918, 'server')
# a.run_in_loop(a.test())
