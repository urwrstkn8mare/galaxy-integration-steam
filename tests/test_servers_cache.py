import pytest
import json
import time
from asyncio import TimeoutError
from unittest.mock import MagicMock, ANY, call
import websockets

from galaxy.unittest.mock import async_return_value, skip_loop

from servers_cache import ServersCache
from async_mock import AsyncMock
from persistent_cache_state import PersistentCacheState


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
    persistent_cache_state = PersistentCacheState()

    cache = ServersCache(backend_client, MagicMock(), persistent_cache, persistent_cache_state)
    backend_client.get_servers.return_value = addresses

    connect = mocker.patch(
        "protocol.websocket_client.websockets.connect",
        return_value=async_raise(exception)
    )
    used_server_cell_id = "0"
    assert await cache.get(used_server_cell_id) == []
    backend_client.get_servers.assert_called_once_with(used_server_cell_id)
    assert 'servers_cache' not in persistent_cache
    assert not persistent_cache_state.modified
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
    persistent_cache_state = PersistentCacheState()

    cache = ServersCache(backend_client, MagicMock(), persistent_cache, persistent_cache_state)
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
    used_server_cell_id = "0"
    assert await cache.get(used_server_cell_id) == [wrap_address(addresses[1])]
    backend_client.get_servers.assert_called_once_with(used_server_cell_id)
    assert 'servers_cache' in persistent_cache
    assert persistent_cache_state.modified
    connect.assert_has_calls([call(wrap_address(address), ssl=ANY) for address in addresses])


@pytest.mark.asyncio
async def test_valid_cache(backend_client):
    addresses = [
        "address_1"
    ]
    used_server_cell_id = "0"

    persistent_cache = {'servers_cache': json.dumps({used_server_cell_id: {'timeout': time.time() + 10, 'servers': [(addresses[0], 3.206969738006592)]}})}
    persistent_cache_state = PersistentCacheState()

    cache = ServersCache(backend_client, MagicMock(), persistent_cache, persistent_cache_state)
    assert await cache.get(used_server_cell_id) == addresses
    backend_client.get_servers.assert_not_called()
    assert not persistent_cache_state.modified


@pytest.mark.asyncio
async def test_timeouted_cache(backend_client, mocker):
    addresses = [
        "echo.websocket.org"
    ]

    used_server_cell_id = "0"
    persistent_cache = {
        'servers_cache': json.dumps({
            used_server_cell_id:{
                'timeout': time.time() - 10,
                'servers': [(wrap_address(address), 3.206969738006592) for address in addresses]
            }
        })
    }
    persistent_cache_state = PersistentCacheState()

    cache = ServersCache(backend_client, MagicMock(), persistent_cache, persistent_cache_state)
    backend_client.get_servers.return_value = addresses

    websocket = MagicMock()
    websocket.close = AsyncMock()
    websocket.close.return_value = None
    connect = mocker.patch(
        "protocol.websocket_client.websockets.connect",
        side_effect=lambda *args, **kwargs: async_return_value(websocket)
    )
    assert await cache.get(used_server_cell_id) == [wrap_address(address) for address in addresses]
    backend_client.get_servers.assert_called_once_with(used_server_cell_id)
    assert json.loads(persistent_cache['servers_cache'])[used_server_cell_id]['timeout'] > time.time()
    assert persistent_cache_state.modified
    connect.assert_has_calls([call(wrap_address(address), ssl=ANY) for address in addresses])
