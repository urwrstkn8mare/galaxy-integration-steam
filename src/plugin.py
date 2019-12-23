import asyncio
import json
import logging
import platform
import random
import re
import subprocess
import ssl
import sys
import webbrowser
import time
from http.cookies import SimpleCookie, Morsel
from typing import Any, Dict, List, Optional, NewType

import certifi
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import (
    Achievement, Authentication, Cookie, Game, GameTime, LicenseInfo, NextStep,
    LocalGame, LocalGameState, GameLibrarySettings, UserPresence
)
from galaxy.api.errors import (
    AuthenticationRequired, UnknownBackendResponse, AccessDenied, InvalidCredentials, UnknownError
)
from galaxy.api.consts import Platform, LicenseType
from galaxy.api.jsonrpc import InvalidParams

import achievements_cache
from backend import SteamHttpClient, AuthenticatedHttpClient, UnfinishedAccountSetup
from cache import Cache
from client import local_games_list, get_state_changes, get_client_executable
from servers_cache import ServersCache
from presence import from_user_info
from friends_cache import FriendsCache
from games_cache import GamesCache
from persistent_cache_state import PersistentCacheState
from protocol.websocket_client import WebSocketClient
from protocol.types import UserInfo
from registry_monitor import get_steam_registry_monitor
from uri_scheme_handler import is_uri_handler_installed
from version import __version__
from leveldb_parser import LevelDbParser


logger = logging.getLogger(__name__)

Timestamp = NewType('Timestamp', int)


def is_windows():
    return platform.system().lower() == "windows"


LOGIN_URI = r"https://steamcommunity.com/login/home/?goto="
JS_PERSISTENT_LOGIN = r"document.getElementById('remember_login').checked = true;"
END_URI_REGEX = r"^https://steamcommunity.com/(profiles|id)/.*"


AUTH_PARAMS = {
    "window_title": "Login to Steam",
    "window_width": 640,
    "window_height": 462 if is_windows() else 429,
    "start_uri": LOGIN_URI,
    "end_uri_regex": END_URI_REGEX
}


def morsels_to_dicts(morsels):
    cookies = []
    for morsel in morsels:
        cookie = {
            "name": morsel.key,
            "value": morsel.value,
            "domain": morsel["domain"],
            "path": morsel["path"]
        }
        cookies.append(cookie)
    return cookies


def dicts_to_morsels(cookies):
    morsels = []
    for cookie in cookies:
        name = cookie["name"]
        value = cookie["value"]
        m = Morsel()
        m.set(name, value, value)
        m["domain"] = cookie.get("domain", "")
        m["path"] = cookie.get("path", "")
        morsels.append(m)
    return morsels


def parse_stored_cookies(cookies):
    if isinstance(cookies, dict):
        cookies = [{"name": key, "value": value} for key, value in cookies.items()]
    return dicts_to_morsels(cookies)


