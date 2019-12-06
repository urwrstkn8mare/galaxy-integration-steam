import asyncio
import struct
import gzip
import logging
from itertools import count
from typing import Awaitable, Callable,Dict, Optional

from protocol.messages import steammessages_base_pb2, steammessages_clientserver_login_pb2, \
    steammessages_clientserver_friends_pb2
from protocol.messages.steammessages_chat import steamclient_pb2
from protocol.consts import EMsg, EResult, EAccountType, EFriendRelationship, EPersonaState
from protocol.types import SteamId, UserInfo


logger = logging.getLogger(__name__)


class ProtobufClient:
    _PROTO_MASK = 0x80000000

    def __init__(self, socket):
        self._socket = socket
        self.log_on_handler: Optional[Callable[[EResult], Awaitable[None]]] = None
        self.log_off_handler: Optional[Callable[[EResult], Awaitable[None]]] = None
        self.relationship_handler: Optional[Callable[[bool, Dict[int, EFriendRelationship]], Awaitable[None]]] = None
        self.user_info_handler: Optional[Callable[[int, UserInfo], Awaitable[None]]] = None
        self._steam_id: Optional[int] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._session_id: Optional[int] = None
        self._job_id_iterator = count(1)

    async def close(self):
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()

    async def wait_closed(self):
        pass

    async def run(self):
        while True:
            packet = await self._socket.recv()
            await self._process_packet(packet)

    async def log_on(self, steam_id, account_name, token):
        # magic numbers taken from JavaScript Steam client
        message = steammessages_clientserver_login_pb2.CMsgClientLogon()
        message.account_name = account_name
        message.protocol_version = 65580
        message.qos_level = 2
        message.client_os_type = 4294966596
        message.ui_mode = 4
        message.chat_mode = 2
        message.web_logon_nonce = token
        message.client_instance_id = 0

        try:
            self._steam_id = steam_id
            await self._send(EMsg.ClientLogon, message)
        except Exception:
            self._steam_id = None
            raise

    async def set_persona_state(self, state):
        message = steammessages_clientserver_friends_pb2.CMsgClientChangeStatus()
        message.persona_state = state
        await self._send(EMsg.ClientChangeStatus, message)

    async def get_friends_statuses(self):
        job_id = next(self._job_id_iterator)
        message = steamclient_pb2.CChat_RequestFriendPersonaStates_Request()
        await self._send(EMsg.ServiceMethodCallFromClient, message, job_id, None, "Chat.RequestFriendPersonaStates#1")

    async def get_user_infos(self, users, flags):
        message = steammessages_clientserver_friends_pb2.CMsgClientRequestFriendData()
        message.friends.extend(users)
        message.persona_state_requested = flags
        await self._send(EMsg.ClientRequestFriendData, message)

    async def _send(
            self,
            emsg,
            message,
            source_job_id=None,
            target_job_id=None,
            target_job_name=None
    ):
        proto_header = steammessages_base_pb2.CMsgProtoBufHeader()
        if self._steam_id is not None:
            proto_header.steamid = self._steam_id
        if self._session_id is not None:
            proto_header.client_sessionid = self._session_id
        if source_job_id is not None:
            proto_header.jobid_source = source_job_id
        if target_job_name is not None:
            proto_header.target_job_name = target_job_name

        header = proto_header.SerializeToString()

        body = message.SerializeToString()
        data = struct.pack("<2I", emsg | self._PROTO_MASK, len(header))
        data = data + header + body

        logger.debug("Sending message %d (%d bytes)", emsg, len(data))
        await self._socket.send(data)

    async def _heartbeat(self, interval):
        message = steammessages_clientserver_login_pb2.CMsgClientHeartBeat()
        while True:
            await asyncio.sleep(interval)
            await self._send(EMsg.ClientHeartBeat, message)

    async def _process_packet(self, packet):
        package_size = len(packet)
        logger.debug("Processing packet of %d bytes", package_size)
        if package_size < 8:
            logger.warning("Package too small, ignoring...")
        raw_emsg = struct.unpack("<I", packet[:4])[0]
        emsg = raw_emsg & ~self._PROTO_MASK
        if raw_emsg & self._PROTO_MASK != 0:
            header_len = struct.unpack("<I", packet[4:8])[0]
            header = steammessages_base_pb2.CMsgProtoBufHeader()
            header.ParseFromString(packet[8:8 + header_len])
            if self._session_id is None and header.client_sessionid != 0:
                logger.info("Session id: %d", header.client_sessionid)
                self._session_id = header.client_sessionid
            await self._process_message(emsg, header, packet[8 + header_len:])
        else:
            logger.warning("Packet with extended header - ignoring")

    async def _process_message(self, emsg, header, body):
        logger.debug("Processing message %d", emsg)
        if emsg == EMsg.Multi:
            await self._process_multi(body)
        elif emsg == EMsg.ClientLogOnResponse:
            await self._process_client_log_on_response(body)
        elif emsg == EMsg.ClientLogOff:
            await self._process_client_log_off(body)
        elif emsg == EMsg.ClientFriendsList:
            await self._process_client_friend_list(body)
        elif emsg == EMsg.ClientPersonaState:
            await self._process_client_persona_state(body)
        elif emsg == EMsg.ServiceMethodResponse:
            await self._process_service_method_response(header.target_job_name, body)
        else:
            logger.warning("Ignored message %d", emsg)

    async def _process_multi(self, body):
        logger.debug("Processing message Multi")
        message = steammessages_base_pb2.CMsgMulti()
        message.ParseFromString(body)
        if message.size_unzipped > 0:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, gzip.decompress, message.message_body)
        else:
            data = message.message_body

        data_size = len(data)
        offset = 0
        size_bytes = 4
        while offset + size_bytes <= data_size:
            size = struct.unpack("<I", data[offset:offset + size_bytes])[0]
            await self._process_packet(data[offset + size_bytes:offset + size_bytes + size])
            offset += size_bytes + size
        logger.debug("Finished processing message Multi")

    async def _process_client_log_on_response(self, body):
        logger.debug("Processing message ClientLogOnResponse")
        message = steammessages_clientserver_login_pb2.CMsgClientLogonResponse()
        message.ParseFromString(body)
        result = message.eresult

        if result == EResult.OK:
            interval = message.out_of_game_heartbeat_seconds
            self._heartbeat_task = asyncio.create_task(self._heartbeat(interval))

        if self.log_on_handler is not None:
            await self.log_on_handler(result)

    async def _process_client_log_off(self, body):
        logger.debug("Processing message ClientLoggedOff")
        message = steammessages_clientserver_login_pb2.CMsgClientLoggedOff()
        message.ParseFromString(body)
        result = message.eresult

        assert self._heartbeat_task is not None
        self._heartbeat_task.cancel()

        if self.log_off_handler is not None:
            await self.log_off_handler(result)

    async def _process_client_friend_list(self, body):
        logger.debug("Processing message ClientFriendsList")
        if self.relationship_handler is None:
            return

        message = steammessages_clientserver_friends_pb2.CMsgClientFriendsList()
        message.ParseFromString(body)

        friends = {}
        for relationship in message.friends:
            steam_id = relationship.ulfriendid
            details = SteamId.parse(steam_id)
            if details.type_ == EAccountType.Individual:
                friends[steam_id] = EFriendRelationship(relationship.efriendrelationship)

        await self.relationship_handler(message.bincremental, friends)

    async def _process_client_persona_state(self, body):
        logger.debug("Processing message ClientPersonaState")
        if self.user_info_handler is None:
            return

        message = steammessages_clientserver_friends_pb2.CMsgClientPersonaState()
        message.ParseFromString(body)

        for user in message.friends:
            user_id = user.friendid
            user_info = UserInfo()
            if user.HasField("player_name"):
                user_info.name = user.player_name
            if user.HasField("avatar_hash"):
                user_info.avatar_hash = user.avatar_hash
            if user.HasField("persona_state"):
                user_info.state = EPersonaState(user.persona_state)
            if user.HasField("gameid"):
                user_info.game_id = user.gameid
                rich_presence: Dict[str, str] = {}
                for element in user.rich_presence:
                    rich_presence[element.key] = element.value
                user_info.rich_presence = rich_presence
            if user.HasField("game_name"):
                user_info.game_name = user.game_name

            await self.user_info_handler(user_id, user_info)

    async def _process_service_method_response(self, target_job_name, body):
        logger.debug("Processing message ServiceMethodResponse %s", target_job_name)
