from unittest.mock import MagicMock, ANY, call
import asyncio

import pytest
import websockets
from galaxy.api.errors import AccessDenied, BackendNotAvailable, BackendTimeout, BackendError, NetworkError
from galaxy.unittest.mock import async_return_value, skip_loop, AsyncMock

from protocol.websocket_client import WebSocketClient, RECONNECT_INTERVAL_SECONDS
from friends_cache import FriendsCache
from games_cache import GamesCache
from stats_cache import StatsCache
from times_cache import TimesCache
from user_info_cache import UserInfoCache
from ownership_ticket_cache import OwnershipTicketCache
from websocket_list import WebSocketList

from protocol.protocol_client import UserActionRequired

ACCOUNT_NAME = "john"
PASSWORD = "testing123"
TWO_FACTOR = "AbCdEf"


async def async_raise(error, loop_iterations_delay=0):
    if loop_iterations_delay > 0:
        await skip_loop(loop_iterations_delay)
    raise error


@pytest.fixture
def websocket_list():
    websocket_list = MagicMock(WebSocketList)
    return websocket_list


@pytest.fixture()
def protocol_client(mocker):
    protocol_client = mocker.patch("protocol.websocket_client.ProtocolClient").return_value
    protocol_client.get_steam_app_ownership_ticket = AsyncMock(return_value=async_return_value(None))
    protocol_client.register_auth_ticket_with_cm = AsyncMock(return_value=async_return_value(None))
    return protocol_client


@pytest.fixture
def websocket(mocker):
    websocket_ = MagicMock()
    mocker.patch(
        "protocol.websocket_client.websockets.connect",
        side_effect=lambda *args, **kwargs: async_return_value(AsyncMock())
    )
    return websocket_


@pytest.fixture
def friends_cache(mocker):
    return MagicMock(FriendsCache)

@pytest.fixture
def games_cache(mocker):
    return MagicMock(GamesCache)

@pytest.fixture
def stats_cache(mocker):
    return MagicMock(StatsCache)

@pytest.fixture
def times_cache(mocker):
    return MagicMock(TimesCache)

@pytest.fixture
def translations_cache():
    return dict()

@pytest.fixture
def user_info_cache(mocker):
    return MagicMock(UserInfoCache)

@pytest.fixture
def local_machine_cache():
    return MagicMock()

@pytest.fixture
def ownership_ticket_cache():
    return MagicMock(OwnershipTicketCache)

@pytest.fixture
async def client(backend_client, websocket_list, protocol_client, friends_cache, games_cache, translations_cache, stats_cache, times_cache, user_info_cache, local_machine_cache, ownership_ticket_cache):
    return WebSocketClient(backend_client, MagicMock(), websocket_list, friends_cache, games_cache, translations_cache, stats_cache, times_cache, user_info_cache, local_machine_cache, ownership_ticket_cache)


@pytest.mark.asyncio
async def test_connect_authenticate(client, protocol_client, websocket_list, websocket):
    websocket_list.get.return_value = async_return_value(["wss://abc.com/websocket"])
    protocol_client.run.return_value = async_raise(AssertionError)
    credentials_mock = {'password': PASSWORD, "two_factor": TWO_FACTOR}
    plugin_queue_mock = AsyncMock()
    websocket_queue_mock = AsyncMock()
    websocket_queue_mock.get.return_value = credentials_mock
    error_queue_mock = AsyncMock()
    error_queue_mock.get.return_value = MagicMock()
    client.communication_queues = {'plugin': plugin_queue_mock, 'websocket': websocket_queue_mock, 'errors': error_queue_mock}
    client._user_info_cache = MagicMock()
    client._user_info_cache.old_flow = False
    client._user_info_cache.token = False
    client._user_info_cache.account_username = ACCOUNT_NAME
    client._user_info_cache.two_step = None

    protocol_client.authenticate_password.return_value = async_return_value(UserActionRequired.NoActionRequired)
    protocol_client.close.return_value = async_return_value(None)
    protocol_client.wait_closed.return_value = async_return_value(None)
    with pytest.raises(AssertionError):
        await client.run()

    websocket_list.get.assert_called_once_with(0)
    protocol_client.run.assert_called_once_with()
    protocol_client.authenticate_password.assert_called_once_with(ACCOUNT_NAME, PASSWORD, TWO_FACTOR, ANY, ANY)


