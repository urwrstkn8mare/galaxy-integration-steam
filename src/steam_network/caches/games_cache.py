from __future__ import annotations

import asyncio
import copy
import json
import logging
from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, List, NamedTuple, Optional, Set

from dataclasses_json import dataclass_json

from ..w3_hack import WITCHER_3_DLCS_APP_IDS
from .cache_proto import ProtoCache

logger = logging.getLogger(__name__)


@dataclass_json
@dataclass
class App:
    appid: str
    title: str
    type_: str
    parent: Optional[str]


# if i'm not mistaken, we can probably remove this class in favor of just using Apps.
# some terminology first:
# - App: any entity in the steam store (be it a game, a dlc, a tool, or else; all of which are Apps); an App may be referenced in multiple packages or have a parent App if it's a DLC/tool
# - Package: probably "things you can buy in the steam store"; can contain one or more apps (e.g. a single game or a bundle of several games)
#
# after a long afternoon of debugging i have the feeling that packages (as referenced
# by/in SteamLicense and GameLicense) are just entities you can buy in the steam store.
# these packages may contain a single game or be a bundle of several games which explains
# why they contain one or more appids. these appids are the actual games/programs you own
# which we need to report to Galaxy.
# that means that if we pass on the `shared' flag to Apps (which we need to distinguish
# owned games from shared games) we can get rid of all the **License classes because
# we can get all information we need from the App list:
# * DLCs: Apps which have a parent and have type dlc (filter by the parent to get the game-specific list of DLCs)
# * Games: Apps which don't have a parent and have type game (and maybe even demo if we want)
# * Tools: Apps which may or may not have a parent and type tool
# given that, there's no need to hold onto the License information from my perspective
@dataclass_json
@dataclass
class GameLicense:
    package_id: str
    shared: bool
    app_ids: Set[int] = field(default_factory=set)


@dataclass_json
@dataclass
class LicensesCache:
    license_lookup: Dict[int, GameLicense] = field(default_factory=dict)
    dlc_lookup: Dict[int, Set[int]] = field(default_factory=dict)  # this resolves games/programs to their DLCs/components/etc
    apps: Dict[int, App] = field(default_factory=dict)

    @classmethod
    def migrateV1(cls, data: str) -> LicensesCache:
        obj = json.loads(data)

        for appid in obj.get("apps", {}):
            app = obj["apps"][appid]

            if "type" in app:
                app["type_"] = app["type"]
                del app["type"]

        if "licenses" in obj:
            obj["license_lookup"] = { int(item.package_id): item for item in obj["licenses"]}

        return LicensesCache.from_dict(obj)


@dataclass
class ParsingStatus:
    packages_to_parse: Set[int] = field(default_factory=set)
    apps_to_parse: Set[int] = field(default_factory=set)


class SteamLicense(NamedTuple):
    package_id: int
    access_token: int
    shared: bool


