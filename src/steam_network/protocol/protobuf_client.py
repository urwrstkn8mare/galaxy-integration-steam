import asyncio
import gzip
import json
import logging
import socket as sock
import struct
import ipaddress
from itertools import count
from typing import Awaitable, Callable, Coroutine, Dict, Optional, Any, List, NamedTuple, Iterator

import base64

import vdf

from websockets.client import WebSocketClientProtocol
from betterproto import Message

from steam_network.protocol.protobuf_socket_handler import ProtocolParser

from .consts import EMsg, EResult, EAccountType, EFriendRelationship, EPersonaState
from .messages.steammessages_base import (
    CMsgMulti,
    CMsgProtoBufHeader,
)
from .messages.steammessages_clientserver_login import (
    CMsgClientAccountInfo,
    CMsgClientHeartBeat,
    CMsgClientHello,
    CMsgClientLoggedOff,
    CMsgClientLogOff,
    CMsgClientLogon,
    CMsgClientLogonResponse,
)
from .messages.steammessages_auth import (
    CAuthentication_BeginAuthSessionViaCredentials_Request,
    CAuthentication_BeginAuthSessionViaCredentials_Response,
    CAuthentication_GetPasswordRSAPublicKey_Request,
    CAuthentication_GetPasswordRSAPublicKey_Response,
    CAuthentication_PollAuthSessionStatus_Request,
    CAuthentication_PollAuthSessionStatus_Response,
    CAuthentication_UpdateAuthSessionWithSteamGuardCode_Request,
    CAuthentication_UpdateAuthSessionWithSteamGuardCode_Response,
    EAuthSessionGuardType,
    EAuthTokenPlatformType,
    ESessionPersistence,
)
from .messages.steammessages_player import (
    CPlayer_GetLastPlayedTimes_Request,
    CPlayer_GetLastPlayedTimes_Response,
)
from .messages.steammessages_clientserver_friends import (
    CMsgClientChangeStatus,
    CMsgClientFriendsList,
    CMsgClientPersonaState,
    CMsgClientPlayerNicknameList,
    CMsgClientRequestFriendData,
)
from .messages.steammessages_clientserver import (
    CMsgClientLicenseList,
    CMsgClientLicenseListLicense
)
from .messages.steammessages_chat import (
    CChat_RequestFriendPersonaStates_Request,
)
from .messages.steammessages_clientserver_2 import (
    CMsgClientUpdateMachineAuthResponse,
)
from .messages.steammessages_clientserver_userstats import (
    CMsgClientGetUserStats,
    CMsgClientGetUserStatsResponse,
)
from .messages.steammessages_clientserver_appinfo import (
    CMsgClientPICSProductInfoRequest,
    CMsgClientPICSProductInfoRequestPackageInfo,
    CMsgClientPICSProductInfoResponse,
    CMsgClientPICSProductInfoResponsePackageInfo,
    CMsgClientPICSProductInfoResponseAppInfo,
)
from .messages.service_cloudconfigstore import (
    CCloudConfigStore_Download_Request,
    CCloudConfigStore_Download_Response,
    CCloudConfigStore_NamespaceVersion,
)
from .messages.steammessages_webui_friends import (
    CCommunity_GetAppRichPresenceLocalization_Request,
    CCommunity_GetAppRichPresenceLocalization_Response,
)

from .steam_types import SteamId, ProtoUserInfo
from .task_parallelizer import parallel_map_async

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
LOG_SENSITIVE_DATA = False

GET_APP_RICH_PRESENCE = "Community.GetAppRichPresenceLocalization#1"
GET_LAST_PLAYED_TIMES = 'Player.ClientGetLastPlayedTimes#1'
CLOUD_CONFIG_DOWNLOAD = 'CloudConfigStore.Download#1'
REQUEST_FRIEND_PERSONA_STATES = "Chat.RequestFriendPersonaStates#1"
GET_RSA_KEY = "Authentication.GetPasswordRSAPublicKey#1"
LOGIN_CREDENTIALS = "Authentication.BeginAuthSessionViaCredentials#1"
UPDATE_TWO_FACTOR = "Authentication.UpdateAuthSessionWithSteamGuardCode#1"
CHECK_AUTHENTICATION_STATUS = "Authentication.PollAuthSessionStatus#1"

