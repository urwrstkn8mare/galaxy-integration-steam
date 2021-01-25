from unittest.mock import MagicMock

import pytest
from galaxy.unittest.mock import AsyncMock

from websocket_cache import WebSocketCache


@pytest.mark.asyncio
async def test_get_returns_websocket_from_cache():
    cell_id = 0
    address = "address_from_cache"
    websocket_cache_persistence = MagicMock()
    websocket_cache_persistence.read = MagicMock(return_value=address)
    websocket_list = MagicMock()
    websocket_cache = WebSocketCache(websocket_cache_persistence, websocket_list)

    async for socket in websocket_cache.get(cell_id):
        assert socket == address
        break


@pytest.mark.asyncio
async def test_get_returns_first_address_in_websocket_list_if_valid_cache_unavailable():
    cell_id = 0
    address = None
    address_list = ["address_from_steam_1", "address_from_steam_2"]
    websocket_cache_persistence = MagicMock()
    websocket_cache_persistence.read = MagicMock(return_value=address)
    websocket_list = MagicMock()
    websocket_list.get_ordered_by_ping = AsyncMock(return_value=address_list)
    websocket_cache = WebSocketCache(websocket_cache_persistence, websocket_list)

    async for socket in websocket_cache.get(cell_id):
        assert socket == address_list[0]
        break


@pytest.mark.asyncio
async def test_get_returns_all_addresses_while_iterating():
    cell_id = 0
    address = "address_from_cache"
    address_list = ["address_from_steam_1", "address_from_steam_2"]
    websocket_cache_persistence = MagicMock()
    websocket_cache_persistence.read = MagicMock(return_value=address)
    websocket_list = MagicMock()
    websocket_list.get_ordered_by_ping = AsyncMock(return_value=address_list)
    websocket_cache = WebSocketCache(websocket_cache_persistence, websocket_list)

    returned_addresses = []

    async for socket in websocket_cache.get(cell_id):
        returned_addresses.append(socket)

    assert returned_addresses[0] == address
    assert returned_addresses[1] == address_list[0]
    assert returned_addresses[2] == address_list[1]
