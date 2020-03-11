
from cache_proto import ProtoCache
import logging

logger = logging.getLogger(__name__)


class GamesCache(ProtoCache):
    def __init__(self):
        super(GamesCache, self).__init__()
        self._packages_to_parse = None
        self._apps_to_parse = {}
        self._games_added = {}
        self.add_game_lever: bool = False

    def start_packages_import(self, licenses):
        self._packages_to_parse = dict.fromkeys(licenses, None)

    def _reset(self, game_ids):
        pass

    def _add(self, game_id):
        pass

    def _remove(self, game_id):
        pass

    def get_added_games(self):
        games = self._games_added
        self._games_added = {}
        return games

    def update_packages(self, package_id):
        try:
            self._packages_to_parse.pop(package_id)
        except KeyError:
            logger.error(f"Unexpected package_id {package_id}")
        self._update_ready_state()

    def __iter__(self):
        yield from self._info_map.items()

    def update(self, appid, title, game):
        if not title and game is None and appid not in self._apps_to_parse:
            self._apps_to_parse[appid] = None

        if (game is False or (title and game)) and appid in self._apps_to_parse:
            self._apps_to_parse.pop(appid)

        if title and game:
            if self.add_game_lever:
                self._info_map[appid] = title
                self._games_added[appid] = title
            else:
                self._info_map[appid] = title

        self._update_ready_state()

    def _update_ready_state(self):
        if self._packages_to_parse is not None and len(self._packages_to_parse) == 0 and len(self._apps_to_parse) == 0:
            if self._ready_event.is_set():
                return
            logger.info("Setting state to ready")
            self._ready_event.set()
        else:
            self._ready_event.clear()
