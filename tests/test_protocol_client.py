import asyncio
from unittest.mock import MagicMock, ANY

import pytest
from galaxy.api.errors import AccessDenied, Banned
from galaxy.unittest.mock import async_return_value, skip_loop

from protocol.consts import EResult, EFriendRelationship
from protocol.protocol_client import ProtocolClient
from protocol.types import UserInfo


STEAM_ID = 71231321
ACCOUNT_NAME = "john"
TOKEN = "TOKEN"


@pytest.fixture
def protobuf_client(mocker):
    mock = mocker.patch("protocol.protocol_client.ProtobufClient")
    return mock.return_value


@pytest.fixture()
def friends_cache():
    return MagicMock()

@pytest.fixture()
def games_cache():
    return MagicMock()

@pytest.fixture
async def client(protobuf_client, friends_cache, games_cache):
    return ProtocolClient(MagicMock(), friends_cache, games_cache)


@pytest.mark.asyncio
async def test_close(client, protobuf_client):
    protobuf_client.close.return_value = async_return_value(None)
    await client.close()
    protobuf_client.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_authenticate_success(client, protobuf_client):
    protobuf_client.log_on.return_value = async_return_value(None)
    auth_task = asyncio.create_task(client.authenticate(STEAM_ID, ACCOUNT_NAME, TOKEN, None))
    await skip_loop()
    await protobuf_client.log_on_handler(EResult.OK)
    await auth_task
    protobuf_client.log_on.assert_called_once_with(STEAM_ID, ACCOUNT_NAME, TOKEN)


@pytest.mark.asyncio
async def test_authenticate_failure(client, protobuf_client):
    auth_lost_handler = MagicMock()
    protobuf_client.log_on.return_value = async_return_value(None)
    auth_task = asyncio.create_task(client.authenticate(STEAM_ID, ACCOUNT_NAME, TOKEN, auth_lost_handler))
    await skip_loop()
    await protobuf_client.log_on_handler(EResult.AccessDenied)
    with pytest.raises(AccessDenied):
        await auth_task
    auth_lost_handler.assert_not_called()


@pytest.mark.asyncio
async def test_log_out(client, protobuf_client):
    auth_lost_handler = MagicMock(return_value=async_return_value(None))
    protobuf_client.log_on.return_value = async_return_value(None)
    auth_task = asyncio.create_task(client.authenticate(STEAM_ID, ACCOUNT_NAME, TOKEN, auth_lost_handler))
    await skip_loop()
    await protobuf_client.log_on_handler(EResult.OK)
    await auth_task
    await protobuf_client.log_off_handler(EResult.Banned)
    auth_lost_handler.assert_called_with(Banned({"result": EResult.Banned}))


@pytest.mark.asyncio
async def test_relationship_initial(client, protobuf_client, friends_cache):
    friends = {
        15: EFriendRelationship.Friend,
        56: EFriendRelationship.Friend
    }

    protobuf_client.set_persona_state.return_value = async_return_value(None)
    protobuf_client.get_friends_statuses.return_value = async_return_value(None)
    protobuf_client.get_user_infos.return_value = async_return_value(None)
    await protobuf_client.relationship_handler(False, friends)
    friends_cache.reset.assert_called_once_with([15, 56])
    protobuf_client.get_friends_statuses.assert_called_once_with()
    protobuf_client.get_user_infos.assert_called_once_with([15, 56], ANY)


@pytest.mark.asyncio
async def test_relationship_update(client, protobuf_client, friends_cache):
    friends = {
        15: EFriendRelationship.Friend,
        56: EFriendRelationship.None_
    }
    protobuf_client.get_friends_statuses.return_value = async_return_value(None)
    protobuf_client.get_user_infos.return_value = async_return_value(None)
    await protobuf_client.relationship_handler(True, friends)
    friends_cache.add.assert_called_once_with(15)
    friends_cache.remove.assert_called_once_with(56)
    protobuf_client.get_friends_statuses.assert_called_once_with()
    protobuf_client.get_user_infos.assert_called_once_with([15], ANY)


@pytest.mark.asyncio
async def test_user_info(client, protobuf_client, friends_cache):
    user_id = 15
    user_info = UserInfo("Ola")
    await protobuf_client.user_info_handler(user_id, user_info)
    friends_cache.update.assert_called_once_with(user_id, user_info)
