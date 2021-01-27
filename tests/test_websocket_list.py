from asyncio import sleep
from unittest.mock import MagicMock

import pytest
import websockets
from galaxy.unittest.mock import AsyncMock

from websocket_list import WebSocketList


@pytest.mark.asyncio
async def test_get_ordered_by_ping_returns_single_server(backend_client, monkeypatch):
    cell_id = 0
    address = "cm2-waw1.cm.teststeam.com:27039"
    backend_client.get_servers.return_value = [address]
    ssl_context = MagicMock()

    websocket = MagicMock()
    websocket.close = AsyncMock()
    websockets_connect = AsyncMock(return_value=websocket)
    monkeypatch.setattr(websockets, 'connect', websockets_connect)
    websocket_list = WebSocketList(backend_client, ssl_context)

    servers = await websocket_list.get_ordered_by_ping(cell_id)

    assert len(servers) == 1
    assert servers[0] == f"wss://{address}/cmsocket/"


@pytest.mark.asyncio
async def test_get_ordered_by_ping_queries_list_with_given_cell_id(backend_client):
    cell_id = 1
    address = "cm2-waw1.cm.teststeam.com:27039"
    backend_client.get_servers.return_value = [address]
    ssl_context = MagicMock()
    websocket_list = WebSocketList(backend_client, ssl_context)

    await websocket_list.get_ordered_by_ping(cell_id)

    backend_client.get_servers.assert_called_once_with(cell_id)


@pytest.mark.asyncio
async def test_get_ordered_by_ping_connects_to_servers_and_closes_connection(backend_client, monkeypatch):
    cell_id = 0
    address = "cm2-waw1.cm.teststeam.com:27039"
    backend_client.get_servers.return_value = [address]
    ssl_context = MagicMock()

    websocket = MagicMock()
    websocket.close = AsyncMock()
    websockets_connect = AsyncMock(return_value=websocket)
    monkeypatch.setattr(websockets, 'connect', websockets_connect)
    websocket_list = WebSocketList(backend_client, ssl_context)

    await websocket_list.get_ordered_by_ping(cell_id)

    websockets_connect.assert_called_once_with(f"wss://{address}/cmsocket/", ssl=ssl_context)
    websocket.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_ordered_by_ping_orders_servers_by_ping(backend_client, monkeypatch):
    cell_id = 0
    address_slow = "address_slow"
    address_fast = "address_fast"
    backend_client.get_servers.return_value = [address_slow, address_fast]
    ssl_context = MagicMock()

    websocket = MagicMock()
    websocket.close = AsyncMock()

    async def fake_connect(uri, ssl):
        delays = {
            f"wss://{address_slow}/cmsocket/": 0.1,
            f"wss://{address_fast}/cmsocket/": 0.0,
        }
        delay = delays[uri]
        await sleep(delay)
        return websocket

    websockets_connect = MagicMock(side_effect=fake_connect)
    monkeypatch.setattr(websockets, 'connect', websockets_connect)
    websocket_list = WebSocketList(backend_client, ssl_context)

    servers = await websocket_list.get_ordered_by_ping(cell_id)

    assert servers == [f"wss://{address_fast}/cmsocket/", f"wss://{address_slow}/cmsocket/"]
