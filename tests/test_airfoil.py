import pytest
from airfoil import Airfoil, ON, OFF, MIDDLE
from airfoil_finder import AirfoilFinder
from tests import *

class TestAirfoil:

    @pytest.fixture(scope='session')
    def airfoil(self):
        return AirfoilFinder.get_first_airfoil()

    def test_is_airfoil(self, airfoil):
        assert type(airfoil) is Airfoil

    def test_other_airfoils(self):
        a_by_ip = AirfoilFinder.get_airfoil_by_ip(airfoil_ip)
        assert type(a_by_ip) is Airfoil
        assert a_by_ip.name == airfoil_name
        a_by_name = AirfoilFinder.get_airfoil_by_name(airfoil_name)
        assert type(a_by_name) is Airfoil
        assert a_by_name.ip == airfoil_ip

        for timeout in [10, None, 2, 1000]:
            a_by_ip = AirfoilFinder.get_airfoil_by_ip(airfoil_ip, timeout=timeout)
            assert type(a_by_ip) is Airfoil
            assert a_by_ip.name == airfoil_name
            a_by_name = AirfoilFinder.get_airfoil_by_name(airfoil_name, timeout=timeout)
            assert type(a_by_name) is Airfoil
            assert a_by_name.ip == airfoil_ip

    def test_get_keywords(self, airfoil):
        input = '_hello}GOODBYE|123.789\n     tomorrow,afternoon'
        output = ['hello', 'goodbye', '123', '789', 'tomorrow', 'afternoon']
        result = airfoil.get_keywords(input)
        assert result == output

    def test_parse_volume(self, airfoil):
        assert airfoil._parse_volume(-1) == 0
        assert airfoil._parse_volume(-1.25) == 0
        assert airfoil._parse_volume('none') == 0
        assert airfoil._parse_volume('full') == 1.0
        assert airfoil._parse_volume('mid') == 0.5
        assert airfoil._parse_volume('20%') == 0.2
        assert pytest.approx(airfoil._parse_volume(1.1), 0.00000001) == 11/1000
        assert airfoil._parse_volume(20) == 0.2
        assert airfoil._parse_volume(100) == 1.0
        assert airfoil._parse_volume(1000) == 1.0

    def test_get_speakers(self, airfoil):
        speakers = airfoil.get_speakers()
        assert type(speakers) is list
        for s in speakers:
            assert len(s) == 7
            assert hasattr(s, 'name') and type(s.name) is str
            assert hasattr(s, 'id') and type(s.id) is str
            assert hasattr(s, 'type') and type(s.type) is str
            assert hasattr(s, 'password') and type(s.password) is bool
            assert hasattr(s, 'keywords') and type(s.keywords) is list
            assert hasattr(s, 'volume') and type(s.volume) is float
            assert hasattr(s, 'connected') and type(s.volume) is float
            if s.type in ['chromecast', 'airplay']:
                assert '@' in s.id
                assert s.name in s.id

    def test_get_sources(self, airfoil):
        sources = airfoil.get_sources()
        assert type(sources) is list
        for s in sources:
            assert type(s) is airfoil.source
            assert len(s) == 5
            assert hasattr(s, 'name') and type(s.name) is str
            assert hasattr(s, 'id') and type(s.id) is str
            assert hasattr(s, 'type') and type(s.type) is str
            assert hasattr(s, 'keywords') and type(s.keywords) is list
            assert hasattr(s, 'icon') and type(s.icon) is str

    def test_get_current_source(self, airfoil):
        s = airfoil.get_current_source()
        assert type(s) is airfoil.current_source
        assert len(s) == 9
        assert hasattr(s, 'source_name') and type(s.source_name) is str
        assert hasattr(s, 'source_has_track_metadata')
        assert type(s.source_has_track_metadata) is bool
        assert hasattr(s, 'source_controllable')
        assert type(s.source_controllable) is bool
        assert hasattr(s, 'track_album')
        assert type(s.track_album) in [str, type(None)]
        assert hasattr(s, 'track_artist')
        assert type(s.track_artist) in [str, type(None)]
        assert hasattr(s, 'track_title')
        assert type(s.track_title) in [str, type(None)]
        assert hasattr(s, 'track_album_art')
        assert s.track_album_art is None
        assert hasattr(s, 'source_icon')
        assert s.source_icon is None
        assert hasattr(s, 'system_icon')
        assert s.system_icon is None

    def test_find_speaker(self, airfoil):
        s = airfoil.find_speaker(id=speaker_id)
        assert type(s) is airfoil.speaker
        assert hasattr(s, 'name') and type(s.name) is str
        assert s.name == speaker_name
        assert s.id == speaker_id
        with pytest.raises(AttributeError):
            s.icon = 'hello'
        assert hasattr(s, 'id') and type(s.id) is str
        assert hasattr(s, 'type') and type(s.type) is str
        assert hasattr(s, 'password') and type(s.password) is bool
        assert hasattr(s, 'keywords') and type(s.keywords) is list
        assert hasattr(s, 'volume') and type(s.volume) is float
        assert hasattr(s, 'connected') and type(s.connected) is bool

        s = airfoil.find_speaker(name=speaker_name)
        assert type(s) is airfoil.speaker
        assert hasattr(s, 'name') and type(s.name) is str
        assert s.name == speaker_name
        assert s.id == speaker_id
        assert hasattr(s, 'id') and type(s.id) is str
        assert hasattr(s, 'type') and type(s.type) is str
        assert hasattr(s, 'password') and type(s.password) is bool
        assert hasattr(s, 'keywords') and type(s.keywords) is list
        assert hasattr(s, 'volume') and type(s.volume) is float
        assert hasattr(s, 'connected') and type(s.connected) is bool

        s = airfoil.find_speaker(keywords=speaker_keywords)
        assert type(s) is airfoil.speaker
        assert hasattr(s, 'name') and type(s.name) is str
        assert s.name == speaker_name
        assert s.id == speaker_id
        assert hasattr(s, 'id') and type(s.id) is str
        assert hasattr(s, 'type') and type(s.type) is str
        assert hasattr(s, 'password') and type(s.password) is bool
        assert hasattr(s, 'keywords') and type(s.keywords) is list
        assert hasattr(s, 'volume') and type(s.volume) is float
        assert hasattr(s, 'connected') and type(s.connected) is bool

        s = airfoil.find_speaker(unknown='speaker--++..bedroom')
        assert type(s) is airfoil.speaker
        assert s.name == speaker_name
        assert s.id == speaker_id

    def test_find_source(self, airfoil):
        s = airfoil.find_source(id=source_id)
        # source(name='System Audio', id='windows.systemaudio', type='system_audio',
        #        keywords=['system', 'audio'], icon='')
        assert hasattr(s, 'name') and type(s.name) is str
        assert hasattr(s, 'type') and type(s.type) is str
        assert hasattr(s, 'keywords') and type(s.keywords) is list
        assert hasattr(s, 'id') and type(s.id) is str
        assert hasattr(s, 'icon') and type(s.icon) is str
        assert s.name == source_name
        assert s.id == source_id
        assert s.keywords == source_keywords
        s = airfoil.find_source(name=source_name)
        assert s.name == source_name
        assert s.id == source_id
        assert s.keywords == source_keywords
        s = airfoil.find_source(keywords=source_keywords)
        assert s.name == source_name
        assert s.id == source_id
        assert s.keywords == source_keywords

    @changes_sources
    def test_set_source(self, airfoil):
        s = airfoil.set_source(name=source_name)
        # current_source(source_name='System Audio', source_has_track_metadata=False,
        #                source_controllable=False, track_album=None, track_artist=None,
        #                track_title=None, track_album_art=None, source_icon=None, system_icon=None)
        assert hasattr(s, 'source_name')
        assert type(s.source_name) is str
        assert hasattr(s, 'source_has_track_metadata')
        assert type(s.source_has_track_metadata) is bool
        assert hasattr(s, 'source_controllable')
        assert type(s.source_controllable) is bool
        assert hasattr(s, 'track_album')
        assert type(s.track_album) in [str, type(None)]
        assert hasattr(s, 'track_artist')
        assert type(s.track_artist) in [str, type(None)]
        assert hasattr(s, 'track_album_art')
        assert type(s.track_album_art) in [str, type(None)]
        assert hasattr(s, 'source_icon')
        assert type(s.source_icon) in [str, type(None)]
        assert hasattr(s, 'system_icon')
        assert type(s.system_icon) in [str, type(None)]
        assert s.source_name == source_name
        s = airfoil.set_source(id=source_id)
        assert s.source_name == source_name
        s = airfoil.set_source(keywords=source_keywords)
        assert s.source_name == source_name

    @changes_sources
    def test_media_keys(self, airfoil):
        assert type(airfoil.play_pause()) is bool
        assert type(airfoil.next_track()) is bool
        assert type(airfoil.last_track()) is bool

    @changes_speakers
    def test_disconnect_speaker(self, airfoil):
        results = airfoil.disconnect_speaker(name=speaker_name)
        assert type(results) is list
        s = results[0]
        assert type(s) is airfoil.speaker
        assert s.name == speaker_name
        assert not s.connected

    @changes_speakers
    def test_connect_speaker(self, airfoil):
        results = airfoil.connect_speaker(name=speaker_name)
        assert type(results) is list
        s = results[0]
        assert type(s) is airfoil.speaker
        assert s.name == speaker_name
        assert s.connected

    @changes_speakers
    def test_disconnect_connect_speakers_multiple(self, airfoil):
        s = airfoil.disconnect_speaker(name=speaker_name)[0]
        assert type(s) is airfoil.speaker
        assert s.name == speaker_name
        assert not s.connected
        s = airfoil.connect_speaker(name=speaker_name)[0]
        assert type(s) is airfoil.speaker
        assert s.name == speaker_name
        assert s.connected
        s = airfoil.disconnect_speaker(id=speaker_id)[0]
        assert type(s) is airfoil.speaker
        assert s.name == speaker_name
        assert not s.connected
        s = airfoil.connect_speaker(id=speaker_id)[0]
        assert type(s) is airfoil.speaker
        assert s.name == speaker_name
        assert s.connected
        s = airfoil.disconnect_speaker(keywords=speaker_keywords)[0]
        assert type(s) is airfoil.speaker
        assert s.name == speaker_name
        assert not s.connected
        s = airfoil.connect_speaker(keywords=speaker_keywords)[0]
        assert type(s) is airfoil.speaker
        assert s.name == speaker_name
        assert s.connected

    @changes_speakers
    def test_toggle_speaker_from_connected_state(self, airfoil):
        # test from connected state
        s = airfoil.connect_speaker(name=speaker_name)[0]
        assert s.connected
        results = airfoil.toggle_speaker(name=speaker_name)
        assert type(results) is list
        s = results[0]
        assert type(s) is airfoil.speaker
        assert s.name == speaker_name
        assert s.connected

    @changes_speakers
    def test_toggle_speaker_from_disconnected_state(self, airfoil):
        # test from disconnected state
        s = airfoil.disconnect_speaker(name=speaker_name)[0]
        assert not s.connected
        results = airfoil.toggle_speaker(name=speaker_name)
        assert type(results) is list
        s = results[0]
        assert type(s) is airfoil.speaker
        assert s.name == speaker_name
        assert s.connected

    @changes_speakers
    def test_disconnect_connect_multiple_speakers(self, airfoil):
        result = airfoil.disconnect_speakers(
            names=[speaker_name, speaker_name2])
        for s in result:
            assert not s.connected
        result = airfoil.connect_speakers(
            names=[speaker_name, speaker_name2])
        for s in result:
            assert s.connected

        result = airfoil.disconnect_some(
            ids=[speaker_id, speaker_id2])
        for s in result:
            assert not s.connected
        result = airfoil.connect_some(
            ids=[speaker_id, speaker_id2])
        for s in result:
            assert s.connected

    @changes_speakers
    def test_toggle_multiple_speakers_from_disconnected_state_by_name(self, airfoil):
        result = airfoil.disconnect_speakers(ids=ids)
        for s in result:
            assert not s.connected
        result = airfoil.toggle_speakers(
            names=[speaker_name, speaker_name2])
        for s in result:
            assert s.connected

    @changes_speakers
    def test_toggle_multiple_speakers_from_disconnected_state_by_id(self, airfoil):
        result = airfoil.disconnect_speakers(ids=ids)
        for s in result:
            assert not s.connected
        result = airfoil.toggle_some(ids=ids)
        for s in result:
            assert s.connected

    @changes_speakers
    def test_toggle_multiple_speakers_from_connected_state_by_name(self, airfoil):
        result = airfoil.connect_speakers(ids=ids)
        for s in result:
            assert s.connected
        result = airfoil.toggle_speakers(names=names)
        for s in result:
            assert s.connected

    @changes_speakers
    def test_toggle_multiple_speakers_from_connected_state_by_id(self, airfoil):
        result = airfoil.connect_speakers(ids=ids)
        assert type(result) is list
        assert len(result) == 2
        for s in result:
            assert s.connected
        result = airfoil.toggle_some(ids=ids)
        for s in result:
            assert s.connected

    @changes_volumes
    def test_set_volume_speaker(self, airfoil):
        outsiders = {-100: 0.0, -1: 0.0, -1.5: 0.0, 20: 0.2, 100: 1.0,
                     100.1: 1.0, 1000.00002: 1, '20%': 0.2, '120%': 1.0,
                     '50': 0.5, '-20': 0.0}
        for v in [n/100 for n in range(0, 101, 4)] + OFF + MIDDLE + ON + \
                 [s for s in outsiders.keys()]:
            result = airfoil.set_volume(v, name=speaker_name)
            assert type(result) is list
            assert result
            s = result[0]
            assert type(s) is airfoil.speaker
            assert s.name == speaker_name
            if v not in ON + OFF + MIDDLE + [s for s in outsiders.keys()]:
                assert s.volume == v
            elif v in OFF:
                assert s.volume == 0.0
            elif v in MIDDLE:
                assert s.volume == 0.5
            elif v in ON:
                assert s.volume == 1.0
            elif v in outsiders.keys():
                assert s.volume == outsiders[v]
        with pytest.raises(ValueError):
            airfoil.set_volume('hello')
        with pytest.raises(TypeError):
            airfoil.set_volume()

    @changes_volumes
    def test_set_volume_speakers(self, airfoil):
        for v in [n/100 for n in range(0, 101, 4)] + OFF + MIDDLE + ON:
            result = airfoil.set_volumes(v, names=names)
            assert type(result) is list
            for s in result:
                assert type(s) is airfoil.speaker
                assert s.name in names
                if v not in ON + OFF + MIDDLE:
                    assert s.volume == v
                elif v in OFF:
                    assert s.volume == 0.0
                elif v in MIDDLE:
                    assert s.volume == 0.5
                elif v in ON:
                    assert s.volume == 1.0
            result = airfoil.set_volume_some(v, ids=ids)
            assert type(result) is list
            for s in result:
                assert type(s) is airfoil.speaker
                assert s.name in names
                if v not in ON + OFF + MIDDLE:
                    assert s.volume == v
                elif v in OFF:
                    assert s.volume == 0.0
                elif v in MIDDLE:
                    assert s.volume == 0.5
                elif v in ON:
                    assert s.volume == 1.0
        with pytest.raises(ValueError):
            airfoil.set_volume('hello')
        with pytest.raises(TypeError):
            airfoil.set_volume()

    @changes_volumes
    def test_set_volume_all(self, airfoil):
        for v in [n / 100 for n in range(0, 101, 4)]:
            result = airfoil.set_volume_all(v)
            assert type(result) is list
            for s in result:
                assert type(s) is airfoil.speaker
                assert s.volume == v
                assert s.connected
        with pytest.raises(ValueError):
            airfoil.set_volume('hello')
        with pytest.raises(TypeError):
            airfoil.set_volume()

    @changes_volumes
    def test_mute(self, airfoil):
        result = airfoil.mute(name=speaker_name)
        assert type(result) is list
        for s in result:
            assert type(s) is airfoil.speaker
            assert s.volume == 0.0

    @changes_volumes
    def test_unmute(self, airfoil):
        result = airfoil.set_volume(0, name=speaker_name)
        assert result[0].volume == 0.0
        result = airfoil.unmute(name=speaker_name)
        assert type(result) is list
        for s in result:
            assert type(s) is airfoil.speaker
            assert s.volume == 1.0

    @changes_volumes
    def test_unmute_default_volume(self, airfoil):
        for v in [r/100 for r in range(1, 101, 20)]:
            result = airfoil.set_volume(0, name=speaker_name)
            assert result[0].volume == 0.0
            result = airfoil.unmute(name=speaker_name, default_volume=v)
            assert type(result) is list
            for s in result:
                assert type(s) is airfoil.speaker
                assert s.volume == v

    @changes_volumes
    def test_unmute_some(self, airfoil):
        for v in [r/100 for r in range(1, 101, 20)]:
            result = airfoil.set_volumes(0, names=names)
            for s in result:
                assert s.volume == 0.0
            result = airfoil.unmutes(names=names, default_volume=v)
            assert type(result) is list
            for s in result:
                assert type(s) is airfoil.speaker
                assert s.volume == v

    @changes_volumes
    def test_fade_volume(self, airfoil):
        tests = [[0.0, 4, 3], [1.0, 4, 40], [0.4, 10, 120], [120, 12, 30]]
        for vol, seconds, ticks in tests:
            result = airfoil.fade_volume(
                vol, seconds, ticks=ticks, name=speaker_name)
            assert type(result) is list
            for s in result:
                assert type(s) is airfoil.speaker
                assert s.volume == vol

    @changes_volumes
    def test_fade_volumes(self, airfoil):
        tests = [[0.0, 4, 3], [1.0, 4, 40], [0.4, 10, 120], [120, 12, 30]]
        for vol, seconds, ticks in tests:
            result = airfoil.fade_some(
                vol, seconds, ticks=ticks, names=names)
            assert type(result) is list
            for s in result:
                assert type(s) is airfoil.speaker
                if 0 <= vol <= 1:
                    assert s.volume == vol

    @changes_volumes
    def test_fade_all(self, airfoil):
        tests = [[0.0, 4, 3], [1.0, 4, 40], [0.4, 10, 120], [120, 12, 30]]
        for vol, seconds, ticks in tests:
            result = airfoil.fade_all(vol, seconds, ticks=ticks)
            assert type(result) is list
            for s in result:
                assert type(s) is airfoil.speaker
                if 0 <= vol <= 1:
                    assert s.volume == vol
