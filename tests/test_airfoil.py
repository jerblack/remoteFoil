import pytest
from airfoil import Airfoil
from airfoil_finder import AirfoilFinder
affect_airfoil = False
airfoil = AirfoilFinder.get_first_airfoil()
airfoil_ip = '192.168.0.50'
airfoil_name = 'server'
speaker_id = 'Chromecast-Audio-99130c3591fa2bbff26b770eda819eff@Bedroom speaker'
speaker_name = 'Bedroom speaker'
speaker_keywords = ['bedroom', 'speaker']
source_name = 'System Audio'
source_id = 'windows.systemaudio'
source_keywords = ['system', 'audio']

def test_is_airfoil():
    assert type(airfoil) is Airfoil

def test_other_airfoils():
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

def test_get_keywords():
    input = '_hello}GOODBYE|123.789\n     tomorrow,afternoon'
    output = ['hello', 'goodbye', '123', '789', 'tomorrow', 'afternoon']
    result = airfoil.get_keywords(input)
    assert result == output

def test_parse_volume():
    assert airfoil._parse_volume(-1) == 0
    assert airfoil._parse_volume(-1.25) == 0
    assert airfoil._parse_volume('none') == 0
    assert airfoil._parse_volume('full') == 1.0
    assert airfoil._parse_volume('mid') == 0.5
    assert airfoil._parse_volume('20%') == 0.2
    # assert airfoil._parse_volume(1.1) == 11/1000
    assert airfoil._parse_volume(20) == 0.2
    assert airfoil._parse_volume(100) == 1.0
    assert airfoil._parse_volume(1000) == 1.0

def test_get_speakers():
    speakers = airfoil.get_speakers()
    assert type(speakers) is list
    assert len(speakers[0]) == 7
    s = speakers[0]
    assert hasattr(s, 'name') and type(s.name) is str
    assert hasattr(s, 'id') and type(s.id) is str
    assert hasattr(s, 'type') and type(s.type) is str
    assert hasattr(s, 'password') and type(s.password) is bool
    assert hasattr(s, 'keywords') and type(s.keywords) is list
    assert hasattr(s, 'volume') and type(s.volume) is float
    assert hasattr(s, 'connected') and type(s.volume) is float

def test_find_speaker():
    s = airfoil.find_speaker(id=speaker_id)
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
    assert s.name == speaker_name
    assert s.id == speaker_id

def test_find_source():
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

def set_source():
    s = airfoil.set_source(name=source_name)
    # current_source(source_name='System Audio', source_has_track_metadata=False,
    #                source_controllable=False, track_album=None, track_artist=None,
    #                track_title=None, track_album_art=None, source_icon=None, system_icon=None)
    assert hasattr(s, 'source_name') and type(s.source_name) is str
    assert hasattr(s, 'source_has_track_metadata') and type(s.source_has_track_metadata) is bool
    assert hasattr(s, 'source_controllable') and type(s.source_controllable) is bool
    assert hasattr(s, 'track_album') and type(s.track_album) in [str, None]
    assert hasattr(s, 'track_artist') and type(s.track_artist) in [str, None]
    assert hasattr(s, 'track_album_art') and type(s.track_album_art) in [str, None]
    assert hasattr(s, 'source_icon') and type(s.source_icon) in [str, None]
    assert hasattr(s, 'system_icon') and type(s.system_icon) in [str, None]
    assert s.source_name == source_name
    s = airfoil.set_source(id=source_id)
    assert s.source_name == source_name
    s = airfoil.set_source(keywords=source_keywords)
    assert s.source_name == source_name



