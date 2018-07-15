from flask import Flask, jsonify, request, g
from remoteFoil.airfoil_finder import AirfoilFinder
import sys
finder = None
app = Flask(__name__)
TRUTHIES = ['true', 'yes', 'y', 't', '1', 'on', 'enabled']


def _error(name, caller, reason):
    url = request.url.replace(request.url_root[:-1], '')
    return {'status': 'fail', 'action': caller, 'url': url, 'name': name, 'reason': reason}

def _success(name, caller):
    url = request.url.replace(request.url_root[:-1], '')
    return {'status': 'success', 'action': caller, 'url': url, 'name': name}


@app.route('/')
def get_airfoils():
    airfoils = []
    for af in finder.airfoils.values():
        airfoils.append({'name': af.name, 'ip': af.ip})
    return jsonify({'airfoils': airfoils})

@app.before_request
def _get_args():
    g.disconnected = False
    g.names = []
    g.ids = []
    g.volume = None
    g.seconds = 3
    g.ticks = 10
    g.action = None
    for k, v in request.args.items():
        newk = k.lower()
        newv = v.lower()
        if newk == 'ids':
            g.ids = [i for i in newv.split(',') if i]
        if newk == 'names':
            g.names = [n for n in newv.split(',') if n]
        if newk in ['disconnected', 'all']:
            g.disconnected = newv in TRUTHIES
        if newk in ['end_volume', 'level', 'volume']:
            g.volume = newv
        if newk == 'seconds':
            g.seconds = newv
        if newk == 'ticks':
            g.ticks = newv
        if newk == 'action':
            g.action = newv


def _parse_speaker_cmd(name, speaker, functions):
    if speaker == 'speakers':
        speakers = [c._asdict() for c in _airfoil_cmd(name, functions['multi'])]
    else:
        speakers = [c._asdict() for c in _airfoil_cmd(name, functions['specific'], speaker=speaker)]
    caller = sys._getframe(1).f_code.co_name
    result = _success(name, caller)
    result['speakers'] = speakers
    return jsonify(result)


def _airfoil_cmd(name, cmd, speaker=None):
    caller = sys._getframe(1).f_code.co_name
    name = name.lower()
    airfoil = finder.airfoils.get(name, None)
    if airfoil:
        if not speaker:
            return cmd(airfoil)
        else:
            match = airfoil.find_speaker(unknown=speaker)
            if match:
                return cmd(airfoil, match)
            else:
                return _error(name, caller, f'No speaker found with name, id, or keywords: \'{speaker}\'')
    else:
        return _error(name, caller, f'No remoteFoil instance found with name \'{name}\'')


def _media_button(name, cmd):
    caller = sys._getframe(1).f_code.co_name
    cmds = {
        'play': lambda airfoil: airfoil.play_pause(),
        'next': lambda airfoil: airfoil.next_track(),
        'back': lambda airfoil: airfoil.last_track()
    }
    source = _airfoil_cmd(name, lambda airfoil: airfoil.get_current_source())
    if not source.source_controllable:
        response = _error(name, caller, 'current source does not support remote control by Airfoil')
    else:
        result = _airfoil_cmd(name, cmds[cmd])
        if result:
            response = _success(name, caller)
            source = _airfoil_cmd(name, lambda airfoil: airfoil.get_current_source())
        else:
            response = _error(name, caller, 'unknown')
    response['current_source'] = source._asdict()
    return jsonify(response)


@app.route('/<name>/')
@app.route('/<name>')
def get_airfoil(name):
    return jsonify(_airfoil_cmd(name, lambda airfoil: {'remoteFoil': {'name': airfoil.name, 'ip': airfoil.ip}}))


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
    source_name = request.args.get('name', '')
    source_id = request.args.get('id', '')
    keywords = [kw for kw in request.args.get('keywords', '').split(',') if kw]
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
        try:
            if source_name or source_id or keywords:
                match = airfoil.find_source(name=source_name, id=source_id, keywords=keywords)
        except ValueError:
            return jsonify(_error(name, 'no source was found with the specified url keyword parameter'))
        if source:
            try:
                match = airfoil.find_source(name=source)
            except ValueError:
                try:
                    match = airfoil.find_source(id=source)
                except ValueError:
                    keywords = airfoil.get_keywords(source)
                    try:
                        match = airfoil.find_source(keywords=keywords)
                    except ValueError:
                        pass
        response = {'action': 'set_source', 'status': 'success', 'current_source': None}
        if match:
            source = airfoil.set_source(id=match.id)._asdict()
            if source['source_name'] != match.name:
                response['status'] = 'fail'
                response['reason'] = 'source was not successfully changed. check Airfoil.'
        else:
            source = airfoil.get_current_source()._asdict()
            response['status'] = 'fail'
            response['reason'] = 'no source was found with the given name.'
        response['current_source'] = source
        return jsonify(response)



    else:
        return _error(name, f'No remoteFoil instance found with name \'{name}\'')


