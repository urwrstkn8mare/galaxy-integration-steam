import pytest
import time
from servers_cache import ServersCache
from asyncio import Event, TimeoutError
from unittest.mock import MagicMock, ANY, call
from galaxy.unittest.mock import async_return_value, skip_loop
import websockets
from async_mock import AsyncMock


async def async_raise(error, loop_iterations_delay=0):
    if loop_iterations_delay > 0:
        await skip_loop(loop_iterations_delay)
    raise error


def wrap_address(addr):
    return "wss://{}/cmsocket/".format(addr)


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [
    TimeoutError(), IOError(), websockets.InvalidURI(wrap_address("address_1")), websockets.InvalidHandshake()
])
async def test_no_cache_all_connect_failure(backend_client, mocker, exception):
    addresses = [
        "address_1"
    ]

    persistent_cache = {}
    persistent_cache_update_event = Event()

    cache = ServersCache(backend_client, persistent_cache, persistent_cache_update_event)
    backend_client.get_servers.return_value = addresses

    connect = mocker.patch(
        "protocol.websocket_client.websockets.connect",
        side_effect=[
            async_raise(exception),
            async_raise(exception)
        ]
    )

    assert await cache.get() == []
    backend_client.get_servers.assert_called_once_with()
    assert 'servers_cache' not in persistent_cache
    assert not persistent_cache_update_event.is_set()
    connect.assert_has_calls([call(wrap_address(address), ssl=ANY) for address in addresses])


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [
    TimeoutError(), IOError(), websockets.InvalidURI(wrap_address("address_1")), websockets.InvalidHandshake()
])
async def test_no_cache_fist_connect_failure(backend_client, mocker, exception):
    addresses = [
        "address_1",
        "address_2"
    ]

    persistent_cache = {}
    persistent_cache_update_event = Event()

    cache = ServersCache(backend_client, persistent_cache, persistent_cache_update_event)
    backend_client.get_servers.return_value = addresses

    websocket = MagicMock()
    websocket.close = AsyncMock()
    websocket.close.return_value = None
    connect = mocker.patch(
        "protocol.websocket_client.websockets.connect",
        side_effect=[
            async_raise(exception),
            async_return_value(websocket)
        ]
    )

    assert await cache.get() == [wrap_address(addresses[1])]
    backend_client.get_servers.assert_called_once_with()
    assert 'servers_cache' in persistent_cache
    assert persistent_cache_update_event.is_set()
    connect.assert_has_calls([call(wrap_address(address), ssl=ANY) for address in addresses])


@pytest.mark.asyncio
async def test_valid_cache(backend_client):
    addresses = [
        "address_1"
    ]

    persistent_cache = {'servers_cache': {'timeout': time.time() + 10, 'servers': [(addresses[0], 3.206969738006592)]}}
    persistent_cache_update_event = Event()

    cache = ServersCache(backend_client, persistent_cache, persistent_cache_update_event)
    assert await cache.get() == addresses
    backend_client.get_servers.assert_not_called()
    assert not persistent_cache_update_event.is_set()


@pytest.mark.asyncio
async def test_timeouted_cache(backend_client, mocker):
    addresses = [
        "echo.websocket.org"
    ]

    persistent_cache = {
        'servers_cache': {
            'timeout': time.time() - 10,
            'servers': [(wrap_address(address), 3.206969738006592) for address in addresses]
        }
    }
    persistent_cache_update_event = Event()

    cache = ServersCache(backend_client, persistent_cache, persistent_cache_update_event)
    backend_client.get_servers.return_value = addresses

    websocket = MagicMock()
    websocket.close = AsyncMock()
    websocket.close.return_value = None
    connect = mocker.patch(
        "protocol.websocket_client.websockets.connect",
        side_effect=lambda *args, **kwargs: async_return_value(websocket)
    )

    assert await cache.get() == [wrap_address(address) for address in addresses]
    backend_client.get_servers.assert_called_once_with()
    assert persistent_cache['servers_cache']['timeout'] > time.time()
    assert persistent_cache_update_event.is_set()
    connect.assert_has_calls([call(wrap_address(address), ssl=ANY) for address in addresses])
