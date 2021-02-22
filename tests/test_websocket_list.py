import pytest

from websocket_list import WebSocketList


@pytest.mark.asyncio
async def test_get_returns_sockets_received_from_backend_client(backend_client):
    cell_id = 0
    address_1 = "cm2-waw1.cm.teststeam.com:27039"
    address_2 = "cm3-waw3.cm.teststeam.com:27033"
    backend_client.get_servers.return_value = [address_1, address_2]
    websocket_list = WebSocketList(backend_client)

    servers = await websocket_list.get(cell_id)

    assert servers == [f"wss://{address_1}/cmsocket/", f"wss://{address_2}/cmsocket/"]


@pytest.mark.asyncio
async def test_get_queries_list_with_given_cell_id(backend_client):
    cell_id = 1
    address = "cm2-waw1.cm.teststeam.com:27039"
    backend_client.get_servers.return_value = [address]
    websocket_list = WebSocketList(backend_client)

    await websocket_list.get(cell_id)

    backend_client.get_servers.assert_called_once_with(cell_id)
