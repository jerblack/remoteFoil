from flask import Flask, jsonify, request
from airfoil_finder import AirfoilFinder
import sys
finder = None
app = Flask(__name__)
TRUTHIES = ['true', 'yes', 'y', 't', '1', 'on', 'enabled']


def _error(name, reason):
    url = request.url.replace(request.url_root[:-1], '')
    return {'error': 404, 'url': url, 'name': name, 'reason': reason}


@app.route('/')
def get_airfoils():
    airfoils = []
    for af in finder.airfoils.values():
        airfoils.append({'name': af.name, 'ip': af.ip})
    return jsonify({'airfoils': airfoils})


def _airfoil_cmd(name, fn):
    name = name.lower()
    airfoil = finder.airfoils.get(name, None)
    if airfoil:
        return fn(airfoil)
    else:
        return _error(name, f'No airfoil instance found with name \'{name}\'')


def _get_ids_names():
    ids = [i for i in request.args.get('ids', '').split(',') if i]
    names = [n for n in request.args.get('names', '').split(',') if n]
    return ids, names


def _parse_speaker_cmd(name, speaker, functions, ids, names):
    if speaker == 'speakers':
        if names:
            return jsonify([c._asdict() for c in _airfoil_cmd(name, functions['names'])])
        elif ids:
            return jsonify([c._asdict() for c in _airfoil_cmd(name, functions['ids'])])
        else:
            return jsonify([c._asdict() for c in _airfoil_cmd(name, functions['all'])])
    else:
        return jsonify([c._asdict() for c in _speaker_cmd(name, speaker, functions['specific'])])


def _speaker_cmd(name, speaker, cmd):
    airfoil = finder.airfoils.get(name, None)
    match = None
    if airfoil:
        try:
            match = airfoil.find_speaker(name=speaker.lower().replace('_', ' '))
        except ValueError:
            keywords = airfoil.get_keywords(speaker)
            try:
                match = airfoil.find_speaker(keywords=keywords)
            except ValueError:
                try:
                    match = airfoil.find_speaker(id=speaker)
                except ValueError:
                    pass
        if match:
            return cmd(airfoil, match)
        else:
            return _error(name, f'No speaker found with name, id, or keywords: \'{speaker}\'')
    else:
        return _error(name, f'No airfoil instance found with name \'{name}\'')


def _media_button(name, cmd):
    cmds = {
        'play': lambda airfoil: airfoil.play_pause(),
        'next': lambda airfoil: airfoil.next_track(),
        'back': lambda airfoil: airfoil.last_track()
    }
    result = _airfoil_cmd(name, cmds[cmd])
    if result:
        return jsonify({'result': 'success'})
    else:
        source = _airfoil_cmd(name, lambda airfoil: airfoil.get_current_source())
        url = request.url.replace(request.url_root[:-1], '')
        fail = {'result': 'failed', 'url': url, 'name': name, 'reason': None}
        if not source.source_controllable:
            fail['reason'] = f'\'{source.source_name}\' cannot be remotely controlled by Airfoil'
        else:
            fail['reason'] = 'unknown'
        return jsonify(fail)


@app.route('/<name>/')
@app.route('/<name>')
def get_airfoil(name):
    return jsonify(_airfoil_cmd(name, lambda airfoil: {'airfoil': {'name': airfoil.name, 'ip': airfoil.ip}}))


@app.route('/<name>/pause/')
@app.route('/<name>/pause')
@app.route('/<name>/play/')
@app.route('/<name>/play')
@app.route('/<name>/play_pause/')
@app.route('/<name>/play_pause')
def play_pause(name):
    return _media_button(name, 'play')


@app.route('/<name>/skip/')
@app.route('/<name>/skip')
@app.route('/<name>/next/')
@app.route('/<name>/next')
@app.route('/<name>/next_track/')
@app.route('/<name>/next_track')
def next_track(name):
    return _media_button(name, 'next')


@app.route('/<name>/prev/')
@app.route('/<name>/prev')
@app.route('/<name>/last/')
@app.route('/<name>/last')
@app.route('/<name>/back/')
@app.route('/<name>/back')
@app.route('/<name>/prev_track/')
@app.route('/<name>/prev_track')
@app.route('/<name>/last_track/')
@app.route('/<name>/last_track')
def last_track(name):
    return _media_button(name, 'back')


@app.route('/<name>/sources/')
@app.route('/<name>/sources')
def get_sources(name):
    source_icon = request.args.get('source_icon', '').lower() in TRUTHIES
    sources = _airfoil_cmd(name, lambda airfoil: airfoil.get_sources(source_icon))
    return jsonify([s._asdict() for s in sources])


