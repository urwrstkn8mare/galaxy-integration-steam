from unittest.mock import MagicMock

import pytest

from websocket_list import WebSocketList


@pytest.mark.asyncio
async def test_get_ordered_by_ping_returns_single_server(backend_client):
    cell_id = 0
    address = "cm2-waw1.cm.teststeam.com:27039"
    backend_client.get_servers.return_value = [address]
    ssl_context = MagicMock()

    websocket_list = WebSocketList(backend_client, ssl_context)

    servers = await websocket_list.get(cell_id)

    assert len(servers) == 1
    assert servers[0] == f"wss://{address}/cmsocket/"


@pytest.mark.asyncio
async def test_get_ordered_by_ping_queries_list_with_given_cell_id(backend_client):
    cell_id = 1
    address = "cm2-waw1.cm.teststeam.com:27039"
    backend_client.get_servers.return_value = [address]
    ssl_context = MagicMock()
    websocket_list = WebSocketList(backend_client, ssl_context)

    await websocket_list.get(cell_id)

    backend_client.get_servers.assert_called_once_with(cell_id)
