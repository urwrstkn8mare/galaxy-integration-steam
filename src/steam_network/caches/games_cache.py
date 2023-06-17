from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import Any, List, Dict, Optional, Set, AsyncGenerator
import logging
import json
import copy
import asyncio

from .cache_proto import ProtoCache
from ..protocol.protobuf_client import SteamLicense
from ..w3_hack import WITCHER_3_DLCS_APP_IDS


logger = logging.getLogger(__name__)


@dataclass_json
@dataclass
class App:
    appid: str
    title: str
    type_: str
    parent: Optional[str]


@dataclass_json
@dataclass
class GameLicense:
    package_id: str
    shared: bool
    app_ids: Set[int] = field(default_factory=set)

@dataclass_json
@dataclass
class LicensesCache:
    #licenses: List[GameLicense] = field(default_factory=list)
    license_lookup: Dict[int, GameLicense] = field(default_factory=dict)
    apps: Dict[str, App] = field(default_factory=dict)

    @classmethod
    def migrateV1(cls, data: str) -> LicensesCache:
        obj = json.loads(data)

        for appid in obj.get("apps", {}):
            app = obj["apps"][appid]

            if "type" in app:
                app["type_"] = app["type"]
                del app["type"]

            #CHECK ME!
            if ("licenses" in obj):
                obj["license_lookup"] = { int(item.package_id): item for item in obj["licenses"]}

        return LicensesCache.from_dict(obj)


@dataclass
class ParsingStatus:
    packages_to_parse: Optional[int] = None
    apps_to_parse: Optional[int] = None


class GamesCache(ProtoCache):

    _VERSION = "1.0.0"

    def __init__(self):
        super(GamesCache, self).__init__()
        self._storing_map: LicensesCache = LicensesCache()

        self._sent_apps = []

        self._apps_added: List[App] = []
        self.add_game_lever: bool = False

        self._parsing_status = ParsingStatus()

    @property
    def version(self):
        return self._VERSION

    def reset_storing_map(self):
        self._storing_map: LicensesCache = LicensesCache()

    def start_packages_import(self, steam_licenses: List[SteamLicense]):
        package_ids = self.get_package_ids()
        self._parsing_status.packages_to_parse = 0
        logger.debug('Licenses to parse: %d, cached package_ids: %d', len(steam_licenses), len(package_ids))
        for steam_license in steam_licenses:
            if steam_license.license_data.package_id in package_ids:
                continue
            pid = steam_license.license_data.package_id
            self._storing_map.license_lookup[pid] = (GameLicense(package_id=str(pid), shared=steam_license.shared))
            self._parsing_status.packages_to_parse += 1
        self._parsing_status.apps_to_parse = 0
        self._update_ready_state()

    def consume_added_games(self) -> List[App]:
        apps = self._apps_added
        self._apps_added = []
        games = []
        for app in apps:
            self._sent_apps.append(app)
            if app.type_ == "game":
                games.append(app)
        return games

    def get_package_ids(self) -> Set[int]:
        if not self._storing_map:
            return set()
        return set(self._storing_map.license_lookup.keys())

    def get_resolved_packages(self) -> Set[str]:
        if not self._storing_map:
            return set()
        packages = set()
        storing_map = copy.copy(self._storing_map)
        for game_license in storing_map.license_lookup.values():
            if game_license.app_ids:
                resolved = True
                for app in game_license.app_ids:
                    if app not in storing_map.apps:
                        resolved = False
                if resolved:
                    packages.add(game_license.package_id)
        return packages

    def update_packages(self):
        self._parsing_status.packages_to_parse -= 1
        self._update_ready_state()

    async def __consume_resolved_apps(self, shared_licenses: bool, apptype: str) -> AsyncGenerator[App, None]:
        storing_map = copy.copy(self._storing_map)
        for game_license in storing_map.license_lookup.values():
            await asyncio.sleep(0.0001)  # do not block event loop; waiting one frame (0) was not enough 78#issuecomment-687140437
            if game_license.shared != shared_licenses:
                continue
            for appid in game_license.app_ids:
                if appid not in self._storing_map.apps:
                    logger.warning("Tried to retrieve unresolved app: %s for license: %s!", appid, game_license.package_id)
                    continue
                app = self._storing_map.apps[appid]
                if app.type_ == apptype:
                    self._sent_apps.append(app)
                    yield app
                # Necessary for the Witcher 3 => Witcher 3 GOTY import hack
                elif apptype == 'game' and app.type_ == 'dlc' and appid in WITCHER_3_DLCS_APP_IDS:
                    yield app

    async def get_owned_games(self) -> AsyncGenerator[App, None]:
        async for app in self.__consume_resolved_apps(False, 'game'):
            yield app

    async def get_dlcs(self) -> AsyncGenerator[App, None]:
        async for app in self.__consume_resolved_apps(False, 'dlc'):
            yield app

    async def get_shared_games(self) -> AsyncGenerator[App, None]:
        async for app in self.__consume_resolved_apps(True, 'game'):
            yield app

    def update_license_apps(self, total_packages_processed: int, packages_with_apps: Dict[int, List[int]]):
        self._parsing_status.packages_to_parse -= total_packages_processed
        self._update_ready_state()

        for package_id, apps in packages_with_apps.items():
            self._parsing_status.apps_to_parse += 1
            if package_id in self._storing_map.license_lookup:
                self._storing_map.license_lookup[package_id].app_ids.update(apps)
            else:
                self._storing_map.license_lookup[package_id] = set(apps)

    def update_app_titles(self, new_apps : List[App]):
        for new_app in new_apps:

            appid = new_app.appid
            if (appid.parent is not None and int(appid.parent) in self._storing_map.license_lookup):
                self._parsing_status.apps_to_parse -= 1
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
        cache_json['version'] = self.version
        return json.dumps(cache_json)

    def loads(self, persistent_cache):
        cache = json.loads(persistent_cache)

        if 'version' not in cache or cache['version'] != self.version:
            logging.error("New plugin version, refreshing cache")
            return

        #assume this will work, then fallback to the migration code if it doesn't. (aka optimistic checking)
        #we do it this way because migration only occurs once, so there's no point doing the more costly migration unless necessary.
        try:
            self._storing_map = LicensesCache.from_json(cache['licenses'])
        except KeyError:
            self._storing_map = LicensesCache.migrateV1(cache['licenses'])

        self._storing_map.apps

        logging.info(f"Loaded games from cache {self._storing_map}")