@app.route('/<name>/current_source/')
@app.route('/<name>/current_source')
@app.route('/<name>/source/')
@app.route('/<name>/source')
def get_current_source(name):
    source_name = request.args.get('name','')
    source_id = request.args.get('id','')
    keywords = [kw for kw in request.args.get('keywords').split(',') if kw]
    if source_name or source_id or keywords:
        return set_source(source_name=source_name, source_id=source_id, keywords=keywords)

    machine_icon = request.args.get('machine_icon', '').lower() == 'true'
    album_art = request.args.get('album_art', '').lower() == 'true'
    source_icon = request.args.get('source_icon', '').lower() == 'true'
    track_meta = request.args.get('track_meta', '').lower() == 'true'

    source = _airfoil_cmd(name, lambda airfoil: airfoil.get_current_source(
        machine_icon=machine_icon, album_art=album_art, source_icon=source_icon, track_meta=track_meta))
    return jsonify(source._asdict())

@app.route('/<name>/source/<source>/')
@app.route('/<name>/source/<source>')
def set_source(name, source='', source_name='', source_id='', keywords=[]):
    if [bool(source), bool(source_name), bool(source_id), bool(keywords)].count(True) > 1:
        return jsonify(_error(name, 'More than one parameter was specified for set_source'))

    airfoil = finder.airfoils.get(name, None)
    match = None
    if airfoil:
        pass
    else:
        return _error(name, f'No airfoil instance found with name \'{name}\'')





@app.route('/<name>/speakers/')
@app.route('/<name>/speakers')
def get_speakers(name):
    speakers = _airfoil_cmd(name, lambda airfoil: airfoil.get_speakers())
    speaker_list = []
    for s in speakers:
        speaker_list.append(s._asdict())
    return jsonify(speaker_list)

@app.route('/<name>/<speaker>/')
@app.route('/<name>/<speaker>')
def get_speaker(name, speaker):
    return jsonify(_speaker_cmd(name, speaker, lambda _, match: match._asdict()))

@app.route('/<name>/<speaker>/on/')
@app.route('/<name>/<speaker>/on')
@app.route('/<name>/<speaker>/yes/')
@app.route('/<name>/<speaker>/yes')
@app.route('/<name>/<speaker>/true/')
@app.route('/<name>/<speaker>/true')
@app.route('/<name>/<speaker>/connect/')
@app.route('/<name>/<speaker>/connect')
@app.route('/<name>/<speaker>/enable/')
@app.route('/<name>/<speaker>/enable')
def connect(name, speaker):
    return jsonify(_speaker_cmd(name, speaker, lambda airfoil, match: airfoil.connect_speaker(id=match.id)))

@app.route('/<name>/<speaker>/off/')
@app.route('/<name>/<speaker>/off')
@app.route('/<name>/<speaker>/no/')
@app.route('/<name>/<speaker>/no')
@app.route('/<name>/<speaker>/false/')
@app.route('/<name>/<speaker>/false')
@app.route('/<name>/<speaker>/disconnect/')
@app.route('/<name>/<speaker>/disconnect')
@app.route('/<name>/<speaker>/disable/')
@app.route('/<name>/<speaker>/disable')
def disconnect(name, speaker):
    return jsonify(_speaker_cmd(name, speaker, lambda airfoil, match: airfoil.disconnect_speaker(id=match.id)))


@app.route('/<name>/<speaker>/mute/')
@app.route('/<name>/<speaker>/mute')
def mute(name, speaker):
    ids, names = _get_ids_names()
    disconnected = request.args.get('disconnected', 'false').lower() in TRUTHIES

    functions = {'names':
         lambda airfoil: airfoil.mute_some(names=names, include_disconnected=disconnected),
                 'ids':
         lambda airfoil: airfoil.mute_some(ids=ids, include_disconnected=disconnected),
                 'all':
         lambda airfoil: airfoil.mute_all(include_disconnected=disconnected),
                 'specific':
         lambda airfoil, match: airfoil.mute(id=match.id)
                 }
    return _parse_speaker_cmd(name, speaker, functions, ids, names)


