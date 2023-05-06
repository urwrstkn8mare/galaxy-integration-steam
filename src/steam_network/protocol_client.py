import asyncio
import logging
import secrets
from typing import Callable, List, TYPE_CHECKING, Optional, Tuple

from .steam_public_key import SteamPublicKey
from .steam_auth_polling_data import SteamPollingData

from .utils import get_os, translate_error

import galaxy.api.errors

from asyncio import Future
from .local_machine_cache import LocalMachineCache
from .protocol.protobuf_client import ProtobufClient, SteamLicense
from .protocol.consts import EResult, EFriendRelationship, EPersonaState, STEAM_CLIENT_APP_ID, EOSType
from .friends_cache import FriendsCache
from .games_cache import GamesCache
from .stats_cache import StatsCache
from .user_info_cache import UserInfoCache
from .times_cache import TimesCache
from .ownership_ticket_cache import OwnershipTicketCache

from .enums import UserActionRequired, to_UserActionWithMessage
from .utils import get_os, translate_error

from rsa import PublicKey

from .protocol.messages.steammessages_auth_pb2 import CAuthentication_BeginAuthSessionViaCredentials_Response, CAuthentication_AllowedConfirmation, CAuthentication_PollAuthSessionStatus_Response
from pprint import pformat


if TYPE_CHECKING:
    from protocol.messages import steammessages_clientserver_pb2


logger = logging.getLogger(__name__)