class SteamLicense(NamedTuple):
    license_data: CMsgClientLicenseListLicense  # type: ignore[name-defined]
    shared: bool


class ProtobufClient:
    _PROTO_MASK = 0x80000000
    _ACCOUNT_ID_MASK = 0x0110000100000000
    _IP_OBFUSCATION_MASK = 0x606573A4
    _MSG_PROTOCOL_VERSION = 65580
    _MSG_CLIENT_PACKAGE_VERSION = 1561159470

    def __init__(self, set_socket : WebSocketClientProtocol):
        self._socket :                      WebSocketClientProtocol = set_socket
        #new auth flow
        self.rsa_handler:                   Optional[Callable[[EResult, int, int, int], Awaitable[None]]] = None
        self.login_handler:                 Optional[Callable[[EResult,CAuthentication_BeginAuthSessionViaCredentials_Response], Awaitable[None]]] = None
        self.two_factor_update_handler:     Optional[Callable[[EResult, str], Awaitable[None]]] = None
        self.poll_status_handler:           Optional[Callable[[EResult, CAuthentication_PollAuthSessionStatus_Response], Awaitable[None]]] = None
        #old auth flow. Used to confirm login and repeat logins using the refresh token.
        self.log_on_token_handler:          Optional[Callable[[EResult, Optional[int], Optional[int]], Awaitable[None]]] = None
        self._heartbeat_task:               Optional[asyncio.Task] = None #keeps our connection alive, essentially, by pinging the steam server.
        self.log_off_handler:               Optional[Callable[[EResult], Awaitable[None]]] = None
        #retrieve information
        self.relationship_handler:          Optional[Callable[[bool, Dict[int, EFriendRelationship]], Awaitable[None]]] = None
        self.user_info_handler:             Optional[Callable[[int, ProtoUserInfo], Awaitable[None]]] = None
        self.user_nicknames_handler:        Optional[Callable[[dict], Awaitable[None]]] = None
        self.license_import_handler:        Optional[Callable[[int], Awaitable[None]]] = None
        self.app_info_handler:              Optional[Callable[[str, str, str, str, str], None]] = None
        self.package_info_handler:          Optional[Callable[[], None]] = None
        self.translations_handler:          Optional[Callable[[float, Any], Awaitable[None]]] = None
        self.stats_handler:                 Optional[Callable[[int, Any, Any], Awaitable[None]]] = None
        self.confirmed_steam_id:            Optional[int] = None #this should only be set when the steam id is confirmed. this occurs when we actually complete the login. before then, it will cause errors.
        self.times_handler:                 Optional[Callable[[int, int, int], Awaitable[None]]] = None
        self.times_import_finished_handler: Optional[Callable[[bool], Awaitable[None]]] = None
        self._session_id:                   Optional[int] = None
        self._job_id_iterator:              Iterator[int] = count(1) #this is actually clever. A lazy iterator that increments every time you call next.
        self.job_list : List[Dict[str,str]] = []

        self.collections = {'event': asyncio.Event(),
                            'collections': dict()}
        self._recv_task:                    Optional[Coroutine[Any, Any, Any]] = None
    async def close(self, send_log_off):
        if (self._recv_task is not None):
            self._recv_task.cancel()
        if send_log_off:
            await self.send_log_off_message()
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()

    async def wait_closed(self):
        pass

    async def run(self):
        jobs_to_process = 0
        while True:
            if jobs_to_process < 2:
                for job in self.job_list[:1].copy():
                    logger.info(f"New job on list {job}")
                    jobs_to_process += 1
                    if job['job_name'] == "import_game_stats":
                        await self._import_game_stats(job['game_id'])
                        self.job_list.remove(job)
                    elif job['job_name'] == "import_collections":
                        await self._import_collections()
                        self.job_list.remove(job)
                    elif job['job_name'] == "import_game_times":
                        await self._import_game_time()
                        self.job_list.remove(job)
                    else:
                        self.job_list.remove(job)
                        logger.warning(f'Unknown job {job}')
            try:
                self._recv_task = asyncio.create_task(self._socket.recv())
                packet = await asyncio.wait_for(self._recv_task, 10)
                self._recv_task = None
                await self._process_packet(packet)
                if jobs_to_process > 0:
                    jobs_to_process -= 1
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError: #occurs when we cancel the recv. only should occur if the socket is closing anyway.
                break
            finally:
                self._recv_task = None

    async def _send_service_method_with_name(self, message, target_job_name: str):
        emsg = EMsg.ServiceMethodCallFromClientNonAuthed if self.confirmed_steam_id is None else EMsg.ServiceMethodCallFromClient;
        job_id = next(self._job_id_iterator)
        await self._send(emsg, message, source_job_id=job_id, target_job_name= target_job_name)

    #new workflow:  say hello -> get rsa public key -> log on with password -> handle steam guard -> confirm login
    #each is getting a dedicated function so i don't go insane.
    #confirm login is the old log_on_token call.

    async def say_hello(self):
        """Say Hello to the server. Necessary before sending non-authed calls.

            If we don't do this, they will just shut down the websocket connection gracefully with "OK", which is most definitely not "OK"
        """
        message = CMsgClientHello()
        message.protocol_version = self._MSG_PROTOCOL_VERSION
        await self._send(EMsg.ClientHello,message)

    #send the get rsa key request
    #imho we should just do a send and receive back to back instead of this bouncing around, but whatever.
    async def get_rsa_public_key(self, account_name: str):
        message = CAuthentication_GetPasswordRSAPublicKey_Request()
        message.account_name = account_name
        await self._send_service_method_with_name(message, GET_RSA_KEY) #parsed from SteamKit's gobbledygook

    #process the received the rsa key response. Because we will need all the information about this process, we send the entire message up the chain.
    async def _process_rsa(self, result : EResult, body : bytes):
        message = CAuthentication_GetPasswordRSAPublicKey_Response().parse(body)
        logger.info("Received RSA KEY")
        #logger.info(pformat(message))
        if (self.rsa_handler is not None):
            await self.rsa_handler(result, int(message.publickey_mod, 16), int(message.publickey_exp, 16), message.timestamp)
        else:
            logger.warning("NO RSA HANDLER SET!")

    async def log_on_password(self, account_name:str, enciphered_password: bytes, timestamp: int, os_value: int):
        friendly_name: str = sock.gethostname() + " (GOG Galaxy)"

        #device details is readonly. So we can't do this the easy way.
        #device_details = CAuthentication_DeviceDetails()
        #device_details.device_friendly_name =
        #device_details.os_type = os_value if os_value >= 0 else 0
        #device_details.platform_type= EAuthTokenPlatformType.k_EAuthTokenPlatformType_SteamClient

        message = CAuthentication_BeginAuthSessionViaCredentials_Request()

        message.account_name = account_name
        #protobuf definition uses string, so we need this to be a string. but we can't parse the regular text as 
        #a string because it's enciphered and contains illegal characters. b64 fixes this. 
        #Then we make it a utf-8 string, and better proto then makes it bytes again when it's packed alongside all other message fields and sent along the websocket. 
        #inelegant but the price you pay for proper type checking. 
        message.encrypted_password = str(base64.b64encode(enciphered_password), "utf-8")
        message.website_id = "Client"
        message.device_friendly_name = friendly_name
        message.encryption_timestamp = timestamp
        message.platform_type = EAuthTokenPlatformType.k_EAuthTokenPlatformType_SteamClient #no idea if this line will work.
        message.persistence = ESessionPersistence.k_ESessionPersistence_Persistent

        #message.device_details = device_details
        #so let's do it the hard way.
        message.device_details.device_friendly_name = friendly_name
        message.device_details.os_type = os_value if os_value >= 0 else 0
        message.device_details.platform_type= EAuthTokenPlatformType.k_EAuthTokenPlatformType_SteamClient
        #message.guard_data = ""
        logger.info("Sending log on message using credentials in new authorization workflow")

        await self._send_service_method_with_name(message, LOGIN_CREDENTIALS)

    async def _process_login(self, result, body):
        message = CAuthentication_BeginAuthSessionViaCredentials_Response().parse(body)
        logger.info("Processing Login Response!")
        
        ##TODO: IF WE GET ERRORS UNSET THIS.
        #if (self.steam_id is None and message.steamid is not None):
        #    self.steam_id = message.steamidd
        if (self.login_handler is not None):
            await self.login_handler(result, message)
        else:
            logger.warning("NO LOGIN HANDLER SET!")

    async def update_steamguard_data(self, client_id: int, steam_id:int, code:str, code_type:EAuthSessionGuardType):
        message = CAuthentication_UpdateAuthSessionWithSteamGuardCode_Request()

        message.client_id = client_id
        message.steamid= steam_id
        message.code = code
        message.code_type = code_type

        await self._send_service_method_with_name(message, UPDATE_TWO_FACTOR)

    async def _process_steamguard_update(self, result, body):
        message = CAuthentication_UpdateAuthSessionWithSteamGuardCode_Response().parse(body)
        logger.info("Processing Two Factor Response!")
        #this gives us a confirm url, but as of this writing we can ignore it. so, just the result is necessary.

        if (self.two_factor_update_handler is not None):
            await self.two_factor_update_handler(result, message.agreement_session_url)
        else:
            logger.warning("NO TWO-FACTOR HANDLER SET!")

    async def poll_auth_status(self, client_id:int, request_id:bytes):
        message = CAuthentication_PollAuthSessionStatus_Request()
        message.client_id = client_id
        message.request_id = request_id

        await self._send_service_method_with_name(message, CHECK_AUTHENTICATION_STATUS)

    async def _process_auth_poll_status(self, result, body):
        message = CAuthentication_PollAuthSessionStatus_Response().parse(body)

        if (self.poll_status_handler is not None):
            await self.poll_status_handler(result, message)
        else:
            logger.warning("NO POLL STATUS HANDLER SET!")

    #old auth flow. Still necessary for remaining logged in and confirming after doing the new auth flow. 
    async def _get_obfuscated_private_ip(self) -> int:
        logger.info('Websocket state is: %s' % self._socket.state.name)
        await self._socket.ensure_open()
        host, port = self._socket.local_address
        ip = int(ipaddress.IPv4Address(host))
        obfuscated_ip = ip ^ self._IP_OBFUSCATION_MASK
        logger.debug(f"Local obfuscated IP: {obfuscated_ip}")
        return obfuscated_ip

    #async def send_log_on_token_message(self, account_name: str, access_token: str, cell_id: int, machine_id: bytes, os_value: int):
    async def send_log_on_token_message(self, account_name: str, steam_id:int, access_token: str, cell_id: int, machine_id: bytes, os_value: int):
        #AccountInstance = SteamID.DesktopInstance; // use the default pc steam instance
        #AccountID = 0;
        #ClientOSType = Utils.GetOSType();
        #ClientLanguage = "english";
        #Username = pollResponse.AccountName,
        #AccessToken = pollResponse.RefreshToken,
        #ShouldSavePassword = True #err on side of caution in case this not being set causes them to ignore access token. then try false. 
        resetSteamIDAfterThisCall : bool = False
        if (self.confirmed_steam_id is None):
            resetSteamIDAfterThisCall = True
            self.confirmed_steam_id = steam_id

        message = CMsgClientLogon()
        message.client_supplied_steam_id = steam_id
        message.protocol_version = self._MSG_PROTOCOL_VERSION
        message.client_package_version = self._MSG_CLIENT_PACKAGE_VERSION
        message.cell_id = cell_id
        message.client_language = "english"
        message.client_os_type = os_value if os_value >= 0 else 0
        message.obfuscated_private_ip.v4 = await self._get_obfuscated_private_ip()
        message.qos_level = 3
        message.machine_id = machine_id
        message.account_name = account_name
        #message.password = ""
        message.should_remember_password = True
        message.eresult_sentryfile = EResult.FileNotFound
        message.machine_name = sock.gethostname()
        message.access_token = access_token
        logger.info("Sending log on message using access token")
        awaitMe = self._send(EMsg.ClientLogon, message)
        if (resetSteamIDAfterThisCall):
            self.confirmed_steam_id = None
        await awaitMe


    async def _heartbeat(self, interval):
        message = CMsgClientHeartBeat()
        while True:
            await asyncio.sleep(interval)
            await self._send(EMsg.ClientHeartBeat, message)

    async def _process_client_log_on_response(self, body):
        logger.debug("Processing message ClientLogOnResponse")
        message = CMsgClientLogonResponse().parse(body)
        result = message.eresult
        interval = message.heartbeat_seconds
        if result == EResult.OK:
            self.confirmed_steam_id = message.client_supplied_steamid
            self._heartbeat_task = asyncio.create_task(self._heartbeat(interval))
        else:
            logger.info(f"Failed to log on, reason : {message}")
            logger.info(f"Extended info : {message.eresult_extended}")

        if self.log_on_token_handler is not None:
            account_id = message.client_supplied_steamid - self._ACCOUNT_ID_MASK if message.client_supplied_steamid else None
            await self.log_on_token_handler(result, message.client_supplied_steamid, account_id)
        else:
            logger.warning("NO LOGIN TOKEN HANDLER SET!")

    async def send_log_off_message(self):
        message = CMsgClientLogOff()
        logger.info("Sending log off message")
        try:
            await self._send(EMsg.ClientLogOff, message)
        except Exception as e:
            logger.error(f"Unable to send logoff message {repr(e)}")

    #retrieve info

    async def _import_game_stats(self, game_id):
        logger.info(f"Importing game stats for {game_id}")
        message = CMsgClientGetUserStats()
        message.game_id = int(game_id)
        await self._send(EMsg.ClientGetUserStats, message)

    async def _import_game_time(self):
        logger.info("Importing game times")
        job_id = next(self._job_id_iterator)
        message = CPlayer_GetLastPlayedTimes_Request()
        message.min_last_played = 0
        await self._send(EMsg.ServiceMethodCallFromClient, message, job_id, None, GET_LAST_PLAYED_TIMES)

    async def set_persona_state(self, state):
        message = CMsgClientChangeStatus()
        message.persona_state = state
        await self._send(EMsg.ClientChangeStatus, message)

    async def get_friends_statuses(self):
        job_id = next(self._job_id_iterator)
        message = CChat_RequestFriendPersonaStates_Request()
        await self._send(EMsg.ServiceMethodCallFromClient, message, job_id, None, REQUEST_FRIEND_PERSONA_STATES)

    async def get_user_infos(self, users, flags):
        message = CMsgClientRequestFriendData()
        message.friends.extend(users)
        message.persona_state_requested = flags
        await self._send(EMsg.ClientRequestFriendData, message)

    async def _import_collections(self):
        job_id = next(self._job_id_iterator)
        message = CCloudConfigStore_Download_Request()
        message_inside = CCloudConfigStore_NamespaceVersion()
        message_inside.enamespace = 1
        message.versions.append(message_inside)
        await self._send(EMsg.ServiceMethodCallFromClient, message, job_id, None, CLOUD_CONFIG_DOWNLOAD)

    async def get_packages_info(self, steam_licenses: List[SteamLicense]):
        logger.info("Sending call %s with %d package_ids", repr(EMsg.ClientPICSProductInfoRequest), len(steam_licenses))
        message = CMsgClientPICSProductInfoRequest()
        message.packages = list()

        for steam_license in steam_licenses:
            info = CMsgClientPICSProductInfoRequestPackageInfo()
            info.packageid = steam_license.license_data.package_id
            info.access_token = steam_license.license_data.access_token
            message.packages.append(info)

        await self._send(EMsg.ClientPICSProductInfoRequest, message)

    async def get_apps_info(self, app_ids : List[int]):
        logger.info("Sending call %s with %d app_ids", repr(EMsg.ClientPICSProductInfoRequest), len(app_ids))
        message = CMsgClientPICSProductInfoRequest()

        for app_id in app_ids:
            message.apps.append(app_id)

        await self._send(EMsg.ClientPICSProductInfoRequest, message)

    async def get_presence_localization(self, appid: int , language: str = 'english'):
        logger.info(f"Sending call for rich presence localization with {appid}, {language}")
        message = CCommunity_GetAppRichPresenceLocalization_Request()

        message.appid = appid
        message.language = language

        job_id = next(self._job_id_iterator)
        await self._send(EMsg.ServiceMethodCallFromClient, message, job_id, None,
                         target_job_name= GET_APP_RICH_PRESENCE)

    async def _send(self, emsg : EMsg, message: Message, source_job_id: Optional[int] = None,
                    target_job_id: Optional[int] = None, target_job_name: Optional[str] = None):
        proto_header = CMsgProtoBufHeader()

        if self.confirmed_steam_id is not None:
            proto_header.steamid = self.confirmed_steam_id
        else:
            proto_header.steamid = 0 + self._ACCOUNT_ID_MASK
        if self._session_id is not None:
            proto_header.client_sessionid = self._session_id
        if source_job_id is not None:
            proto_header.jobid_source = source_job_id
        if target_job_id is not None:
            proto_header.jobid_target = target_job_id
        if target_job_name is not None:
            proto_header.target_job_name = target_job_name

        header = bytes(proto_header)
        body = bytes(message)

        #Magic string decoded: < = little endian. 2I = 2 x unsigned integer. 
        #emsg | proto_mash is the first UInt, length of header is the second UInt.
        data = struct.pack("<2I", emsg | self._PROTO_MASK, len(header))
        data = data + header + body

        if LOG_SENSITIVE_DATA:
            logger.info("[Out] %s (%dB), params:\n", repr(emsg), len(data), repr(message))
        else:
            logger.info("[Out] %s (%dB)", repr(emsg), len(data))
        await self._socket.send(data)

    async def _process_packet(self, packet: bytes):
        package_size = len(packet)
        #packets reserve the first 8 bytes for the Message code (emsg) and 
        logger.debug("Processing packet of %d bytes", package_size)

        if package_size < 8:
            logger.warning("Package too small, ignoring...")
            return

        raw_emsg = int.from_bytes(packet[:4], "little")
        emsg: int = raw_emsg & ~self._PROTO_MASK 

        if raw_emsg & self._PROTO_MASK != 0:
            header_len = int.from_bytes(packet[4:8], "little")
            header = CMsgProtoBufHeader().parse(packet[8:8 + header_len])

            if header.client_sessionid != 0:
                if self._session_id is None:
                    logger.info("New session id: %d", header.client_sessionid)
                    self._session_id = header.client_sessionid
                if self._session_id != header.client_sessionid:
                    logger.warning('Received session_id %s while client one is %s', header.client_sessionid, self._session_id)

            await self._process_message(emsg, header, packet[8 + header_len:])
        else:
            logger.warning("Packet for %d -> EMsg.%s with extended header - ignoring", emsg, EMsg(emsg).name)

    async def _process_message(self, emsg: int, header: CMsgProtoBufHeader, body: bytes):
        logger.info("[In] %d -> EMsg.%s", emsg, EMsg(emsg).name)
        if emsg == EMsg.Multi:
            await self._process_multi(body)
        elif emsg == EMsg.ClientLogOnResponse:
            await self._process_client_log_on_response(body)
        elif emsg == EMsg.ClientLoggedOff:
            await self._process_client_logged_off(body)
        elif emsg == EMsg.ClientFriendsList:
            await self._process_client_friend_list(body)
        elif emsg == EMsg.ClientPersonaState:
            await self._process_client_persona_state(body)
        elif emsg == EMsg.ClientLicenseList:
            await self._process_license_list(body)
        elif emsg == EMsg.ClientPICSProductInfoResponse:
            await self._process_product_info_response(body)
        elif emsg == EMsg.ClientGetUserStatsResponse:
            await self._process_user_stats_response(body)
        elif emsg == EMsg.ClientAccountInfo:
            await self._process_account_info(body)
        elif emsg == EMsg.ClientPlayerNicknameList:
            await self._process_user_nicknames(body)
        elif emsg == EMsg.ServiceMethod:
            await self._process_service_method_response(header.target_job_name, int(header.jobid_target), header.eresult, body)
        elif emsg == EMsg.ServiceMethodResponse:
            await self._process_service_method_response(header.target_job_name, int(header.jobid_target), header.eresult, body)
        else:
            logger.warning("Ignored message %d", emsg)

    async def _process_multi(self, body: bytes):
        logger.debug("Processing message Multi")
        message = CMsgMulti().parse(body)
        if message.size_unzipped > 0:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, gzip.decompress, message.message_body)
        else:
            data = message.message_body

        data_size = len(data)
        offset = 0
        size_bytes = 4
        while offset + size_bytes <= data_size:
            size = int.from_bytes(data[offset:offset + size_bytes], "little")
            await self._process_packet(data[offset + size_bytes:offset + size_bytes + size])
            offset += size_bytes + size
        logger.debug("Finished processing message Multi")

    async def _process_account_info(self, body: bytes):
        logger.debug("Processing message ClientAccountInfo")
        #message = CMsgClientAccountInfo().parse(body)
        logger.info("Client Account Info Message currently unused. It it redundant")

    async def _process_client_logged_off(self, body: bytes):
        logger.debug("Processing message ClientLoggedOff")
        message = CMsgClientLoggedOff().parse(body)
        result = message.eresult

        assert self._heartbeat_task is not None
        self._heartbeat_task.cancel()

        if self.log_off_handler is not None:
            await self.log_off_handler(result)

    async def _process_user_nicknames(self, body: bytes):
        logger.debug("Processing message ClientPlayerNicknameList")
        message = CMsgClientPlayerNicknameList().parse(body)
        nicknames = {}
        for player_nickname in message.nicknames:
            nicknames[str(player_nickname.steamid)] = player_nickname.nickname

        await self.user_nicknames_handler(nicknames)

    async def _process_client_friend_list(self, body: bytes):
        logger.debug("Processing message ClientFriendsList")
        if self.relationship_handler is None:
            return

        message = CMsgClientFriendsList().parse(body)

        friends = {}
        for relationship in message.friends:
            steam_id = relationship.ulfriendid
            details = SteamId.parse(steam_id)
            if details.type_ == EAccountType.Individual:
                friends[steam_id] = EFriendRelationship(relationship.efriendrelationship)

        await self.relationship_handler(message.bincremental, friends)

    async def _process_client_persona_state(self, body: bytes):
        logger.debug("Processing message ClientPersonaState")
        if self.user_info_handler is None:
            return

        message = CMsgClientPersonaState().parse(body)

        for user in message.friends:
            user_id = user.friendid
            if user_id == self.confirmed_steam_id and user.game_played_app_id != 0:
                await self.get_apps_info([user.game_played_app_id])

            user_info = ProtoUserInfo(
                name=user.player_name,
                avatar_hash=user.avatar_hash,
                state=EPersonaState(user.persona_state),
                game_id=user.gameid
            )

            rich_presence: Dict[str, str] = {}
            for element in user.rich_presence:
                rich_presence[element.key] = element.value
                if element.key == 'status' and element.value:
                    if "#" in element.value:
                        await self.translations_handler(user.gameid)
                if element.key == 'steam_display' and element.value:
                    if "#" in element.value:
                        await self.translations_handler(user.gameid)

            user_info.rich_presence = rich_presence
            user_info.game_name = user.game_name

            await self.user_info_handler(user_id, user_info)

    @staticmethod
    def _parallel_process_license(license_: CMsgClientLicenseListLicense, owner_id: int) -> Optional[SteamLicense]:
        # license_.type 1024 = free games
        # license_.flags 520 = unidentified trash entries (games which are not owned nor are free)
        if license_.flags == 520:
            return None

        if license_.package_id == 0:
            # Packageid 0 contains trash entries for every user
            #logger.debug("Skipping packageid 0 ")
            return None

        if license_.owner_id == owner_id:
            return SteamLicense(license_data=license_, shared=False)
        else:
            return SteamLicense(license_data=license_, shared=True)

    async def _process_license_list(self, body: bytes):
        logger.debug("Processing message ClientLicenseList")
        if self.license_import_handler is None:
            return

        message : CMsgClientLicenseList = CMsgClientLicenseList().parse(body)
        message_license_list = message.licenses

        owner_id: int =  int(self.confirmed_steam_id - self._ACCOUNT_ID_MASK)
        licenses_to_check : List[SteamLicense] = await parallel_map_async(message_license_list, lambda x : ProtocolParser._parallel_process_license(message_license_list, owner_id))
        
        await self.license_import_handler(licenses_to_check)

    async def _process_product_info_response(self, body : bytes):
        logger.debug("Processing message ClientPICSProductInfoResponse")
        message = CMsgClientPICSProductInfoResponse().parse(body)
        apps_to_parse: List[str] = []

        def product_info_handler(packages: List[CMsgClientPICSProductInfoResponsePackageInfo], apps: List[CMsgClientPICSProductInfoResponseAppInfo]):
            for info in packages:
                self.package_info_handler()

                package_id = str(info.packageid)
                package_content = vdf.binary_loads(info.buffer[4:])
                package = package_content.get(package_id)
                if package is None:
                    continue

                for app in package['appids'].values():
                    appid = str(app)
                    self.app_info_handler(package_id=package_id, appid=appid)
                    apps_to_parse.append(app)

            for info in apps:
                app_content : dict = vdf.loads(info.buffer[:-1].decode('utf-8', 'replace'))
                appid = str(app_content['appinfo']['appid'])
                try:
                    type_ : str = app_content['appinfo']['common']['type'].lower()
                    title : str = app_content['appinfo']['common']['name']
                    parent : Optional[str] = None
                    if 'extended' in app_content['appinfo'] and type_ == 'dlc':
                        parent = app_content['appinfo']['extended']['dlcforappid']
                        logger.debug(f"Retrieved dlc {title} for {parent}")
                    if type_ == 'game':
                        logger.debug(f"Retrieved game {title}")
                    self.app_info_handler(appid=appid, title=title, type_=type_, parent=parent)
                except KeyError:
                    logger.warning(f"Unrecognized app structure {app_content}")
                    self.app_info_handler(appid=appid, title='unknown', type_='unknown', parent=None)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, product_info_handler, message.packages, message.apps)

        if len(apps_to_parse) > 0:
            logger.debug("Apps to parse: %s", str(apps_to_parse))
            await self.get_apps_info(apps_to_parse)

    async def _process_rich_presence_translations(self, body: bytes):
        message = CCommunity_GetAppRichPresenceLocalization_Response().parse(body)

        # keeping info log for further rich presence improvements
        logger.info(f"Received information about rich presence translations for {message.appid}")
        await self.translations_handler(message.appid, message.token_lists)

    async def _process_user_stats_response(self, body: bytes):
        logger.debug("Processing message ClientGetUserStatsResponse")
        message : CMsgClientGetUserStatsResponse = CMsgClientGetUserStatsResponse().parse(body)

        game_id = str(message.game_id)
        stats = message.stats
        achievement_blocks = message.achievement_blocks
        achievements_schema = vdf.binary_loads(message.schema, merge_duplicate_keys=False)

        self.stats_handler(game_id, stats, achievement_blocks, achievements_schema)

    async def _process_user_time_response(self, body: bytes):
        message = CPlayer_GetLastPlayedTimes_Response().parse(body)
        for game in message.games:
            logger.debug(f"Processing game times for game {game.appid}, playtime: {game.playtime_forever} last time played: {game.last_playtime}")
            await self.times_handler(game.appid, game.playtime_forever, game.last_playtime)
        await self.times_import_finished_handler(True)

    async def _process_collections_response(self, body: bytes):
        message = CCloudConfigStore_Download_Response().parse(body)

        for data in message.data:
            for entry in data.entries:
                try:
                    loaded_val = json.loads(entry.value)
                    self.collections['collections'][loaded_val['name']] = loaded_val['added']
                except:
                    pass
        self.collections['event'].set()

    async def _process_service_method_response(self, target_job_name: str, target_job_id: int, eresult: EResult, body: bytes):
        logger.info("Processing message ServiceMethodResponse %s", target_job_name)
        if target_job_name == GET_APP_RICH_PRESENCE:
            await self._process_rich_presence_translations(body)
        elif target_job_name == GET_LAST_PLAYED_TIMES:
            await self._process_user_time_response(body)
        elif target_job_name == CLOUD_CONFIG_DOWNLOAD:
            await self._process_collections_response(body)
        #elif target_job_name == REQUEST_FRIEND_PERSONA_STATES:
            #pass #no idea what to do here. for now, having it error will let me know when it's called so i can see wtf to do with it.
        elif target_job_name == GET_RSA_KEY:
            await self._process_rsa(eresult, body)
        elif target_job_name == LOGIN_CREDENTIALS:
            await self._process_login(eresult, body)
        elif target_job_name == UPDATE_TWO_FACTOR:
            await self._process_steamguard_update(eresult, body)
        elif target_job_name == CHECK_AUTHENTICATION_STATUS:
            await self._process_auth_poll_status(eresult, body)
        else:
            logger.warning("Unparsed message, no idea what it is. Tell me")
            logger.warning("job name: \"" + target_job_name + "\"")