@pytest.mark.asyncio
async def test_websocket_close_reconnect(client, protocol_client, websocket_list, websocket):
    websocket_list.get.side_effect = [
        async_return_value(["wss://abc.com/websocket"]),
        async_return_value(["wss://abc.com/websocket"])
    ]
    protocol_client.run.side_effect = [
        async_raise(websockets.ConnectionClosedError(1002, ""), 10),
        async_raise(AssertionError)
    ]
    credentials_mock = {'password': PASSWORD, "two_factor": TWO_FACTOR}
    plugin_queue_mock = AsyncMock()
    websocket_queue_mock = AsyncMock()
    websocket_queue_mock.get.return_value = credentials_mock
    error_queue_mock = AsyncMock()
    error_queue_mock.get.return_value = MagicMock()
    client.communication_queues = {'plugin': plugin_queue_mock, 'websocket': websocket_queue_mock, 'errors': error_queue_mock}

    protocol_client.close.return_value = async_return_value(None)
    protocol_client.wait_closed.return_value = async_return_value(None)
    protocol_client.authenticate_token = AsyncMock()
    protocol_client.authenticate_token.return_value = async_return_value(None)

    websocket.close.return_value = async_return_value(None)
    websocket.wait_closed.return_value = async_return_value(None)

    client._user_info_cache = MagicMock()
    with pytest.raises(AssertionError):
        await client.run()

    assert websocket_list.get.call_count == 2
    assert protocol_client.authenticate_token.call_count == 2
    assert protocol_client.run.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [
    BackendNotAvailable(), BackendTimeout(), BackendError(), NetworkError()
])
async def test_servers_cache_retry(
    client, protocol_client, websocket_list, mocker, exception, websocket
):
    websocket_list.get.side_effect = [
        async_raise(exception),
        async_return_value(["wss://abc.com/websocket"])
    ]
    protocol_client.run.return_value = async_raise(AssertionError)
    sleep = mocker.patch("protocol.websocket_client.asyncio.sleep", side_effect=lambda x: async_return_value(None))
    client._authenticate = AsyncMock()

    with pytest.raises(AssertionError):
        await client.run()
    assert websocket_list.get.call_count == 2
    sleep.assert_any_call(RECONNECT_INTERVAL_SECONDS)

@pytest.mark.asyncio
async def test_servers_cache_failure(client, protocol_client, backend_client, websocket_list):
    websocket_list.get.return_value = async_raise(AccessDenied())
    with pytest.raises(AccessDenied):
        await client.run()
    websocket_list.get.assert_called_once_with(0)
    backend_client.get_authentication_data.assert_not_called()
    protocol_client.authenticate.assert_not_called()
    protocol_client.run.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [
    asyncio.TimeoutError(), IOError(), websockets.InvalidURI("wss://websocket_1"), websockets.InvalidHandshake()
])
async def test_connect_error(client, protocol_client, websocket_list, mocker, exception):
    websocket_list.get.side_effect = [
        async_return_value(["wss://websocket_1", "wss://websocket_2"])
    ]
    connect = mocker.patch(
        "protocol.websocket_client.websockets.connect",
        side_effect=[
            async_raise(exception),
            async_return_value(MagicMock())
        ]
    )
    protocol_client.run.return_value = async_raise(AssertionError)
    client._authenticate = AsyncMock()
    with pytest.raises(AssertionError):
        await client.run()
    connect.assert_has_calls([call("wss://websocket_1", max_size=ANY, ssl=ANY), call("wss://websocket_2", max_size=ANY, ssl=ANY)])


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [
    asyncio.TimeoutError(), IOError(), websockets.InvalidURI("wss://websocket_1"), websockets.InvalidHandshake()
])
async def test_connect_error_all_servers(client, protocol_client, websocket_list, mocker, exception):
    websocket_list.get.side_effect = [
        async_return_value(["wss://websocket_1"]),
        async_return_value(["wss://websocket_1"]),
    ]
    connect = mocker.patch(
        "protocol.websocket_client.websockets.connect",
        side_effect=[
            async_raise(exception),
            async_return_value(AsyncMock())
        ]
    )
    sleep = mocker.patch("protocol.websocket_client.asyncio.sleep", side_effect=lambda x: async_return_value(None))
    protocol_client.run.return_value = async_raise(AssertionError)
    client._authenticate = AsyncMock()
    with pytest.raises(AssertionError):
        await client.run()
    connect.assert_has_calls([call("wss://websocket_1", max_size=ANY, ssl=ANY), call("wss://websocket_1", max_size=ANY, ssl=ANY)])
    sleep.assert_any_call(RECONNECT_INTERVAL_SECONDS)