class ProtocolClient:
    _STATUS_FLAG = 1106

    def __init__(self,
        socket,
        friends_cache: FriendsCache,
        games_cache: GamesCache,
        translations_cache: dict,
        stats_cache: StatsCache,
        times_cache: TimesCache,
        user_info_cache: UserInfoCache,
        local_machine_cache: LocalMachineCache,
        ownership_ticket_cache: OwnershipTicketCache,
        used_server_cell_id,
    ):

        self._protobuf_client = ProtobufClient(socket)
        self._protobuf_client.rsa_handler = self._rsa_handler
        self._protobuf_client.login_handler = self._login_handler
        self._protobuf_client.two_factor_update_handler = self._two_factor_update_handler
        self._protobuf_client.poll_handler = self._poll_handler
        self._protobuf_client.log_off_handler = self._log_off_handler
        self._protobuf_client.relationship_handler = self._relationship_handler
        self._protobuf_client.user_info_handler = self._user_info_handler
        self._protobuf_client.user_nicknames_handler = self._user_nicknames_handler
        self._protobuf_client.app_info_handler = self._app_info_handler
        self._protobuf_client.package_info_handler = self._package_info_handler
        self._protobuf_client.app_ownership_ticket_handler = self._app_ownership_ticket_handler
        self._protobuf_client.license_import_handler = self._license_import_handler
        self._protobuf_client.translations_handler = self._translations_handler
        self._protobuf_client.stats_handler = self._stats_handler
        self._protobuf_client.times_handler = self._times_handler
        self._protobuf_client.user_authentication_handler = self._user_authentication_handler
        self._protobuf_client.times_import_finished_handler = self._times_import_finished_handler
        self._friends_cache = friends_cache
        self._games_cache = games_cache
        self._translations_cache = translations_cache
        self._stats_cache = stats_cache
        self._user_info_cache = user_info_cache
        self._times_cache = times_cache
        self._ownership_ticket_cache = ownership_ticket_cache
        self._auth_lost_handler = None
        self._rsa_future: Optional[Future] = None
        self._login_future: Optional[Future] = None
        self._two_factor_future: Optional[Future] = None
        self._poll_future: Optional[Future] = None
        self._used_server_cell_id = used_server_cell_id
        self._local_machine_cache = local_machine_cache
        if not self._local_machine_cache.machine_id:
            self._local_machine_cache.machine_id = self._generate_machine_id()
        self._machine_id = self._local_machine_cache.machine_id

    @staticmethod
    def _generate_machine_id():
        return secrets.token_bytes()

    async def close(self, send_log_off):
        await self._protobuf_client.close(send_log_off)

    async def wait_closed(self):
        await self._protobuf_client.wait_closed()

    async def run(self):
        await self._protobuf_client.run()

    async def get_steam_app_ownership_ticket(self):
        await self._protobuf_client.get_app_ownership_ticket(STEAM_CLIENT_APP_ID)

    async def register_auth_ticket_with_cm(self, ticket: bytes):
        await self._protobuf_client.register_auth_ticket_with_cm(ticket)

    async def finish_handshake(self):
        await self._protobuf_client.say_hello()

    async def get_rsa_public_key(self, username:str, auth_lost_handler) -> Tuple[UserActionRequired, SteamPublicKey]:
        loop = asyncio.get_running_loop()
        self._rsa_future = loop.create_future()
        await self._protobuf_client.get_rsa_public_key(username)
        (result, key) = await self._rsa_future
        self._rsa_future = None
        logger.info ("GOT RSA KEY IN PROTOCOL_CLIENT")
        if (result == EResult.OK):
            self._auth_lost_handler = auth_lost_handler
            return (UserActionRequired.PasswordRequired, key)
        elif True: #TODO: FIX ME! If you enter an improper username an error should pop but idk what eresult it is yet.
        #    self._auth_lost_handler = auth_lost_handler
            return (UserActionRequired.InvalidAuthData, key)
        #elif (result == EResult.):
        #    return UserActionRequired.InvalidAuthData
        else:
            logger.warning(f"Received unknown error, code: {result}")
            raise translate_error(result)

    async def _rsa_handler(self, result: EResult, mod: int, exp: int, timestamp: int) -> Tuple[EResult, SteamPublicKey]:
        logger.info("In Protocol_Client RSA Handler")
        spk = None
        if (result == EResult.OK):
            spk = SteamPublicKey(PublicKey(mod, exp), timestamp)
        else:
            pass #probably should get the EResult for bad username separetely from the else, but for now this will work. 
        if self._rsa_future is not None:
            self._rsa_future.set_result((result, spk))
        else:
            logger.warning("NO FUTURE SET")

    async def authenticate_password(self, account_name :str, enciphered_password : bytes, timestamp: int, auth_lost_handler:Callable) -> Optional[SteamPollingData]:
        loop = asyncio.get_running_loop()
        self._login_future = loop.create_future()
        os_value = get_os()

        await self._protobuf_client.log_on_password(account_name, enciphered_password, timestamp, os_value)
        (result, data) = await self._login_future
        self._login_future = None
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
        else: #ServiceUnavailable, RateLimitExceeded
            logger.warning(f"Received unknown error, code: {result}")
            raise translate_error(result)

        return data

    async def _login_handler(self, result: EResult, message : CAuthentication_BeginAuthSessionViaCredentials_Response):
        data : Optional[SteamPollingData] = None
        if (result == EResult.OK):
            auth_method : UserActionRequired = UserActionRequired.InvalidAuthData
            auth_message: str = ""
            if self._user_info_cache.steam_id != message.steamid:
                self._user_info_cache.steam_id = message.steamid;
            allowed : CAuthentication_AllowedConfirmation
            #loop through all the allowed confirmation methods. we will prioritize Codes over confirmation, and phone code over email code.
            # We arguably should let the user choose but this is already complicated enouh.
            #This SHOULD be a list of CAuthentication_AllowedConfirmation, but seems instead to be a list of EAuthTokenState. I DO NOT understand
            for allowed in message.allowed_confirmations:
                action, msg = to_UserActionWithMessage(allowed)
                if (action == UserActionRequired.PhoneTwoFactorInputRequired):
                    auth_method = action
                    auth_message = msg
                    break #this is the highest priority, so stop iterating immediately. 
                elif (action == UserActionRequired.EmailTwoFactorInputRequired):
                    auth_method = action
                    auth_message = msg
                    #since the highest priority stops the loop immediately, we will only ever get here if any previous iterations had a lower priority. 
                    #but, we may still have the phone 2FA after us, so do not break.
                elif (action == UserActionRequired.PhoneTwoFactorConfirmRequired and auth_method != UserActionRequired.EmailTwoFactorInputRequired):
                    auth_method = action
                    auth_message = msg
                    #mobile confirm is the hardest to implement here and requires the most waiting on the user's point of view, so we're deprioritizing it here.
                    #if either mobile or email codes is allowed, use them instead.
                elif (action == UserActionRequired.NoActionRequired and auth_method == UserActionRequired.InvalidAuthData):
                    auth_method = action
                    auth_message = msg
                    #in theory if this is set, none of the others should be, so this gets lowest priority. If somehow none and one of the other options is set, 
                    #steam messed up somehow, so err on the side of caution.
            res = message.DESCRIPTOR.fields_by_name.keys()
            logger.info("Entries in CredentialsResponse: " + pformat(res))
            #data = SteamPollingData(message.client_id, message.steamid, message.request_id, message.interval, auth_method, auth_message, message.extended_error_message)
            data = SteamPollingData(message.client_id, message.steamid, message.request_id, message.interval, auth_method, auth_message)
        else:
            logger.error("Login failed")
            #logger.error("Login failed. Reason: " + message.extended_error_message)

        if self._login_future is not None:
            self._login_future.set_result((result, data))
        else:
            # sometimes Steam sends LogOnResponse message even if plugin didn't send LogOnRequest
            # known example is LogOnResponse with result=EResult.TryAnotherCM

            #if i had to guess, some other random machine is trying to use the connection without going through a handshake. 
            #Steam detects it's not right, but for whatever reason we also get the response. -BaumherA
            raise translate_error(result)

    async def update_two_factor(self, code: str, method: str, auth_lost_handler:Callable):
        loop = asyncio.get_running_loop()
        self._two_factor_future = loop.create_future()
        await self._protobuf_client.update_steamguard_data(code, method)
        (result, key) = await self._two_factor_future
        logger.info ("GOT RSA KEY IN PROTOCOL_CLIENT")
        ret_code = UserActionRequired.InvalidAuthData
        if (result == EResult.OK or result == EResult.DuplicateRequest):
            ret_code = UserActionRequired.NoActionRequired
            self._auth_lost_handler = auth_lost_handler
        elif ()


    async def _two_factor_update_handler(self, result: EResult):
        if self._rsa_future is not None:
            self._rsa_future.set_result(result)
        else:
            logger.warning("NO FUTURE SET")
            


    async def check_auth_status(self, auth_lost_handler:Callable):
        loop = asyncio.get_running_loop()
        self._poll_future = loop.create_future()

        await self._protobuf_client.poll_auth_status()
        (result, data) = await self._poll_future
        self._poll_future = None #we may have to redo the poll so reset this value to null. 
        if result == EResult.OK:
            self._auth_lost_handler = auth_lost_handler

    async def _poll_handler(self, result: EResult, message : CAuthentication_PollAuthSessionStatus_Response):
        pass

    def _clear_poll_data(self):
        pass

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

    async def _license_import_handler(self, steam_licenses: List[SteamLicense]):
        logger.info('Handling %d user licenses', len(steam_licenses))
        not_resolved_licenses = []

        resolved_packages = self._games_cache.get_resolved_packages()
        package_ids = set([str(steam_license.license.package_id) for steam_license in steam_licenses])

        for steam_license in steam_licenses:
            if str(steam_license.license.package_id) not in resolved_packages:
                not_resolved_licenses.append(steam_license)

        if len(package_ids) < 12000:
            # TODO rework cache invalidation for bigger libraries (steam sends licenses in packs of >12k licenses)
            if package_ids != self._games_cache.get_package_ids():
                logger.info(
                    "Licenses list different than last time (cached packages: %d, new packages: %d). Reseting cache.",
                    len(self._games_cache.get_package_ids()),
                    len(package_ids)
                )
                self._games_cache.reset_storing_map()
                self._games_cache.start_packages_import(steam_licenses)
                return await self._protobuf_client.get_packages_info(steam_licenses)

        # This path will only attempt import on packages which aren't resolved (dont have any apps assigned)
        logger.info("Starting license import for %d packages, skipping %d already resolved.",
            len(package_ids - resolved_packages),
            len(resolved_packages)
        )
        self._games_cache.start_packages_import(not_resolved_licenses)
        await self._protobuf_client.get_packages_info(not_resolved_licenses)

    def _app_info_handler(self, appid, package_id=None, title=None, type=None, parent=None):
        if package_id:
            self._games_cache.update_license_apps(package_id, appid)
        if title and type:
            self._games_cache.update_app_title(appid, title, type, parent)

    def _package_info_handler(self):
        self._games_cache.update_packages()

    async def _app_ownership_ticket_handler(self, appid: int, ticket: bytes):
        if appid == STEAM_CLIENT_APP_ID:
            logger.info('Storing steam app ownership ticket')
            self._ownership_ticket_cache.ticket = ticket
        else:
            logger.debug(f'Ignoring app_id {appid} in ownership ticket handler')

    async def _translations_handler(self, appid, translations=None):
        if appid and translations:
            self._translations_cache[appid] = translations[0]
        elif appid not in self._translations_cache:
            self._translations_cache[appid] = None
            await self._protobuf_client.get_presence_localization(appid)

    def _stats_handler(self,
        game_id: str,
        stats: "steammessages_clientserver_pb2.CMsgClientGetUserStatsResponse.Stats",
        achievement_blocks: "steammessages_clientserver_pb2.CMsgClientGetUserStatsResponse.AchievementBlocks",
        schema: dict
    ):
        def get_achievement_name(achievements_block_schema: dict, bit_no: int) -> str:
            name = achievements_block_schema['bits'][str(bit_no)]['display']['name']
            try:
                return name['english']
            except TypeError:
                return name

        logger.debug(f"Processing user stats response for {game_id}")
        achievements_unlocked = []

        for achievement_block in achievement_blocks:
            block_id = str(achievement_block.achievement_id)
            try:
                stats_block_schema = schema[game_id]['stats'][block_id]
            except KeyError:
                logger.warning("No stat schema for block %s for game: %s", block_id, game_id)
                continue

            for i, unlock_time in enumerate(achievement_block.unlock_time):
                if unlock_time > 0:
                    try:
                        display_name = get_achievement_name(stats_block_schema, i)
                    except KeyError:
                        logger.warning("Unexpected schema for achievement bit %d from block %s for game %s: %s",
                            i, block_id, game_id, stats_block_schema
                        )
                        continue

                    achievements_unlocked.append({
                        'id': 32 * (achievement_block.achievement_id - 1) + i,
                        'unlock_time': unlock_time,
                        'name': display_name
                    })

        self._stats_cache.update_stats(game_id, stats, achievements_unlocked)

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
