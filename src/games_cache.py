from cache_proto import ProtoCache
from version import __version__
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import List, Dict
from protocol.protobuf_client import SteamLicense
import logging
import json
import copy

logger = logging.getLogger(__name__)


@dataclass_json
@dataclass
class App:
    appid: str
    title: str
    type: str


@dataclass_json
@dataclass
class License:
    package_id: str
    shared: bool
    app_ids: List[str] = field(default_factory=list)


@dataclass_json
@dataclass
class LicensesCache:
    licenses: List[License] = field(default_factory=list)
    apps: Dict[str, App] = field(default_factory=dict)


@dataclass
class ParsingStatus:
    packages_to_parse: int = None
    apps_to_parse: int = None

class GamesCache(ProtoCache):
    def __init__(self):
        super(GamesCache, self).__init__()
        self._storing_map: LicensesCache = LicensesCache()

        self._sent_apps = []

        self._apps_added: List[App] = []
        self.add_game_lever: bool = False

        self._parsing_status = ParsingStatus()


    def reset_storing_map(self):
        self._storing_map: LicensesCache = LicensesCache()

    def start_packages_import(self, steam_licenses: List[SteamLicense]):
        package_ids = self.get_package_ids()
        for steam_license in steam_licenses:
            if steam_license.license.package_id in package_ids:
                continue
            self._storing_map.licenses.append(License(package_id=str(steam_license.license.package_id),
                                             shared=steam_license.shared))
        self._parsing_status.packages_to_parse = len(steam_licenses)
        self._parsing_status.apps_to_parse = 0
        self._update_ready_state()

    def get_added_games(self):
        apps = self._apps_added
        self._apps_added = []
        games = []
        for app in apps:
            self._sent_apps.append(app)
            if app.type == "game":
                games.append(app)
        return games

    def get_package_ids(self):
        if not self._storing_map:
            return []
        return [license.package_id for license in copy.copy(self._storing_map).licenses]

    def get_resolved_packages(self):
        if not self._storing_map:
            return []
        packages = []
        storing_map = copy.copy(self._storing_map)
        for license in storing_map.licenses:
            if license.app_ids:
                resolved = True
                for app in license.app_ids:
                    if app not in storing_map.apps:
                        resolved = False
                if resolved:
                    packages.append(license.package_id)

        return packages

    def update_packages(self):
        self._parsing_status.packages_to_parse -= 1
        self._update_ready_state()

    def get_owned_games(self):
        storing_map = copy.copy(self._storing_map)
        for license in storing_map.licenses:
            if license.shared:
                continue
            for appid in license.app_ids:
                if appid not in self._storing_map.apps:
                    logger.warning(f"Tried to retrieve unresolved app: {appid} for license: {license.package_id}!")
                    continue
                app = self._storing_map.apps[appid]
                if app.type == "game":
                    self._sent_apps.append(app)
                    yield app

    def get_shared_games(self):
        storing_map = copy.copy(self._storing_map)
        for license in storing_map.licenses:
            if not license.shared:
                continue
            for appid in license.app_ids:
                if appid not in self._storing_map.apps:
                    logger.warning(f"Tried to retrieve unresolved app: {appid} for shared license: {license.package_id}!")
                    continue
                app = self._storing_map.apps[appid]
                if app.type == "game":
                    self._sent_apps.append(app)
                    yield app

    def update_license_apps(self, package_id, appid):
        self._parsing_status.apps_to_parse += 1
        for license in self._storing_map.licenses:
            if license.package_id == package_id:
                license.app_ids.append(appid)

    def update_app_title(self, appid, title, type):
        for license in self._storing_map.licenses:
            if appid in license.app_ids:
                self._parsing_status.apps_to_parse -= 1
        new_app = App(appid=appid, title=title, type=type)
        self._storing_map.apps[appid] = new_app
        if self.add_game_lever and new_app not in self._sent_apps:
            self._apps_added.append(new_app)

        self._update_ready_state()

    def _update_ready_state(self):
        if self._parsing_status.packages_to_parse == 0 and self._parsing_status.apps_to_parse == 0:
            if self._ready_event.is_set():
                return
            logger.info("Setting state to ready")
            self._ready_event.set()
        else:
            self._ready_event.clear()

    def dump(self):
        cache_json = {}
        cache_json['licenses'] = self._storing_map.to_json()
        cache_json['version'] = __version__
        return json.dumps(cache_json)

    def loads(self, persistent_cache):
        cache = json.loads(persistent_cache)

        if 'version' not in cache or cache['version'] != __version__:
            logging.error("New plugin version, refreshing cache")
            return

        self._storing_map = LicensesCache.from_json(cache['licenses'])
        logging.info(f"Loaded games from cache {self._storing_map}")
