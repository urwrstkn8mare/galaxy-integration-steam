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
    appid: int  # id of the app
    title: str  # name of the app
    type_: str  # game, dlc, demo, tool, etc
    parent: Optional[int]  # if an app is a DLC/tool/etc, this specifies the parent app (aka base game)
    shared: bool = False  # true if (family) sharing

    _sent_to_galaxy: bool = False  # internal flag indicating whether we already sent this to Galaxy


@dataclass_json
@dataclass
class LicensesCache:
    dlc_lookup: Dict[int, Set[int]] = field(default_factory=dict)  # this resolves games/programs to their DLCs/components/etc
    apps: Dict[int, App] = field(default_factory=dict)

    def reset(self) -> None:
        self.dlc_lookup.clear()
        self.apps.clear()


@dataclass
class ParsingStatus:
    packages_to_parse: Set[int] = field(default_factory=set)
    apps_to_parse: Set[int] = field(default_factory=set)


class SteamLicense(NamedTuple):
    package_id: int
    access_token: int
    shared: bool


class SteamPackage(NamedTuple):
    package_id: int
    app_ids: List[int] = field(default_factory=list)


class GamesCache(ProtoCache):
    _VERSION = "1.2.0"

    def __init__(self):
        super(GamesCache, self).__init__()
        self._cache: LicensesCache = LicensesCache()

        # the list of licenses a user owns; we need these to request the
        # package information which contains the appids etc. no need to
        # save this to permanent cache because steam sends us the list
        # of licenses after each hello request anyway
        self._licenses: Dict[int, SteamLicense] = dict()  # maps package_id -> license for faster lookups

        self._parsing_status = ParsingStatus()

    @property
    def version(self):
        return self._VERSION

    def reset_storing_map(self):
        self._cache.reset()

    def start_packages_import(self, steam_licenses: List[SteamLicense]) -> List[SteamLicense]:
        """Adds unknown/new licenses to cache and returns the list of SteamLicenses which we need to import"""
        self._parsing_status.packages_to_parse.clear()  # reset any leftovers
        self._parsing_status.apps_to_parse.clear()  # reset leftovers in the apps queue

        logger.debug('Licenses to parse: %d, cached package_ids: %d', len(steam_licenses), len(self._licenses))

        packages_to_import: List[SteamLicense] = list()

        for steam_license in steam_licenses:
            if steam_license.package_id in self._licenses:
                continue

            pid = steam_license.package_id
            self._licenses[pid] = steam_license
            self._parsing_status.packages_to_parse.add(steam_license.package_id)
            packages_to_import.append(steam_license)

        self._update_ready_state()
        return packages_to_import

    def get_apps_to_import_into_galaxy(self, type_: str = "game") -> List[App]:
        return list(filter(lambda app: app.type_ == type_ and not app._sent_to_galaxy, self._cache.apps.values()))

    def mark_app_as_sent_to_galaxy(self, app_id: int) -> None:
        app = self._cache.apps.get(app_id)
        if not app:
            return

        app._sent_to_galaxy = True

    async def get_apps(self, type_: str = "game", shared: bool = False) -> AsyncGenerator[App, None]:
        cache = self._cache.apps.copy()

        # this one needs a rework because it returns the same app multiple times if it's referenced in more than one package
        # see comment on GameLicense for more info
        for app in cache.values():
            await asyncio.sleep(0.0001)  # do not block event loop; waiting one frame (0) was not enough 78#issuecomment-687140437

            if app.shared != shared:
                continue

            if app.type_ == type_:
                yield app

            # Necessary for the Witcher 3 => Witcher 3 GOTY import hack
            elif type_ == 'game' and app.type_ == 'dlc' and str(app.appid) in WITCHER_3_DLCS_APP_IDS:
                yield app


    def add_packages(self, packages: List[SteamPackage]) -> List[int]:
        """Imports the contents of the packages and returns the list of appids which need to be imported"""
        logger.debug(f"importing {len(packages)} packages")

        apps_to_import: Set[int] = set()

        for package in packages:
            self._parsing_status.packages_to_parse.discard(package.package_id)
            apps_to_import.update(package.app_ids)

            logger.debug(f"updating apps for package {package.package_id}: {package.app_ids}")

        apps_to_import.difference_update(self._parsing_status.apps_to_parse)  # remove apps which are already being imported
        apps_to_import.difference_update(self._cache.apps.keys())  # remove apps we already know
        self._parsing_status.apps_to_parse.update(apps_to_import)  # add the to-be-imported apps to the state

        logger.debug(f"{len(apps_to_import)} apps need to be imported: {apps_to_import}")
        self._update_ready_state()

        return list(apps_to_import)

    def add_apps(self, new_apps: List[App]):
        """Imports the given apps into the game cache"""
        logger.info(f"importing {len(new_apps)} apps")

        for new_app in new_apps:
            self._parsing_status.apps_to_parse.discard(new_app.appid)
            if new_app.appid in self._cache.apps:
                logger.debug(f"skipping import of app {new_app.appid}: already present")
                continue  # is this safe or may we be updating apps?

            logger.debug(f"updating app {new_app.appid} ({new_app.title}); parent: {new_app.parent}")
            self._cache.apps[new_app.appid] = new_app

            # if the app has a parent, it's a DLC/component/etc and needs special treatment
            if new_app.parent:
                if new_app.parent in self._cache.apps:  # sometimes the DLCs get imported before the base game
                    new_app.shared = self._cache.apps[new_app.parent].shared  # set shared flag to value of parent app

                # update dlc lookup table
                if new_app.parent not in self._cache.dlc_lookup:
                    self._cache.dlc_lookup[new_app.parent] = set()
                self._cache.dlc_lookup[new_app.parent].add(new_app.appid)

            else: # this app is a base game, check if there already were some DLCs and update their share status
                for dlc_id in self._cache.dlc_lookup.get(new_app.appid, []):
                    self._cache.apps[dlc_id].shared = new_app.shared

        self._update_ready_state()

    def _update_ready_state(self):
        logger.debug(f"import queue status -- packages: {len(self._parsing_status.packages_to_parse)} | apps: {len(self._parsing_status.apps_to_parse)}")
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
        if game_id not in self._cache.dlc_lookup:
            return []

        dlcs = [self._cache.apps[appid] for appid in self._cache.dlc_lookup[game_id]]
        logger.debug(f"retrieved dlcs for game {game_id}: {[dlc.appid for dlc in dlcs]}")

        return dlcs

    def dump(self):
        cache_json = {
            'licenses': self._cache.to_json(),
            'version': self.version
        }
        return json.dumps(cache_json)

    def loads(self, persistent_cache):
        cache = json.loads(persistent_cache)

        if 'version' not in cache or cache['version'] != self.version:
            logger.warning("New plugin version, refreshing cache")
            return

        self._cache: LicensesCache = LicensesCache.from_json(cache['licenses'])

        logger.info(f"Loaded {len(self._cache.apps)} apps from cache")
        logger.debug(self._cache.apps)
