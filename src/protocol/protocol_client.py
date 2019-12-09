import asyncio
import logging

import galaxy.api.errors

from protocol.protobuf_client import ProtobufClient
from protocol.consts import EResult, EFriendRelationship, EPersonaState
from friends_cache import FriendsCache


logger = logging.getLogger(__name__)


def translate_error(result: EResult):
    assert result != EResult.OK
    data = {
        "result": result
    }
    if result in (
        EResult.AccountNotFound,
        EResult.InvalidSteamID,
        EResult.InvalidLoginAuthCode,
        EResult.AccountLogonDeniedNoMailSent,
        EResult.AccountLoginDeniedNeedTwoFactor
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
        EResult.AccountNotFeatured,
        EResult.AccountLogonDenied
    ):
        return galaxy.api.errors.AccessDenied(data)
    if result in (
        EResult.DataCorruption,
        EResult.DiskFull,
        EResult.RemoteCallFailed,
        EResult.RemoteFileConflict,
        EResult.BadResponse
    ):
        return galaxy.api.errors.BackendError

    return galaxy.api.errors.UnknownError(data)


class ProtocolClient:
    _STATUS_FLAG = 1106

    def __init__(self, socket, friends_cache: FriendsCache):
        self._protobuf_client = ProtobufClient(socket)
        self._protobuf_client.log_on_handler = self._log_on_handler
        self._protobuf_client.log_off_handler = self._log_off_handler
        self._protobuf_client.relationship_handler = self._relationship_handler
        self._protobuf_client.user_info_handler = self._user_info_handler
        self._friends_cache = friends_cache
        self._auth_lost_handler = None
        self._login_future = None

    async def close(self):
        await self._protobuf_client.close()

    async def wait_closed(self):
        await self._protobuf_client.wait_closed()

    async def run(self):
        await self._protobuf_client.run()

    async def authenticate(self, steam_id, account_name, token, auth_lost_handler):
        loop = asyncio.get_running_loop()
        self._login_future = loop.create_future()
        await self._protobuf_client.log_on(steam_id, account_name, token)
        result = await self._login_future
        if result == EResult.OK:
            self._auth_lost_handler = auth_lost_handler
        else:
            raise translate_error(result)

    async def _log_on_handler(self, result: EResult):
        assert self._login_future is not None
        self._login_future.set_result(result)

    async def _log_off_handler(self, result):
        logger.warning("Logged off, result: %d", result)
        if self._auth_lost_handler is not None:
            await self._auth_lost_handler(translate_error(result))

    async def _relationship_handler(self, incremental, friends):
        initial_friends = []
        for user_id, relationship in friends.items():
            if relationship == EFriendRelationship.Friend:
                if incremental:
                    self._friends_cache.add(user_id)
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

    async def _user_info_handler(self, user_id, user_info):
        self._friends_cache.update_info(user_id, user_info)
