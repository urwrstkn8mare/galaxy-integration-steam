import asyncio
import logging
import enum
import galaxy.api.errors

from protocol.protobuf_client import ProtobufClient
from protocol.consts import EResult, EFriendRelationship, EPersonaState
from friends_cache import FriendsCache
from games_cache import GamesCache
from stats_cache import StatsCache
from user_info_cache import UserInfoCache
from times_cache import TimesCache


logger = logging.getLogger(__name__)

def translate_error(result: EResult):
    assert result != EResult.OK
    data = {
        "result": result
    }
    if result in (
        EResult.InvalidPassword,
        EResult.AccountNotFound,
        EResult.InvalidSteamID,
        EResult.InvalidLoginAuthCode,
        EResult.AccountLogonDeniedNoMailSent,
        EResult.AccountLoginDeniedNeedTwoFactor,
        EResult.TwoFactorCodeMismatch,
        EResult.TwoFactorActivationCodeMismatch
    ):
        return galaxy.api.errors.InvalidCredentials(data)
    if result in (
        EResult.ConnectFailed,
        EResult.IOFailure,
        EResult.RemoteDisconnect
    ):
        return galaxy.api.errors.NetworkError(data)
    if result in (
        EResult.Busy,
        EResult.ServiceUnavailable,
        EResult.Pending,
        EResult.IPNotFound,
        EResult.TryAnotherCM,
        EResult.Cancelled
    ):
        return galaxy.api.errors.BackendNotAvailable(data)
    if result == EResult.Timeout:
        return galaxy.api.errors.BackendTimeout(data)
    if result in (
        EResult.RateLimitExceeded,
        EResult.LimitExceeded,
        EResult.Suspended,
        EResult.AccountLocked,
        EResult.AccountLogonDeniedVerifiedEmailRequired
    ):
        return galaxy.api.errors.TemporaryBlocked(data)
    if result == EResult.Banned:
        return galaxy.api.errors.Banned(data)
    if result in (
        EResult.AccessDenied,
        EResult.InsufficientPrivilege,
        EResult.LogonSessionReplaced,
        EResult.Blocked,
        EResult.Ignored,
        EResult.AccountDisabled,
        EResult.AccountNotFeatured
    ):
        return galaxy.api.errors.AccessDenied(data)
    if result in (
        EResult.DataCorruption,
        EResult.DiskFull,
        EResult.RemoteCallFailed,
        EResult.RemoteFileConflict,
        EResult.BadResponse
    ):
        return galaxy.api.errors.BackendError()

    return galaxy.api.errors.UnknownError(data)


class UserActionRequired(enum.IntEnum):
    NoActionRequired = 0
    EmailTwoFactorInputRequired = 1
    PhoneTwoFactorInputRequired = 2
    PasswordRequired = 3
    InvalidAuthData = 4