@app.route('/<name>/<speaker>/')
@app.route('/<name>/<speaker>')
@app.route('/<name>/<speaker>/<action>/')
@app.route('/<name>/<speaker>/<action>')
@app.route('/<name>/<speaker>/<action>/<arg1>/')
@app.route('/<name>/<speaker>/<action>/<arg1>')
@app.route('/<name>/<speaker>/<action>/<arg1>/<arg2>/')
@app.route('/<name>/<speaker>/<action>/<arg1>/<arg2>')
@app.route('/<name>/<speaker>/<action>/<arg1>/<arg2>/<arg3>/')
@app.route('/<name>/<speaker>/<action>/<arg1>/<arg2>/<arg3>')
def speaker_uri(name, speaker, action=None, arg1=None, arg2=None, arg3=None):
    g.action = action = action.lower() if action else g.action
    g.volume = arg1 if arg1 else g.volume
    level_error = f'{g.action} requires an end volume in the following formats: A number between 0 and 1 inclusive ' \
                  f'with up to 8 digits after the decimal point, or a percentage. values greater than 1 or less than ' \
                  f'0 will be constrained to valid values. valid values for volume include 0, 1, 0.75432111, 35%, 100%'
    try:  # make sure given volume is a valid value
        if g.volume is not None:
            g.volume = _airfoil_cmd(name, lambda airfoil: airfoil._parse_volume(g.volume))
    except ValueError:
        return jsonify(_error(name, action, level_error))

    if not any([action, arg1, arg2, arg3]):
        if speaker == 'speakers':               # get list of all speakers /remoteFoil/speakers
            return get_speakers(name)
        else:
            return get_speaker(name, speaker)   # get specific speaker info /remoteFoil/my_speaker

    if action in ['on', 'yes', 'true', 'connect', 'enable', 'enabled']:
        return connect(name, speaker)
    if action in ['off', 'no', 'false', 'disconnect', 'disable', 'disabled']:
        return disconnect(name, speaker)
    if action in ['toggle', 'reset', 'cycle']:
        return toggle(name, speaker)
    if action in ['mute', 'silence', 'silent', 'quiet']:
        return mute(name, speaker)
    if action == 'unmute':
        return unmute(name, speaker)
    if action in ['volume', 'level']:
        return volume(name, speaker)
    if action in ['source', 'current_source']:
        return get_current_source(name)
    if action in ['play', 'pause', 'play_pause']:
        return play_pause(name)
    if action in ['skip', 'next', 'next_track']:
        return next_track(name)
    if action in ['prev', 'last', 'back', 'prev_track', 'last_track']:
        return last_track(name)

    if action in ['fade', 'ramp', 'transition']:
        g.seconds = arg2 if arg2 else g.seconds
        try:
            g.seconds = abs(float(g.seconds))
        except ValueError:
            return jsonify(_error(name, g.action, f'seconds must be a positive numeric value like 5, 3.25, 15.021, not '
                                                  f'\'{g.seconds}\''))
        g.ticks = arg3 if arg3 else g.ticks
        try:
            g.ticks = int(g.ticks)
        except ValueError:
            return jsonify(_error(name, g.action, f'ticks must be a positive numeric value like 4 or 20, not '
                                                  f'\'{g.ticks}\''))
        return fade(name, speaker)

    try:
        g.volume = _airfoil_cmd(name, lambda airfoil: airfoil._parse_volume(action))
        return volume(name, speaker)
    except ValueError:
        pass
    return jsonify(_error(name, action, f'action for speaker is not recognized: \'{action}\''))


def get_speakers(name):
    speakers = _airfoil_cmd(name, lambda airfoil: airfoil.get_speakers())
    return jsonify([s._asdict() for s in speakers])


def get_speaker(name, speaker):
    return jsonify(_airfoil_cmd(name, lambda _, match: match._asdict(), speaker=speaker))


def connect(name, speaker):
    functions = {'multi':
         lambda airfoil: airfoil.connect_some(names=g.names, ids=g.ids),
                 'specific':
         lambda airfoil, match: airfoil.disconnect_speaker(id=match.id)
                 }
    return _parse_speaker_cmd(name, speaker, functions)


def disconnect(name, speaker):
    functions = {'multi':
         lambda airfoil: airfoil.disconnect_some(names=g.names, ids=g.ids),
                 'specific':
         lambda airfoil, match: airfoil.disconnect_speaker(id=match.id)
                 }
    return _parse_speaker_cmd(name, speaker, functions)


def toggle(name, speaker):
    functions = {'multi':
         lambda airfoil: airfoil.toggle_some(names=g.names, ids=g.ids, include_disconnected=g.disconnected),
                 'specific':
         lambda airfoil, match: airfoil.toggle_speaker(id=match.id)
                 }
    return _parse_speaker_cmd(name, speaker, functions)


def mute(name, speaker):
    functions = {'multi':
         lambda airfoil: airfoil.mute_some(names=g.names, ids=g.ids, include_disconnected=g.disconnected),
                 'specific':
         lambda airfoil, match: airfoil.mute(id=match.id)
                 }
    return _parse_speaker_cmd(name, speaker, functions)


def unmute(name, speaker):
    functions = {'multi':
         lambda airfoil: airfoil.unmute_some(names=g.names, ids=g.ids, default_volume=g.volume,
                                             include_disconnected=g.disconnected),
                 'specific':
         lambda airfoil, match: airfoil.unmute(id=match.id, default_volume=g.volume)
                 }
    return _parse_speaker_cmd(name, speaker, functions)


def fade(name, speaker):
    functions = {'multi':
        lambda airfoil: airfoil.fade_some(names=g.names, ids=g.ids, end_volume=g.volume, seconds=g.seconds,
                                          ticks=g.ticks, include_disconnected=g.disconnected),
                 'specific':
        lambda airfoil, match: airfoil.fade_volume(id=match.id, end_volume=g.volume, seconds=g.seconds, ticks=g.ticks)}
    return _parse_speaker_cmd(name, speaker, functions)


def volume(name, speaker):
    functions = {'multi':
         lambda airfoil: airfoil.set_volumes(g.volume, names=g.names, ids=g.ids, include_disconnected=g.disconnected),
                 'specific':
         lambda airfoil, match: airfoil.set_volume(g.volume, id=match.id)
                 }
    return _parse_speaker_cmd(name, speaker, functions)

def start():
    cli = sys.modules['flask.cli']
    cli.show_server_banner = lambda *x: None
    finder = AirfoilFinder()
    app.run(host='0.0.0.0', port='80', threaded=True)

if __name__=='__main__':
    start()


