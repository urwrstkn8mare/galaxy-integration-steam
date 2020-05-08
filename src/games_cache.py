from cache_proto import ProtoCache
from version import __version__
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

    def reset_storing_map(self):
        self._storing_map = {'licenses':{}}

    def start_packages_import(self, licenses):
        for license in licenses:
            self._storing_map['licenses'][license['package_id']] = {'shared':license['shared'], 'apps':{}}
        self._parsing_status['packages'] = len(licenses)
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
        return [package_id for package_id in self._storing_map['licenses']]

    def get_resolved_packages(self):
        if not self._storing_map:
            return []
        return [package_id for package_id in self._storing_map['licenses'] if self._storing_map['licenses'][package_id]['apps']]

    def update_packages(self, package_id):
        self._parsing_status['packages'] -= 1
        self._update_ready_state()

    def __iter__(self):
        licenses_map = self._storing_map['licenses']
        for package in licenses_map:
            for app in licenses_map[package]['apps']:
                if licenses_map[package]['apps'][app]:
                    self._sent_games.append(app)
                    if not licenses_map[package]['shared']:
                        yield app, licenses_map[package]['apps'][app]

    def get_shared_games(self):
        shared_games = []
        licenses_map = self._storing_map['licenses']
        for package in licenses_map:
            for app in licenses_map[package]['apps']:
                if licenses_map[package]['apps'][app]:
                    if licenses_map[package]['shared']:
                        shared_games.append({'id': app, 'title': licenses_map[package]['apps'][app]})
        return shared_games

    def update(self, package_id, appid, title, game):


        if package_id:
            self._parsing_status['apps'] += 1
            if appid not in self._appid_package_map:
                self._appid_package_map[appid] = [package_id]
            else:
                self._appid_package_map[appid].append(package_id)
            self._storing_map['licenses'][package_id]['apps'][appid] = None
        else:
            self._parsing_status['apps'] -= 1

        if title and game:
            for package_id in self._appid_package_map[appid]:
                self._storing_map['licenses'][package_id]['apps'][appid] = title

            if self.add_game_lever and appid not in self._sent_games:
                for package_id in self._appid_package_map[appid]:
                    if not self._storing_map['licenses'][package_id]['shared']:
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
        self._storing_map['version'] = __version__
        cache_json = json.dumps(self._storing_map)
        return cache_json

    def loads(self, persistent_cache):
        cache = json.loads(persistent_cache)
        try:
            for license in cache['licenses']:
                cache['licenses'][license]['apps']
                cache['licenses'][license]['shared']
        except KeyError:
            logging.error("Incompatible cache")
            return
        if 'version' not in cache or cache['version'] != __version__:
            logging.error("New plugin version, refreshing cache")
            return

        self._storing_map = cache
        logging.info(f"Loaded games from cache {self._storing_map}")