class ProtocolClient:
    _STATUS_FLAG = 1106

    def __init__(self, socket, friends_cache: FriendsCache, games_cache: GamesCache, translations_cache: dict, stats_cache: StatsCache, times_cache: TimesCache, user_info_cache: UserInfoCache):

        self._protobuf_client = ProtobufClient(socket)
        self._protobuf_client.log_on_handler = self._log_on_handler
        self._protobuf_client.log_off_handler = self._log_off_handler
        self._protobuf_client.relationship_handler = self._relationship_handler
        self._protobuf_client.user_info_handler = self._user_info_handler
        self._protobuf_client.user_nicknames_handler = self._user_nicknames_handler
        self._protobuf_client.app_info_handler = self._app_info_handler
        self._protobuf_client.license_import_handler = self._license_import_handler
        self._protobuf_client.package_info_handler = self._package_info_handler
        self._protobuf_client.translations_handler = self._translations_handler
        self._protobuf_client.stats_handler = self._stats_handler
        self._protobuf_client.times_handler = self._times_handler
        self._protobuf_client.user_authentication_handler = self._user_authentication_handler
        self._protobuf_client.sentry = self._get_sentry
        self._protobuf_client.times_import_finished_handler = self._times_import_finished_handler
        self._friends_cache = friends_cache
        self._games_cache = games_cache
        self._translations_cache = translations_cache
        self._stats_cache = stats_cache
        self._user_info_cache = user_info_cache
        self._times_cache = times_cache
        self._auth_lost_handler = None
        self._login_future = None

    async def close(self, is_socket_connected):
        await self._protobuf_client.close(is_socket_connected)

    async def wait_closed(self):
        await self._protobuf_client.wait_closed()

    async def run(self):
        await self._protobuf_client.run()

    # TODO: Remove - Steamcommunity auth element
    async def authenticate_web_auth(self, steam_id, miniprofile_id, account_name, token, auth_lost_handler):
        loop = asyncio.get_running_loop()
        self._login_future = loop.create_future()
        await self._protobuf_client.log_on_web_auth(steam_id, miniprofile_id, account_name, token)
        result = await self._login_future
        if result == EResult.OK:
            self._auth_lost_handler = auth_lost_handler
        else:
            raise translate_error(result)

    async def authenticate_password(self, account_name, password, two_factor, two_factor_type, auth_lost_handler):
        loop = asyncio.get_running_loop()
        self._login_future = loop.create_future()
        await self._protobuf_client.log_on_password(account_name, password, two_factor, two_factor_type)
        result = await self._login_future
        logger.info(result)
        if result == EResult.OK:
            self._auth_lost_handler = auth_lost_handler
        elif result == EResult.AccountLogonDenied:
            self._auth_lost_handler = auth_lost_handler
            return UserActionRequired.EmailTwoFactorInputRequired
        elif result == EResult.AccountLoginDeniedNeedTwoFactor:
            self._auth_lost_handler = auth_lost_handler
            return UserActionRequired.PhoneTwoFactorInputRequired
        elif result in (EResult.InvalidPassword,
                        EResult.InvalidSteamID,
                        EResult.AccountNotFound,
                        EResult.InvalidLoginAuthCode,
                        EResult.TwoFactorCodeMismatch,
                        EResult.TwoFactorActivationCodeMismatch
                        ):
            self._auth_lost_handler = auth_lost_handler
            return UserActionRequired.InvalidAuthData
        else:
            logger.warning(f"Received unknown error, code: {result}")
            raise translate_error(result)

        await self._protobuf_client.account_info_retrieved.wait()
        await self._protobuf_client.login_key_retrieved.wait()
        return UserActionRequired.NoActionRequired

    async def authenticate_token(self, steam_id, account_name, token, auth_lost_handler):
        loop = asyncio.get_running_loop()
        self._login_future = loop.create_future()
        await self._protobuf_client.log_on_token(steam_id, account_name, token)
        result = await self._login_future
        if result == EResult.OK:
            self._auth_lost_handler = auth_lost_handler
        elif result == EResult.InvalidPassword:
            raise galaxy.api.errors.BackendError()
        else:
            logger.warning(f"Received unknown error, code: {result}")
            raise translate_error(result)

        await self._protobuf_client.account_info_retrieved.wait()
        return UserActionRequired.NoActionRequired

    async def import_game_stats(self, game_ids):
        for game_id in game_ids:
            self._protobuf_client.job_list.append({"job_name": "import_game_stats",
                                                   "game_id": game_id})

    async def import_game_times(self):
        self._protobuf_client.job_list.append({"job_name": "import_game_times"})

    async def retrieve_collections(self):
        self._protobuf_client.job_list.append({"job_name": "import_collections"})
        await self._protobuf_client.collections['event'].wait()
        collections = self._protobuf_client.collections['collections'].copy()
        self._protobuf_client.collections['event'].clear()
        self._protobuf_client.collections['collections'] = dict()
        return collections

    async def _log_on_handler(self, result: EResult):
        assert self._login_future is not None
        self._login_future.set_result(result)

    async def _log_off_handler(self, result):
        logger.warning("Logged off, result: %d", result)
        if self._auth_lost_handler is not None:
            await self._auth_lost_handler(translate_error(result))

    async def _relationship_handler(self, incremental, friends):
        logger.info(f"Received relationships: incremental={incremental}, friends={friends}")
        initial_friends = []
        new_friends = []
        for user_id, relationship in friends.items():
            if relationship == EFriendRelationship.Friend:
                if incremental:
                    self._friends_cache.add(user_id)
                    new_friends.append(user_id)
                else:
                    initial_friends.append(user_id)
            elif relationship == EFriendRelationship.None_:
                assert incremental
                self._friends_cache.remove(user_id)

        if not incremental:
            self._friends_cache.reset(initial_friends)
            # set online state to get friends statuses
            await self._protobuf_client.set_persona_state(EPersonaState.Invisible)
            await self._protobuf_client.get_friends_statuses()
            await self._protobuf_client.get_user_infos(initial_friends, self._STATUS_FLAG)

        if new_friends:
            await self._protobuf_client.get_friends_statuses()
            await self._protobuf_client.get_user_infos(new_friends, self._STATUS_FLAG)

    async def _user_info_handler(self, user_id, user_info):
        logger.info(f"Received user info: user_id={user_id}, user_info={user_info}")
        await self._friends_cache.update(user_id, user_info)

    async def _user_nicknames_handler(self, nicknames):
        logger.info(f"Received user nicknames {nicknames}")
        self._friends_cache.update_nicknames(nicknames)

    async def _license_import_handler(self, licenses_to_check):
        packages = []
        package_ids = []

        not_resolved_packages = []
        not_resolved_packages_ids = []

        resolved_packages = self._games_cache.get_resolved_packages()

        for package_id in licenses_to_check:
            packages.append({'package_id': str(package_id),
                                'shared':licenses_to_check[package_id]['shared']})
            package_ids.append(str(package_id))
            if str(package_id) not in resolved_packages:
                not_resolved_packages.append({'package_id': str(package_id),
                                 'shared': licenses_to_check[package_id]['shared']})
                not_resolved_packages_ids.append(str(package_id))

        if self._games_cache.get_package_ids() != package_ids:
            logger.info("Licenses list different than last time")
            logger.info(f"Starting license import for {package_ids}")
            self._games_cache.reset_storing_map()
            self._games_cache.start_packages_import(packages)
            return await self._protobuf_client.get_packages_info(package_ids)

        # This path will only attempt import on packages which aren't resolved (dont have any apps assigned)

        logger.info(f"Starting license import for {not_resolved_packages_ids}")
        logger.info(f"Skipping already resolved packages {resolved_packages}")

        self._games_cache.start_packages_import(not_resolved_packages)

        await self._protobuf_client.get_packages_info(not_resolved_packages_ids)

    async def _app_info_handler(self, appid, mother_appid=None, title=None, game=None):
        self._games_cache.update(mother_appid, appid, title, game)

    async def _package_info_handler(self, package_id):
        self._games_cache.update_packages(package_id)

    async def _translations_handler(self, appid, translations=None):
        if appid and translations:
            self._translations_cache[appid] = translations[0]
        elif appid not in self._translations_cache:
            self._translations_cache[appid] = None
            await self._protobuf_client.get_presence_localization(appid)

    async def _stats_handler(self, game_id, stats, achievements):
        self._stats_cache.update_stats(str(game_id), stats, achievements)

    async def _user_authentication_handler(self, key, value):
        logger.info(f"Updating user info cache with new {key}")
        if key == 'token':
            self._user_info_cache.token = value
        if key == 'steam_id':
            self._user_info_cache.steam_id = value
        if key == 'account_id':
            self._user_info_cache.account_id = value
        if key == 'account_username':
            self._user_info_cache.account_username = value
        if key == 'persona_name':
            self._user_info_cache.persona_name = value
        if key == 'two_step':
            self._user_info_cache.two_step = value
        if key == 'sentry':
            self._user_info_cache.sentry = value

    async def _get_sentry(self):
        return self._user_info_cache.sentry

    async def _times_handler(self, game_id, time_played, last_played):
        self._times_cache.update_time(str(game_id), time_played, last_played)

    async def _times_import_finished_handler(self, finished):
        self._times_cache.times_import_finished(finished)
