import pytest

affects_sources = False
affects_speakers = False
affects_volumes = True
changes_sources = pytest.mark.skipif(
    not affects_sources, reason='test would makes changes to sources')
changes_speakers = pytest.mark.skipif(
    not affects_speakers, reason='test would makes changes to speakers')
changes_volumes = pytest.mark.skipif(
    not affects_volumes, reason='test would makes changes to volumes')

airfoil_ip = '192.168.0.50'
airfoil_name = 'server'
speaker_id = 'Chromecast-Audio-99130c3591fa2bbff26b770eda819eff@Bedroom speaker'
speaker_name = 'Bedroom speaker'
speaker_keywords = ['bedroom', 'speaker']
speaker_name2 = 'Bedroom Shield'
speaker_id2 = 'SHIELD-Android-TV-fd75fa2dbc4e513427f5926062f037b3@Bedroom Shield'
names = [speaker_name, speaker_name2]
ids = [speaker_id, speaker_id2]
source_name = 'System Audio'
source_id = 'windows.systemaudio'
source_keywords = ['system', 'audio']