class SteamPlugin(Plugin):
    def __init__(self, reader, writer, token):
        super().__init__(Platform.Steam, __version__, reader, writer, token)
        self._steam_id = None
        self._miniprofile_id = None
        self._level_db_parser = None
        self._regmon = get_steam_registry_monitor()
        self._local_games_cache: Optional[List[LocalGame]] = None
        self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._ssl_context.load_verify_locations(certifi.where())
        self._http_client = AuthenticatedHttpClient()
        self._client = SteamHttpClient(self._http_client)
        self._persistent_storage_state = PersistentCacheState()
        self._servers_cache = ServersCache(
            self._client, self._ssl_context, self.persistent_cache, self._persistent_storage_state
        )
        self._friends_cache = FriendsCache()
        self._games_cache = GamesCache()
        self._steam_client = WebSocketClient(self._client, self._ssl_context, self._servers_cache, self._friends_cache, self._games_cache)
        self._achievements_cache = Cache()
        self._achievements_cache_updated = False

        self._achievements_semaphore = asyncio.Semaphore(20)
        self._tags_semaphore = asyncio.Semaphore(5)

        self._library_settings_import_iterator = 0
        self._last_launch: Timestamp = 0

        self._update_local_games_task = None
        self._update_owned_games_task = None

        def user_presence_update_handler(user_id: str, user_info: UserInfo):
            self.update_user_presence(user_id, from_user_info(user_info))

        self._friends_cache.updated_handler = user_presence_update_handler

    def _store_cookies(self, cookies):
        credentials = {
            "cookies": morsels_to_dicts(cookies)
        }
        self.store_credentials(credentials)

    @staticmethod
    def _create_two_factor_fake_cookie():
        return Cookie(
            # random SteamID with proper "instance", "type" and "universe" fields
            # (encoded in most significant bits)
            name="steamMachineAuth{}".format(random.randint(1, 2 ** 32 - 1) + 0x01100001 * 2 ** 32),
            # 40-bit random string encoded as hex
            value=hex(random.getrandbits(20 * 8))[2:].upper()
        )

    async def shutdown(self):
        self._regmon.close()
        await self._steam_client.close()
        await self._http_client.close()
        await self._steam_client.wait_closed()

    def handshake_complete(self):
        achievements_cache_ = self.persistent_cache.get("achievements")
        if achievements_cache_ is not None:
            try:
                achievements_cache_ = json.loads(achievements_cache_)
                self._achievements_cache = achievements_cache.from_dict(achievements_cache_)
            except Exception:
                logger.exception("Can not deserialize achievements cache")

    async def _do_auth(self, morsels):
        cookies = [(morsel.key, morsel) for morsel in morsels]

        self._http_client.update_cookies(cookies)
        self._http_client.set_cookies_updated_callback(self._store_cookies)
        self._force_utc()

        try:
            profile_url = await self._client.get_profile()
        except UnknownBackendResponse:
            raise InvalidCredentials()

        async def set_profile_data(profile_url):
            try:
                self._steam_id, self._miniprofile_id, login = await self._client.get_profile_data(profile_url)
                self.create_task(self._steam_client.run(), "Run WebSocketClient")
                return login
            except AccessDenied:
                raise InvalidCredentials()

        try:
            login = await set_profile_data(profile_url)
        except UnfinishedAccountSetup:
            await self._client.setup_steam_profile(profile_url)
            login = await set_profile_data(profile_url)

        self._http_client.set_auth_lost_callback(self.lost_authentication)

        if "steamRememberLogin" in (cookie[0] for cookie in cookies):
            logging.debug("Remember login cookie present")
        else:
            logging.debug("Remember login cookie not present")

        return Authentication(self._steam_id, login)

    def _force_utc(self):
        cookies = SimpleCookie()
        cookies["timezoneOffset"] = "0,0"
        morsel = cookies["timezoneOffset"]
        morsel["domain"] = "steamcommunity.com"
        # override encoding (steam does not fallow RFC 6265)
        morsel.set("timezoneOffset", "0,0", "0,0")
        self._http_client.update_cookies(cookies)

    async def authenticate(self, stored_credentials=None):
        if not stored_credentials:
            if await self._client.get_steamcommunity_response_status() != 200:
                logger.error("Steamcommunity website not accessible")
            return NextStep(
                "web_session",
                AUTH_PARAMS,
                [self._create_two_factor_fake_cookie()],
                {re.escape(LOGIN_URI): [JS_PERSISTENT_LOGIN]}
            )

        cookies = stored_credentials.get("cookies", [])
        morsels = parse_stored_cookies(cookies)
        return await self._do_auth(morsels)

    async def pass_login_credentials(self, step, credentials, cookies):
        try:
            morsels = dicts_to_morsels(cookies)
        except Exception:
            raise InvalidParams()

        auth_info = await self._do_auth(morsels)
        self._store_cookies(morsels)
        return auth_info

    async def get_owned_games(self):
        if self._steam_id is None:
            raise AuthenticationRequired()

        await self._games_cache.wait_ready(10)
        owned_games = []
        try:
            for game_id, game_title in self._games_cache:
                owned_games.append(
                    Game(
                        str(game_id),
                        game_title,
                        [],
                        LicenseInfo(LicenseType.SinglePurchase, None)
                    )
                )
        except (KeyError, ValueError):
            logger.exception("Can not parse backend response")
            raise UnknownBackendResponse()

        return owned_games

    async def prepare_game_times_context(self, game_ids: List[str]) -> Any:
        if self._steam_id is None:
            raise AuthenticationRequired()

        return await self._get_game_times_dict()

    async def get_game_time(self, game_id: str, context: Any) -> GameTime:
        game_time = context.get(game_id)
        if game_time is None:
            raise UnknownError("Game {} not owned".format(game_id))
        return game_time

    async def _get_game_times_dict(self) -> Dict[str, GameTime]:
        games = await self._client.get_games(self._steam_id)

        game_times = {}

        try:
            for game in games:
                game_id = str(game["appid"])
                last_played = game.get("last_played")
                if last_played == 86400:
                    # 86400 is used as sentinel value for games no supporting last_played
                    last_played = None
                game_times[game_id] = GameTime(
                    game_id,
                    int(float(game.get("hours_forever", "0").replace(",", "")) * 60),
                    last_played
                )
        except (KeyError, ValueError):
            logger.exception("Can not parse backend response")
            raise UnknownBackendResponse()

        return game_times

    async def prepare_game_library_settings_context(self, game_ids: List[str]) -> Any:
        if self._steam_id is None:
            raise AuthenticationRequired()

        if not self._level_db_parser:
            self._level_db_parser = LevelDbParser(self._miniprofile_id)

        self._level_db_parser.parse_leveldb()

        if not self._level_db_parser.lvl_db_is_present:
            return None
        else:
            leveldb_static_games_collections_dict = self._level_db_parser.get_static_collections_tags()
            logger.info(f"Leveldb static settings dict {leveldb_static_games_collections_dict}")
            return leveldb_static_games_collections_dict

    async def get_game_library_settings(self, game_id: str, context: Any) -> GameLibrarySettings:
        if not context:
            return GameLibrarySettings(game_id, None, None)
        else:
            game_tags = context.get(game_id)
            if not game_tags:
                return GameLibrarySettings(game_id, [], False)

            hidden = False
            for tag in game_tags:
                if tag.lower() == 'hidden':
                    hidden = True
            if hidden:
                game_tags.remove('hidden')
            return GameLibrarySettings(game_id, game_tags, hidden)

    async def prepare_achievements_context(self, game_ids: List[str]) -> Any:
        if self._steam_id is None:
            raise AuthenticationRequired()

        return await self._get_game_times_dict()

    async def get_unlocked_achievements(self, game_id: str, context: Any) -> List[Achievement]:
        game_time = await self.get_game_time(game_id, context)

        fingerprint = achievements_cache.Fingerprint(game_time.last_played_time, game_time.time_played)
        achievements = self._achievements_cache.get(game_id, fingerprint)

        if achievements is not None:
            # return from cache
            return achievements

        # fetch from backend and update cache
        achievements = await self._get_achievements(game_id)
        self._achievements_cache.update(game_id, achievements, fingerprint)
        self._achievements_cache_updated = True
        return achievements

    def achievements_import_complete(self) -> None:
        if self._achievements_cache_updated:
            self._persistent_storage_state.modified = True
            self._achievements_cache_updated = False

    async def _get_achievements(self, game_id):
        async with self._achievements_semaphore:
            achievements = await self._client.get_achievements(self._steam_id, game_id)
            return [Achievement(unlock_time, None, name) for unlock_time, name in achievements]

    async def get_friends(self):
        if self._steam_id is None:
            raise AuthenticationRequired()

        return await self._client.get_friends(self._steam_id)

    async def prepare_user_presence_context(self, user_ids: List[str]) -> Any:
        return await self._steam_client.get_friends_info(user_ids)

    async def get_user_presence(self, user_id: str, context: Any) -> UserPresence:
        user_info = context.get(user_id)
        if user_info is None:
            raise UnknownError(
                "User {} not in friend list (plugin only supports fetching presence for friends)".format(user_id)
            )

        return from_user_info(user_info)

    async def _update_owned_games(self):
        new_games = self._games_cache.get_added_games()
        for game in new_games:
            self.add_game(Game(game, new_games[game], [], license_info=LicenseInfo(LicenseType.SinglePurchase)))

    def tick(self):
        if self._local_games_cache is not None and \
                (self._update_local_games_task is None or self._update_local_games_task.done()) and \
                self._regmon.is_updated():
            self._update_local_games_task = self.create_task(self._update_local_games(), "Update local games")
        if self._update_owned_games_task is None or self._update_owned_games_task.done():
            self._update_owned_games_task = self.create_task(self._update_owned_games(), "Update owned games")

        if self._persistent_storage_state.modified:
            # serialize
            self.persistent_cache["achievements"] = achievements_cache.as_dict(self._achievements_cache)
            self.push_cache()
            self._persistent_storage_state.modified = False

    async def _update_local_games(self):
        loop = asyncio.get_running_loop()
        new_list = await loop.run_in_executor(None, local_games_list)
        notify_list = get_state_changes(self._local_games_cache, new_list)
        self._local_games_cache = new_list
        for game in notify_list:
            if LocalGameState.Running in game.local_game_state:
                self._last_launch = time.time()
            self.update_local_game_status(game)

    async def get_local_games(self):
        loop = asyncio.get_running_loop()
        self._local_games_cache = await loop.run_in_executor(None, local_games_list)
        return self._local_games_cache

    @staticmethod
    def _steam_command(command, game_id):
        if is_uri_handler_installed("steam"):
            webbrowser.open("steam://{}/{}".format(command, game_id))
        else:
            webbrowser.open("https://store.steampowered.com/about/")

    async def launch_game(self, game_id):
        SteamPlugin._steam_command("launch", game_id)

    async def install_game(self, game_id):
        SteamPlugin._steam_command("install", game_id)

    async def uninstall_game(self, game_id):
        SteamPlugin._steam_command("uninstall", game_id)

    async def shutdown_platform_client(self) -> None:
        launch_debounce_time = 3
        if time.time() < self._last_launch + launch_debounce_time:
            # workaround for quickly closed game (Steam sometimes dumps false positive just after a launch)
            logging.info('Ignoring shutdown request because game was launched a moment ago')
            return
        if is_windows():
            exe = get_client_executable()
            if exe is None:
                return
            cmd = '"{}" -shutdown -silent'.format(exe)
        else:
            cmd = "osascript -e 'quit app \"Steam\"'"
        logger.debug("Running command '%s'", cmd)
        process = await asyncio.create_subprocess_shell(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await process.communicate()


def main():
    create_and_run_plugin(SteamPlugin, sys.argv)


if __name__ == "__main__":
    main()