@app.route('/<name>/<speaker>/unmute/')
@app.route('/<name>/<speaker>/unmute')
@app.route('/<name>/<speaker>/unmute/<default_volume>/')
@app.route('/<name>/<speaker>/unmute/<default_volume>')
def unmute(name, speaker, default_volume=None):
    disconnected = request.args.get('disconnected', 'false').lower() in TRUTHIES
    default_volume = float(request.args.get('default_volume', 1.0) if not default_volume else default_volume)
    if default_volume < 0 or default_volume > 1:
        return jsonify(_error(name, 'the end_volume parameter for unmute must be between 0 and 1 with up to 6 digits '
                                    f'after the decimal point. for example:  /{name}/{speaker}/unmute/1.0  -or-  '
                                    f' /{name}/{speaker}/unmute?default_volume=0.654321'))
    ids, names = _get_ids_names()
    functions = {'names':
         lambda airfoil: airfoil.unmute_some(names=names, default_volume=default_volume,
                                             include_disconnected=disconnected),
                 'ids':
         lambda airfoil: airfoil.unmute_some(ids=ids, default_volume=default_volume,
                                             include_disconnected=disconnected),
                 'all':
         lambda airfoil: airfoil.unmute_all(default_volume=default_volume,
                                            include_disconnected=disconnected),
                 'specific':
         lambda airfoil, match: airfoil.unmute(id=match.id, default_volume=default_volume,
                                               include_disconnected=disconnected)
                 }
    return _parse_speaker_cmd(name, speaker, functions, ids, names)


@app.route('/<name>/<speaker>/fade/')
@app.route('/<name>/<speaker>/fade')
@app.route('/<name>/<speaker>/fade/<end_volume>/')
@app.route('/<name>/<speaker>/fade/<end_volume>')
@app.route('/<name>/<speaker>/fade/<end_volume>/<seconds>/')
@app.route('/<name>/<speaker>/fade/<end_volume>/<seconds>')
@app.route('/<name>/<speaker>/fade/<end_volume>/<seconds>/<ticks>/')
@app.route('/<name>/<speaker>/fade/<end_volume>/<seconds>/<ticks>')
def fade(name, speaker, end_volume=None, seconds=None, ticks=None):
    end_volume = float(request.args.get('end_volume', -1) if not end_volume else end_volume)
    seconds = float(request.args.get('seconds', 5) if not seconds else seconds)
    disconnected = request.args.get('disconnected', 'false').lower() in TRUTHIES
    if end_volume < 0 or end_volume > 1:
        return jsonify(_error(name, 'fade requires an end volume between 0 and 1 with up to 6 digits after the decimal point. '
                            f'for example:  /{name}/{speaker}/fade/0.7  -or-  /{name}/{speaker}/fade/0.35/10/100  -or- '
                            f' /{name}/{speaker}/fade?end_volume=0.654444&seconds=15&ticks=500'))
    if ticks and not ticks.isdigit():
        return jsonify(_error(name, 'the number given for ticks must be an integer greater than 0.'))
    ticks = int(request.args.get('ticks', 10) if not ticks else ticks)
    ids, names = _get_ids_names()
    functions = {'names':
        lambda airfoil: airfoil.fade_some(names=names, end_volume=end_volume, seconds=seconds, ticks=ticks,
                                          include_disconnected=disconnected),
                 'ids':
        lambda airfoil: airfoil.fade_some(ids=ids, end_volume=end_volume, seconds=seconds, ticks=ticks,
                                          include_disconnected=disconnected),
                 'all':
        lambda airfoil: airfoil.fade_all(end_volume=end_volume, seconds=seconds, ticks=ticks,
                                         include_disconnected=disconnected),
                 'specific':
        lambda airfoil, match: airfoil.fade_volume(id=match.id, end_volume=end_volume, seconds=seconds, ticks=ticks)}
    return _parse_speaker_cmd(name, speaker, functions, ids, names)

@app.route('/<name>/<speaker>/volume/')
@app.route('/<name>/<speaker>/volume')
@app.route('/<name>/<speaker>/volume/<level>/')
@app.route('/<name>/<speaker>/volume/<level>')
def volume(name, speaker, level=None):
    disconnected = request.args.get('disconnected', 'false').lower() in TRUTHIES
    level = float(request.args.get('level', -1) if level is None else level)
    if level < 0 or level > 1:
        return jsonify(_error(name, 'volume requires a level value between 0 and 1 with up to 6 digits after the'
                                    f' decimal point. for example:  /{name}/{speaker}/volume/0.7  -or  /{name}/'
                                    f'{speaker}/volume?level=0.354242'))
    ids, names = _get_ids_names()
    functions = {'names':
         lambda airfoil: airfoil.set_volumes(level, names=names, include_disconnected=disconnected),
                 'ids':
         lambda airfoil: airfoil.set_volumes(level, ids=ids, include_disconnected=disconnected),
                 'all':
         lambda airfoil: airfoil.set_volume_all(level, include_disconnected=disconnected),
                 'specific':
         lambda airfoil, match: airfoil.set_volume(level, id=match.id, include_disconnected=disconnected)
                 }
    return _parse_speaker_cmd(name, speaker, functions, ids, names)


if __name__=='__main__':
    cli = sys.modules['flask.cli']
    cli.show_server_banner = lambda *x: None
    finder = AirfoilFinder()
    app.run(host='0.0.0.0', port='80', threaded=True)

