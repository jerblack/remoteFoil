from aiohttp import web
import asyncio
from airfoil_async import AirfoilAsync
from airfoil_finder import AirfoilFinder


class AirfoilHttp(object):
    def __init__(self):
        self.app = web.Application()
        self.app.add_routes(self.get_routes())
        self.finder = AirfoilFinder()
        # self.app.loop.run_until_complete(asyncio.ensure_future(self.watch))
        web.run_app(self.app, port=80, host='0.0.0.0')

    def get_routes(self):
        routes = []
        route_tuples = [
            ('/', self.get_airfoil),
            ('/{name}', self.get_airfoil),
            ('/{name}/{speaker}', self.get_speaker),
            # ('/{name}/play_pause', self.play_pause),
            # ('/{name}/next_track', self.next_track),
            # ('/{name}/last_track', self.last_track),
            # ('/{name}/source', self.get_sources),
            # ('/{name}/source/{source}', self.set_source),
            # ('/{name}/{speaker}/connect', self.connect),
            # ('/{name}/{speaker}/disconnect', self.disconnect),
            # ('/{name}/{speaker}/toggle', self.toggle),
            # ('/{name}/{speaker}/mute', self.mute),
            # ('/{name}/{speaker}/unmute', self.unmute),
            # ('/{name}/{speaker}/unmute/{default_volume}', self.unmute),
            # ('/{name}/{speaker}/fade', self.fade),
            # ('/{name}/{speaker}/fade/{end_volume}', self.fade),
            # ('/{name}/{speaker}/fade/{end_volume}/{seconds}', self.fade),
            # ('/{name}/{speaker}/fade/{end_volume}/{seconds}/{ticks}', self.fade),
            ('/{name}/{speaker}/volume/{level}', self.set_volume),

        ]
        for r in route_tuples:
            path, fn = r
            routes.append(web.get(path, fn))
            if len(path) > 1:
                routes.append(web.get(f'{path}/', fn))
        return routes

    def _error(self, request, reason):
        name = request.match_info['name']
        uri = str(request.url.relative())
        return {'error': 404, 'name': name, 'uri': uri, 'reason': reason}

    async def get_speaker(self, request):
        print(request)
        name = request.match_info.get('name')
        speaker = request.match_info.get('speaker')
        airfoil = self.finder.airfoils.get(name, None)
        if airfoil:
            if speaker == 'speakers':
                speakers = airfoil.get_speakers()
                speaker_list = []
                for s in speakers:
                    speaker_list.append(s._asdict())
                return web.json_response(speaker_list)
            else:
                speaker_match = await self.match_speaker(airfoil, speaker)
                if speaker_match:
                    return web.json_response(speaker_match._asdict())
                else:
                    return web.json_response(
                        self._error(request, f'No speaker found with name, id, or keywords: \'{speaker}\''))
        else:
            fail = self._error(request, f'No airfoil instance found with name \'{name}\'')
            return web.json_response(fail)

    async def match_speaker(self, airfoil, speaker):
        try:
            return airfoil.find_speaker(name=speaker.replace('_', ' '))
        except ValueError:
            keywords = airfoil.get_keywords(speaker)
            try:
                return airfoil.find_speaker(keywords=keywords)
            except ValueError:
                try:
                    return airfoil.find_speaker(id=speaker)
                except ValueError:
                    return None

    # async def set_volume(self, request):
    #     name = request.match_info.get('name')
    #     airfoil = self.finder.airfoils.get(name, None)
    #     speaker = request.match_info.get('speaker')
    #     speaker = await self.match_speaker(airfoil, speaker)
    #     if airfoil:
    #         if speaker == 'speakers':
    #             airfoil.

    async def get_airfoil(self, request):
        name = request.match_info.get('name', None)
        if name:
            airfoil = self.finder.airfoils.get(name, None)
            success = {'airfoil': {'name': airfoil.name, 'ip': airfoil.ip}} if airfoil else None
            fail = self._error(request, f'No airfoil instance found with name \'{name}\'')
            return web.json_response(success if airfoil else fail)
        else:
            airfoils = []
            for af in self.finder.airfoils.values():
                airfoils.append({'name': af.name, 'ip': af.ip})
            return web.json_response({'airfoils': airfoils})





















        # return web.Response(text=uri+'\n')
























AirfoilHttp()