from cache_proto import ProtoCache
import logging
import json

logger = logging.getLogger(__name__)


class GamesCache(ProtoCache):
    def __init__(self):
        super(GamesCache, self).__init__()
        self._storing_map = None
        self._sent_games = []
        self._appid_package_map = {}

        self._games_added = {}
        self.add_game_lever: bool = False

        self._parsing_status = {'packages': 0, 'apps': 0}

    def start_packages_import(self, licenses):
        self._storing_map = {}
        for license in licenses:
            self._storing_map[license['package_id']] = {'shared':license['shared'], 'apps':{}}
        self._parsing_status['packages'] = len(self._storing_map)
        self._parsing_status['apps'] = 0
        self._update_ready_state()

    def _reset(self, game_ids):
        pass

    def _add(self, game_id):
        pass

    def _remove(self, game_id):
        pass

    def get_added_games(self):
        games = self._games_added
        self._games_added = {}
        for game in games:
            self._sent_games.append(game)
        return games

    def get_package_ids(self):
        if not self._storing_map:
            return []
        return [package_id for package_id in self._storing_map]

    def update_packages(self, package_id):
        self._parsing_status['packages'] -= 1
        self._update_ready_state()

    def __iter__(self):
        for package in self._storing_map:
            for app in self._storing_map[package]['apps']:
                if self._storing_map[package]['apps'][app]:
                    self._sent_games.append(app)
                    if not self._storing_map[package]['shared']:
                        yield app, self._storing_map[package]['apps'][app]

    def get_shared_games(self):
        shared_games = []
        for package in self._storing_map:
            for app in self._storing_map[package]['apps']:
                if self._storing_map[package]['apps'][app]:
                    if self._storing_map[package]['shared']:
                        shared_games.append({'id': app, 'title': self._storing_map[package]['apps'][app]})
        return shared_games

    def update(self, mother_appid, appid, title, game):

        if mother_appid:
            self._parsing_status['apps'] += 1
            self._appid_package_map[appid] = mother_appid
            self._storing_map[mother_appid]['apps'][appid] = None
        else:
            self._parsing_status['apps'] -= 1

        if title and game:
            self._storing_map[self._appid_package_map[appid]]['apps'][appid] = title

            if self.add_game_lever and appid not in self._sent_games:
                if not self._storing_map[self._appid_package_map[appid]]['shared']:
                    self._games_added[appid] = title

            self._update_ready_state()

    def _update_ready_state(self):
        if self._parsing_status['packages'] == 0 and self._parsing_status['apps'] == 0:
            if self._ready_event.is_set():
                return
            logger.info("Setting state to ready")
            self._ready_event.set()
        else:
            self._ready_event.clear()

    def dump(self):
        return json.dumps(self._storing_map)

    def loads(self, persistent_cache):
        cache = json.loads(persistent_cache)
        try:
            for license in cache:
                cache[license]['apps']
                cache[license]['shared']
        except KeyError:
            logging.error("Incompatible cache")
            return

        self._storing_map = cache
        logging.info(f"Loaded games from cache {self._storing_map}")