class GamesCache(ProtoCache):

    _VERSION = "1.1.0"

    def __init__(self):
        super(GamesCache, self).__init__()
        self._storing_map: LicensesCache = LicensesCache()

        self._sent_apps: Set[str] = set()

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
        self._parsing_status.packages_to_parse.clear()  # reset any leftovers
        logger.debug('Licenses to parse: %d, cached package_ids: %d', len(steam_licenses), len(package_ids))
        for steam_license in steam_licenses:
            if steam_license.package_id in package_ids:
                continue
            pid = steam_license.package_id
            self._storing_map.license_lookup[pid] = \
                GameLicense(package_id=str(pid), shared=steam_license.shared)
            self._parsing_status.packages_to_parse.add(steam_license.package_id)

        self._parsing_status.apps_to_parse.clear()  # reset leftovers in the apps queue
        self._update_ready_state()

    def consume_added_games(self) -> List[App]:
        apps = self._apps_added
        self._apps_added = []
        games = []
        for app in apps:
            self._sent_apps.add(app.appid)
            if app.type_ == "game":
                games.append(app)
        return games

    def get_package_ids(self) -> Set[int]:
        if not self._storing_map:
            return set()
        return set(self._storing_map.license_lookup.keys())

    def get_resolved_packages(self) -> Set[int]:
        if not self._storing_map:
            return set()
        packages: Set[int] = set()
        storing_map = copy.copy(self._storing_map)
        for game_license in storing_map.license_lookup.values():
            if game_license.app_ids:
                resolved = True
                for app in game_license.app_ids:
                    if app not in storing_map.apps:
                        resolved = False
                        logger.debug(f"app {app} unresolved in package {game_license.package_id}")
                if resolved:
                    packages.add(int(game_license.package_id))
        return packages

    def update_packages(self):
        raise Exception("not sure if this is correct")
        self._parsing_status.packages_to_parse -= 1
        self._update_ready_state()

    async def __consume_resolved_apps(self, shared_licenses: bool, apptype: str) -> AsyncGenerator[App, None]:
        storing_map = copy.copy(self._storing_map)

        # this one needs a rework because it returns the same app multiple times if it's referenced in more than one package
        # see comment on GameLicense for more info
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
                    self._sent_apps.add(app.appid)
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

    def add_packages(self, packages_with_apps: Dict[int, List[int]]):
        for package_id, apps in packages_with_apps.items():
            self._parsing_status.packages_to_parse.discard(package_id)
            self._parsing_status.apps_to_parse.update(apps)

            if package_id not in self._storing_map.license_lookup:
                logger.debug(f"adding {package_id} to license lookup table")
                self._storing_map.license_lookup[package_id] = GameLicense(package_id=package_id)

            logger.debug(f"updating apps for package {package_id}: {apps}")
            self._storing_map.license_lookup[package_id].app_ids.update(apps)

        logger.debug(f"package keys {self._storing_map.license_lookup.keys()}")
        self._update_ready_state()

    def add_apps(self, new_apps: List[App]):
        logger.info(f"adding {len(new_apps)} apps to game cache")
        for new_app in new_apps:
            logger.debug(f"updating app {new_app.appid} ({new_app.title}); parent: {new_app.parent}")
            self._parsing_status.apps_to_parse.discard(int(new_app.appid))
            self._storing_map.apps[int(new_app.appid)] = new_app

            # if the app has a parent, it's a DLC/component/etc and the lookup table needs an update
            if new_app.parent:
                parent = int(new_app.parent)
                if parent not in self._storing_map.dlc_lookup:
                    self._storing_map.dlc_lookup[parent] = set()
                self._storing_map.dlc_lookup[parent].add(int(new_app.appid))

            # add game lever is probably set after the initial import is done
            if self.add_game_lever and new_app.appid not in self._sent_apps:
                self._apps_added.append(new_app)

        self._update_ready_state()

    def _update_ready_state(self):
        logger.debug(f"READY STATE -- packages: {len(self._parsing_status.packages_to_parse)} | apps: {len(self._parsing_status.apps_to_parse)}")
        if len(self._parsing_status.packages_to_parse) == 0 and len(self._parsing_status.apps_to_parse) == 0:
            if self._ready_event.is_set():
                return
            logger.info("Setting state to ready")
            self._ready_event.set()
        else:
            self._ready_event.clear()

    def get_dlcs_for_game(self, game_id: int) -> List[App]:
        # this should work but I don't know where to see the DLCs in Galaxy
        # so, as long I'm not proven otherwise, I declare this to be working as intended
        if game_id not in self._storing_map.dlc_lookup:
            return []

        dlcs = [self._storing_map.apps[appid] for appid in self._storing_map.dlc_lookup[game_id]]
        logger.debug(f"retrieved dlcs for game {game_id}: {[dlc.appid for dlc in dlcs]}")

        return dlcs

    def dump(self):
        cache_json = {}
        cache_json['licenses'] = self._storing_map.to_json()
        cache_json['version'] = self.version
        return json.dumps(cache_json)

    def loads(self, persistent_cache):
        cache = json.loads(persistent_cache)

        if 'version' not in cache or cache['version'] != self.version:
            logger.error("New plugin version, refreshing cache")
            return

        #assume this will work, then fallback to the migration code if it doesn't. (aka optimistic checking)
        #we do it this way because migration only occurs once, so there's no point doing the more costly migration unless necessary.
        try:
            self._storing_map = LicensesCache.from_json(cache['licenses'])
        except KeyError:
            self._storing_map = LicensesCache.migrateV1(cache['licenses'])

        logger.info(f"Loaded games from cache {self._storing_map}")
