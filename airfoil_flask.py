from flask import Flask, jsonify, request
from airfoil_finder import AirfoilFinder
import sys

app = Flask(__name__)


def _error(name, reason):
    url = request.url.replace(request.url_root[:-1], '')
    return jsonify({'error': 404, 'url': url, 'name': name, 'reason': reason})


@app.route('/')
def get_airfoils():
    airfoils = []
    for af in finder.airfoils.values():
        airfoils.append({'name': af.name, 'ip': af.ip})
    return jsonify({'airfoils': airfoils})


def _run_in_airfoil(name, fn):
    airfoil = finder.airfoils.get(name, None)
    if airfoil:
        return fn(airfoil)
    else:
        return _error(name, f'No airfoil instance found with name \'{name}\'')


@app.route('/<name>/')
@app.route('/<name>')
def get_airfoil(name):
    return jsonify(_run_in_airfoil(name, lambda airfoil: {'airfoil': {'name': airfoil.name, 'ip': airfoil.ip}}))


@app.route('/<name>/pause/')
@app.route('/<name>/pause')
@app.route('/<name>/play/')
@app.route('/<name>/play')
@app.route('/<name>/play_pause/')
@app.route('/<name>/play_pause')
def play_pause(name):
    return jsonify(_run_in_airfoil(name, lambda airfoil: airfoil.play_pause()))


@app.route('/<name>/skip/')
@app.route('/<name>/skip')
@app.route('/<name>/next/')
@app.route('/<name>/next')
@app.route('/<name>/next_track/')
@app.route('/<name>/next_track')
def next_track(name):
    return jsonify(_run_in_airfoil(name, lambda airfoil: airfoil.next_track()))


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
    return jsonify(_run_in_airfoil(name, lambda airfoil: airfoil.last_track()))


@app.route('/<name>/sources/')
@app.route('/<name>/sources')
def get_sources(name):
    source_icon = True if request.args.get('source_icon', '').lower() == 'true' else False
    sources = _run_in_airfoil(name, lambda airfoil: airfoil.get_sources(source_icon))
    source_list = []
    for s in sources:
        source_list.append(s._asdict())
    return jsonify(source_list)


@app.route('/<name>/current_source/')
@app.route('/<name>/current_source')
@app.route('/<name>/source/')
@app.route('/<name>/source')
def get_current_source(name):
    # machine_icon = False, album_art = False, source_icon = False, track_meta = False
    machine_icon = True if request.args.get('machine_icon', '').lower() == 'true' else False
    album_art = True if request.args.get('album_art', '').lower() == 'true' else False
    source_icon = True if request.args.get('source_icon', '').lower() == 'true' else False
    track_meta = True if request.args.get('track_meta', '').lower() == 'true' else False

    source = _run_in_airfoil(name, lambda airfoil: airfoil.get_current_source(
        machine_icon=machine_icon, album_art=album_art, source_icon=source_icon, track_meta=track_meta))

    return jsonify(source._asdict())


@app.route('/<name>/speakers/')
@app.route('/<name>/speakers')
def get_speakers(name):
    speakers = _run_in_airfoil(name, lambda airfoil: airfoil.get_speakers())
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
    if speaker.lower() == 'speakers':
        ids = request.args.get('ids', '').split(',')
        names = request.args.get('names', '').split(',')
        if names and names != ['']:
            return jsonify(_run_in_airfoil(name, lambda airfoil: airfoil.mute_some(names=names)))
        elif ids and ids != ['']:
            return jsonify(_run_in_airfoil(name, lambda airfoil: airfoil.mute_some(ids=ids)))
        else:
            return jsonify(_run_in_airfoil(name, lambda airfoil: airfoil.mute_all()))
    else:
        return jsonify(_speaker_cmd(name, speaker, lambda airfoil, match: airfoil.mute(id=match.id)))


@app.route('/<name>/<speaker>/unmute/')
@app.route('/<name>/<speaker>/unmute')
@app.route('/<name>/<speaker>/unmute/<default_volume>/')
@app.route('/<name>/<speaker>/unmute/<default_volume>')
def unmute(name, speaker, default_volume=None):
    default_volume = float(request.args.get('default_volume', 1.0) if not default_volume else default_volume)

    if speaker.lower() == 'speakers':
        ids = request.args.get('ids', '').split(',')
        names = request.args.get('names', '').split(',')
        if names and names != ['']:
            return jsonify(_run_in_airfoil(name, lambda airfoil: airfoil.unmute_some(
                names=names, default_volume=default_volume)))
        elif ids and ids != ['']:
            return jsonify(_run_in_airfoil(
                name, lambda airfoil: airfoil.unmute_some(ids=ids, default_volume=default_volume)))
        else:
            return jsonify(_run_in_airfoil(name, lambda airfoil: airfoil.unmute_all(default_volume=default_volume)))
    else:
        return jsonify(_speaker_cmd(
            name, speaker, lambda airfoil, match: airfoil.unmute(id=match.id, default_volume=default_volume)))


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
    if end_volume < 0 or end_volume > 1:
        return _error(name, 'fade requires an end volume between 0 and 1 with up to 6 digits after the decimal point. '
                            f'for example:  /{name}/{speaker}/fade/0.7  -or-  /{name}/{speaker}/fade/0.35/10/100  -or- '
                            f' /{name}/{speaker}/fade?end_volume=0.654444&seconds=15&ticks=500')
    if ticks and not ticks.isdigit():
        return _error(name, 'the number given for ticks must be an integer greater than 0.')

    ticks = int(request.args.get('ticks', 10) if not ticks else ticks)

    ids = request.args.get('ids', '').split(',')
    names = request.args.get('names', '').split(',')
    if speaker == 'speakers':
        if names and names != ['']:
            return jsonify(_run_in_airfoil(name, lambda airfoil: airfoil.fade_some(
                names=names, end_volume=end_volume, seconds=seconds, ticks=ticks)))
        elif ids and ids != ['']:
            return jsonify(_run_in_airfoil(
                name, lambda airfoil: airfoil.fade_some(ids=ids, end_volume=end_volume, seconds=seconds, ticks=ticks)))
        else:
            return jsonify(_run_in_airfoil(
                name, lambda airfoil: airfoil.fade_all(end_volume=end_volume, seconds=seconds, ticks=ticks)))
    else:
        return jsonify(_speaker_cmd(name, speaker, lambda airfoil, match: airfoil.fade_volume(
            id=match.id, end_volume=end_volume, seconds=seconds, ticks=ticks)))


@app.route('/<name>/<speaker>/volume/')
@app.route('/<name>/<speaker>/volume')
@app.route('/<name>/<speaker>/volume/<level>/')
@app.route('/<name>/<speaker>/volume/<level>')
def volume(name, speaker, level=None):
    level = float(request.args.get('level', -1) if level is None else level)
    if level < 0 or level > 1:
        return _error(name, 'volume requires a level value between 0 and 1 with up to 6 digits after the decimal point.'
                            f' for example:  /{name}/{speaker}/volume/0.7  -or  /{name}/{speaker}/volume?level=0.354242')
    return jsonify(_speaker_cmd(name, speaker, lambda airfoil, match: airfoil.set_volume(level, id=match.id)))


def _speaker_cmd(name, speaker, cmd):
    airfoil = finder.airfoils.get(name, None)
    match = None
    if airfoil:
        try:
            match = airfoil.find_speaker(name=speaker.replace('_', ' '))
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


if __name__=='__main__':
    cli = sys.modules['flask.cli']
    cli.show_server_banner = lambda *x: None
    finder = AirfoilFinder()
    app.run(host='0.0.0.0', port='80', threaded=True)

