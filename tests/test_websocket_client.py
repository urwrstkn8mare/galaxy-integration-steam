from unittest.mock import MagicMock, ANY, call
import asyncio

import pytest
import websockets
from galaxy.api.errors import AccessDenied, BackendNotAvailable, BackendTimeout, BackendError, NetworkError
from galaxy.unittest.mock import async_return_value, skip_loop

from protocol.websocket_client import WebSocketClient, RECONNECT_INTERVAL_SECONDS
from protocol.types import UserInfo
from servers_cache import ServersCache
from friends_cache import FriendsCache

STEAM_ID = 71231321
ACCOUNT_NAME = "john"
TOKEN = "TOKEN"


async def async_raise(error, loop_iterations_delay=0):
    if loop_iterations_delay > 0:
        await skip_loop(loop_iterations_delay)
    raise error


@pytest.fixture
def servers_cache():
    return MagicMock(ServersCache)


@pytest.fixture()
def protocol_client(mocker):
    return mocker.patch("protocol.websocket_client.ProtocolClient").return_value


@pytest.fixture
def websocket(mocker):
    websocket_ = MagicMock()
    mocker.patch(
        "protocol.websocket_client.websockets.connect",
        side_effect=lambda *args, **kwargs: async_return_value(websocket_)
    )
    return websocket_


@pytest.fixture
def friends_cache(mocker):
    return MagicMock(FriendsCache)


@pytest.fixture
async def client(backend_client, servers_cache, protocol_client, friends_cache):
    return WebSocketClient(backend_client, servers_cache, friends_cache)


@pytest.mark.asyncio
async def test_get_friends(client, friends_cache):
    friends_cache.wait_ready.return_value = async_return_value(None)
    friends_cache.user_ids.return_value = [1, 5, 7]
    assert await client.get_friends() == ["1", "5", "7"]
    friends_cache.wait_ready.assert_called_once_with()
    friends_cache.user_ids.assert_called_once_with()


@pytest.mark.asyncio
async def test_get_friends_info(client, friends_cache):
    friends_cache.wait_ready.return_value = async_return_value(None)
    friends_cache.get.side_effect = [
        UserInfo("Franek"),
        None,
        UserInfo("Janek")
    ]
    assert await client.get_friends_info(["1", "5", "7"]) == {
        "1": UserInfo("Franek"),
        "7": UserInfo("Janek")
    }
    friends_cache.wait_ready.assert_called_once_with()
    friends_cache.get.assert_has_calls([call(1), call(5), call(7)])


@pytest.mark.asyncio
async def test_connect_authenticate(client, protocol_client, backend_client, servers_cache, websocket):
    servers_cache.get.return_value = async_return_value(["wss://abc.com/websocket"])
    backend_client.get_authentication_data.return_value = STEAM_ID, ACCOUNT_NAME, TOKEN
    protocol_client.authenticate.return_value = async_return_value(None)
    protocol_client.run.return_value = async_raise(websockets.ConnectionClosedOK(1000, ""), 10)
    await client.run()
    servers_cache.get.assert_called_once_with()
    protocol_client.authenticate.assert_called_once_with(STEAM_ID, ACCOUNT_NAME, TOKEN, ANY)
    protocol_client.run.assert_called_once_with()


@pytest.mark.asyncio
async def test_websocket_close_reconnect(client, protocol_client, backend_client, servers_cache, websocket):
    servers_cache.get.side_effect = [
        async_return_value(["wss://abc.com/websocket"]),
        async_return_value(["wss://abc.com/websocket"])
    ]
    backend_client.get_authentication_data.return_value = STEAM_ID, ACCOUNT_NAME, TOKEN
    protocol_client.authenticate.return_value = async_return_value(None)
    protocol_client.run.side_effect = [
        async_raise(websockets.ConnectionClosedError(1002, ""), 10),
        async_raise(websockets.ConnectionClosedOK(1000, ""), 10)
    ]
    protocol_client.close.return_value = async_return_value(None)
    protocol_client.wait_closed.return_value = async_return_value(None)
    websocket.close.return_value = async_return_value(None)
    websocket.wait_closed.return_value = async_return_value(None)
    await client.run()
    assert servers_cache.get.call_count == 2
    assert protocol_client.authenticate.call_count == 2
    assert protocol_client.run.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [
    BackendNotAvailable(), BackendTimeout(), BackendError(), NetworkError()
])
async def test_servers_cache_retry(
    client, protocol_client, backend_client, servers_cache, websocket, mocker, exception
):
    servers_cache.get.side_effect = [
        async_raise(exception),
        async_return_value(["wss://abc.com/websocket"])
    ]
    sleep = mocker.patch("protocol.websocket_client.asyncio.sleep", side_effect=lambda x: async_return_value(None))
    backend_client.get_authentication_data.return_value = STEAM_ID, ACCOUNT_NAME, TOKEN
    protocol_client.authenticate.return_value = async_return_value(None)
    protocol_client.run.return_value = async_raise(websockets.ConnectionClosedOK(1000, ""), 10)
    await client.run()
    sleep.assert_any_call(RECONNECT_INTERVAL_SECONDS)

@pytest.mark.asyncio
async def test_servers_cache_failure(client, protocol_client, backend_client, servers_cache):
    servers_cache.get.return_value = async_raise(AccessDenied())
    await client.run()
    servers_cache.get.assert_called_once_with()
    backend_client.get_authentication_data.assert_not_called()
    protocol_client.authenticate.assert_not_called()
    protocol_client.run.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [
    asyncio.TimeoutError(), IOError(), websockets.InvalidURI("wss://websocket_1"), websockets.InvalidHandshake()
])
async def test_connect_error(client, backend_client, protocol_client, servers_cache, mocker, exception):
    servers_cache.get.side_effect = [
        async_return_value(["wss://websocket_1", "wss://websocket_2"]),
    ]
    connect = mocker.patch(
        "protocol.websocket_client.websockets.connect",
        side_effect=[
            async_raise(exception),
            async_return_value(MagicMock())
        ]
    )
    backend_client.get_authentication_data.return_value = STEAM_ID, ACCOUNT_NAME, TOKEN
    protocol_client.authenticate.return_value = async_return_value(None)
    protocol_client.run.return_value = async_raise(websockets.ConnectionClosedOK(1000, ""), 10)
    await client.run()
    connect.assert_has_calls([call("wss://websocket_1", ssl=ANY), call("wss://websocket_2", ssl=ANY)])


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [
    asyncio.TimeoutError(), IOError(), websockets.InvalidURI("wss://websocket_1"), websockets.InvalidHandshake()
])
async def test_connect_error_all_servers(client, backend_client, protocol_client, servers_cache, mocker, exception):
    servers_cache.get.side_effect = [
        async_return_value(["wss://websocket_1"]),
        async_return_value(["wss://websocket_1"])
    ]
    connect = mocker.patch(
        "protocol.websocket_client.websockets.connect",
        side_effect=[
            async_raise(exception),
            async_return_value(MagicMock())
        ]
    )
    sleep = mocker.patch("protocol.websocket_client.asyncio.sleep", side_effect=lambda x: async_return_value(None))
    backend_client.get_authentication_data.return_value = STEAM_ID, ACCOUNT_NAME, TOKEN
    protocol_client.authenticate.return_value = async_return_value(None)
    protocol_client.run.return_value = async_raise(websockets.ConnectionClosedOK(1000, ""), 10)
    await client.run()
    connect.assert_has_calls([call("wss://websocket_1", ssl=ANY), call("wss://websocket_1", ssl=ANY)])
    sleep.assert_any_call(RECONNECT_INTERVAL_SECONDS)

