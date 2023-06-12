from asyncio import Future
from typing import Dict, NamedTuple, Tuple, Optional, List, Iterator, Callable, TypeVar, Generic
from betterproto import Message
from itertools import count
import logging
import asyncio
from asyncio import Future
from gzip import decompress
import struct
from base64 import b64encode
import socket as sock

from steam_network.protocol.messages.steammessages_clientserver_userstats import CMsgClientGetUserStatsResponse

from steam_network.websocket_client import WebSocketClient

from .consts import EMsg, EResult, EAccountType, EFriendRelationship, EPersonaState

from .messages.steammessages_base import (
    CMsgMulti,
    CMsgProtoBufHeader,
)

from .messages.service_cloudconfigstore import (
    CCloudConfigStore_Download_Request,
    CCloudConfigStore_Download_Response,
    CCloudConfigStore_NamespaceVersion,
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
    CAuthentication_RefreshToken_Revoke_Request,
    CAuthentication_RefreshToken_Revoke_Response,
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

from .messages.steammessages_player import (
    CPlayer_GetLastPlayedTimes_Request,
    CPlayer_GetLastPlayedTimes_Response,
)
from .messages.steammessages_chat import (
    CChat_RequestFriendPersonaStates_Request,
)
from .messages.steammessages_clientserver import (
    CMsgClientLicenseList,
    CMsgClientLicenseListLicense
)
from .messages.steammessages_clientserver_2 import (
    CMsgClientUpdateMachineAuthResponse,
)
from .messages.steammessages_clientserver_appinfo import (
    CMsgClientPICSProductInfoRequest,
    CMsgClientPICSProductInfoRequestPackageInfo,
    CMsgClientPICSProductInfoResponse,
    CMsgClientPICSProductInfoResponsePackageInfo,
    CMsgClientPICSProductInfoResponseAppInfo,
)
from .messages.steammessages_clientserver_friends import (
    CMsgClientChangeStatus,
    CMsgClientFriendsList,
    CMsgClientPersonaState,
    CMsgClientPlayerNicknameList,
    CMsgClientRequestFriendData,
)
from .messages.steammessages_clientserver_userstats import (
    CMsgClientGetUserStats,
    CMsgClientGetUserStatsResponse,
)
from .messages.steammessages_webui_friends import (
    CCommunity_GetAppRichPresenceLocalization_Request,
    CCommunity_GetAppRichPresenceLocalization_Response,
)

from .steam_types import SteamId, ProtoUserInfo
from .consts import EMsg, EResult


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

class FutureInfo(NamedTuple):
    future: Future
    sent_type: EMsg
    expected_return_type: Optional[EMsg] #some messages are one-way, so these should not return anything. 
    sent_recv_name: Optional[str]

    def is_expected_response(self, return_type:EMsg, target_name: Optional[str]) -> bool:
        retVal, _ = self.is_expected_response_with_message(return_type, target_name)
        return retVal

    def is_expected_response_with_message(self, return_type:EMsg, target_name: Optional[str]) -> Tuple(bool, str):
        expected_return_type_str = self.expected_return_type.name if self.expected_return_type is not None else "<no response>"

        if return_type == EMsg.ServiceMethod:
            return_type = EMsg.ServiceMethodResponse

        if (self.expected_return_type != return_type):
            return (False, f"Message has return type {return_type.name}, but we were expecting {expected_return_type_str}. Treating as an unsolicited message")

        elif (return_type == EMsg.ServiceMethodResponse and target_name is None or target_name != self.send_recv_name):
            return (False, f"Received a service message, but not of the expected name. Got {target_name}, but we were expecting {self.sent_recv_name}. Treating as an unsolicited message")

        return (True, "")

T = TypeVar("T", bound = Message)
class ProtoResult(Generic[T]):
    def __init__(self, emsg: EMsg, error_message: str, body: Optional[T]) -> None:
        self._emsg : EMsg = emsg
        self._error_message = error_message
        self._body: Optional[T] = body
    
    @property
    def emsg(self):
        return self._emsg

    @property
    def error_message(self):
        return self._error_message

    @property
    def body(self):
        return self._body

class ProtocolParser:
    _PROTO_MASK = 0x80000000


    def __init__(self):
        self._future_lookup: Dict[int, FutureInfo] = {}
        self._job_id_iterator: Iterator[int] = count(1) #this is actually clever. A lazy iterator that increments every time you call next.
        self.confirmed_steam_id : Optional[int] = None
        pass

    #Standard Request/Response style messages. They aren't synchronous by nature of websocket communication, but we can write our code to closely mimic that behavior.

    #get the rsa public key for the provided user
    async def GetPasswordRSAPublicKey(self, socket: WebSocketClient, username: str) -> ProtoResult[CAuthentication_GetPasswordRSAPublicKey_Response]:
        msg = CAuthentication_GetPasswordRSAPublicKey_Request(username)
        header, resp_bytes = await self._send_recv_service_message(socket, msg, GET_RSA_KEY, next(self._job_id_iterator))

        if (header.eresult != EResult.OK):
            return None
        else:
            return CAuthentication_GetPasswordRSAPublicKey_Response().parse(resp_bytes)
    
    #start the login process with credentials
    async def BeginAuthSessionViaCredentials(self, socket: WebSocketClient, account_name:str, enciphered_password: bytes, timestamp: int, os_value: int, language: Optional[str] = None) -> ProtoResult[CAuthentication_BeginAuthSessionViaCredentials_Response]:
        friendly_name: str = sock.gethostname() + " (GOG Galaxy)"

        message = CAuthentication_BeginAuthSessionViaCredentials_Request()

        message.account_name = account_name
        #protobuf definition uses string, so we need this to be a string. but we can't parse the regular text as 
        #a string because it's enciphered and contains illegal characters. b64 fixes this. 
        #Then we make it a utf-8 string, and better proto then makes it bytes again when it's packed alongside all other message fields and sent along the websocket. 
        #inelegant but the price you pay for proper type checking. 
        message.encrypted_password = str(b64encode(enciphered_password), "utf-8")
        message.website_id = "Client"
        message.device_friendly_name = friendly_name
        message.encryption_timestamp = timestamp
        message.platform_type = EAuthTokenPlatformType.k_EAuthTokenPlatformType_SteamClient
        message.persistence = ESessionPersistence.k_ESessionPersistence_Persistent
        if (language is not None and language):
            message.language = language

        message.device_details.device_friendly_name = friendly_name
        message.device_details.os_type = os_value if os_value >= 0 else 0
        message.device_details.platform_type= EAuthTokenPlatformType.k_EAuthTokenPlatformType_SteamClient
        
        logger.info("Sending log on message using credentials in new authorization workflow")
        header, resp_bytes = await self._send_recv_service_message(socket, message, LOGIN_CREDENTIALS, next(self._job_id_iterator))
        if (header.eresult != EResult.OK):
            return None
        else:
            return CAuthentication_BeginAuthSessionViaCredentials_Response().parse(resp_bytes)

	#update login with steam guard code
    async def UpdateAuthSessionWithSteamGuardCode(self, socket) -> ProtoResult[CAuthentication_UpdateAuthSessionWithSteamGuardCode_Response]:
        pass
    
    #determine if we are logged on
    async def PollAuthSessionStatus(self, socket) -> ProtoResult[CAuthentication_PollAuthSessionStatus_Response]:
        pass

    #log on with token
    async def TokenLogOn(self, socket) -> ProtoResult[CMsgClientLogonResponse]:
        pass

    #log off
    async def LogOff(self, socket) -> ProtoResult[CMsgClientLoggedOff]:
        pass

    #log off and forget
    async def RevokeRefreshToken(self, socket) -> ProtoResult[CAuthentication_RefreshToken_Revoke_Response]:
        pass

    #get user stats
    async def GetUserStats(self, socket) -> ProtoResult[CMsgClientGetUserStatsResponse]:
        pass

    #get user license information
    async def PICSProductInfo(self, socket) -> ProtoResult[CMsgClientPICSProductInfoResponse]:
        pass

    #forgot
    async def GetAppRichPresenceLocalization(self, socket) -> ProtoResult[CCommunity_GetAppRichPresenceLocalization_Response]:
        pass

    #mystery
    async def Store_Download(self, socket) -> ProtoResult[CCloudConfigStore_Download_Response]:
        pass

    #danger
    async def GetLastPlayedTimes(self, socket) -> ProtoResult[CPlayer_GetLastPlayedTimes_Response]:
        pass

    #legally cannot say

    async def _send_async(self, socket: WebSocketClient, msg: Message):
        pass
    
    async def _send_recv_common(self, socket: WebSocketClient, msg: Message, job_id: int, callback : Callable[[Future], FutureInfo], 
                                target_job_id: Optional[int], job_name: Optional[str])-> Tuple[CMsgProtoBufHeader, bytes]:
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        info : FutureInfo = callback(future)
        self._future_lookup[job_id] = info
        header = self._generate_header(job_id, target_job_id, job_name)
        body = bytes(msg)
        emsg = info.sent_type
        #provide the information about the message being sent before the header and body.
        #Magic string decoded: < = little endian. 2I = 2 x unsigned integer. 
        #emsg | proto_mask is the first UInt (describes what we are sending), length of header is the second UInt.
        msg_info = struct.pack("<2I", emsg | self._PROTO_MASK, len(header))
        data = msg_info + header + body

        if LOG_SENSITIVE_DATA:
            logger.info("[Out] %s (%dB), params:\n", repr(emsg), len(data), repr(msg))
        else:
            logger.info("[Out] %s (%dB)", repr(emsg), len(data))
        await socket.send(data)


        header : CMsgProtoBufHeader
        data: bytes
        header, data = await self._future_lookup[job_id].future
        del self._future_lookup[job_id]
        return (header, data)

    async def _send_recv_service_message(self, socket: WebSocketClient, msg: Message, send_recv_name: str, job_id: int, target_job_id: Optional[int] = None) -> Tuple[CMsgProtoBufHeader, bytes]:
        emsg = EMsg.ServiceMethodCallFromClientNonAuthed if self.confirmed_steam_id is None else EMsg.ServiceMethodCallFromClient

        def um_generate_future(future: Future):
            return FutureInfo(future, emsg, EMsg.ServiceMethodResponse, send_recv_name)

        return await self._send_recv_common(socket, msg, job_id, um_generate_future, target_job_id, send_recv_name)

    async def _generate_header(self, job_id: int, target_job_id : Optional[int] = None, job_name: Optional[str] = None) -> CMsgProtoBufHeader:
        proto_header = CMsgProtoBufHeader()
        
        proto_header.jobid_source = job_id

        if self.confirmed_steam_id is not None:
            proto_header.steamid = self.confirmed_steam_id
        else:
            proto_header.steamid = 0 + self._ACCOUNT_ID_MASK
        if self._session_id is not None:
            proto_header.client_sessionid = self._session_id
        if target_job_id is not None:
            proto_header.jobid_target = target_job_id
        if job_name is not None:
            proto_header.target_job_name = job_name

        return proto_header

    async def _send_recv(self, socket: WebSocketClient, msg: Message, send_type: EMsg, expected_return_type: EMsg, job_id: int, target_job_id : Optional[int] = None, job_name: Optional[str] = None) -> Tuple[CMsgProtoBufHeader, bytes]:
        def normal_generate_future(future: Future) -> FutureInfo:
            return FutureInfo(future, send_type, expected_return_type)

        return await self._send_recv_common(socket, msg, job_id, normal_generate_future, target_job_id, job_name)

    async def process_packet(self, packet: bytes):
        package_size = len(packet)
        #packets reserve the first 8 bytes for the Message code (emsg) and 
        logger.debug("Processing packet of %d bytes", package_size)

        if package_size < 8:
            logger.warning("Package too small, ignoring...")
            return

        raw_emsg = int.from_bytes(packet[:4], "little")
        emsg: EMsg = EMsg(raw_emsg & ~self._PROTO_MASK)

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

    async def _process_message(self, emsg: EMsg, header: CMsgProtoBufHeader, body: bytes):
        logger.info("[In] %d -> EMsg.%s", emsg.value, emsg.name)
        if emsg == EMsg.Multi:
            await self._process_multi(body)
        else:
            emsg = EMsg.ServiceMethodResponse if emsg == EMsg.ServiceMethod else emsg #make sure it't not borked if it's a solicited service message.
            header_jobid : int = int(header.jobid_source)
            
            if (header_jobid in self._future_lookup ):
                future_info = self._future_lookup[header_jobid]
                is_expected, log_msg = future_info.is_expected_response_with_message(emsg, header.target_job_name)
                if not is_expected:
                    logger.warning(log_msg)
                elif future_info.future.cancelled():
                    logger.warning("Attempted to set future to the processed message, but it was already cancelled. Removing it from the list")
                    self._future_lookup.pop(header_jobid)
                else:
                    future_info.future.set_result((header, body))
                    return
            else:
                logger.info(f"Received Unsolicited message {emsg.name}" + (f"({header.target_job_name})" if emsg == EMsg.ServiceMethodResponse else ""))

        await self._handle_unsolicited_message(emsg, header, body)

    async def _process_multi(self, body: bytes):
        logger.debug("Processing message Multi")
        message = CMsgMulti().parse(body)
        if message.size_unzipped > 0:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, decompress, message.message_body)
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

    async def _handle_unsolicited_message(emsg: EMsg, header: CMsgProtoBufHeader, body: bytes):
        pass