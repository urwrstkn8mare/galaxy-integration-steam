from unittest.mock import MagicMock

import pytest
from galaxy.unittest.mock import AsyncMock

from protocol.protobuf_client import ProtobufClient


ACCOUNT_NAME = "john"
PASSWORD = "testing123"
TWO_FACTOR = "AbCdEf"
TOKEN = "TOKEN"
USED_SERVER_CELL_ID = 0
MACHINE_ID = bytes('machine_id', 'utf-8')
OS_VALUE = 1
SENTRY = None
PRIVATE_IP = 1
HOST_NAME = "john pc"
PROTOCOL_VERSION = ProtobufClient._MSG_PROTOCOL_VERSION
CLIENT_PACKAGE_VERSION = ProtobufClient._MSG_CLIENT_PACKAGE_VERSION
CLIENT_LANGUAGE = "english"
TWO_FACTOR_TYPE = 'email'


@pytest.fixture
def websocket():
    websocket_ = MagicMock()
    websocket_.send = AsyncMock()
    return websocket_


@pytest.fixture
async def client(websocket, mocker):
    protobuf_client = ProtobufClient(websocket)
    protobuf_client._get_obfuscated_private_ip = MagicMock(return_value=PRIVATE_IP)
    mocker.patch(
        "socket.gethostname", return_value=HOST_NAME
    )
    return protobuf_client


@pytest.mark.asyncio
async def test_log_on_token_message(client, websocket):
    await client.log_on_token(ACCOUNT_NAME, TOKEN, USED_SERVER_CELL_ID, MACHINE_ID, OS_VALUE, SENTRY)
    msg_to_send = str(websocket.send.call_args[0][0])
    assert ACCOUNT_NAME in msg_to_send
    assert TOKEN in msg_to_send
    assert str(USED_SERVER_CELL_ID) in msg_to_send
    assert MACHINE_ID.decode('utf-8') in msg_to_send
    assert str(OS_VALUE) in msg_to_send
    assert str(PRIVATE_IP) in msg_to_send
    assert HOST_NAME in msg_to_send
    assert CLIENT_LANGUAGE in msg_to_send


@pytest.mark.asyncio
async def test_log_on_password_message(client, websocket):
    await client.log_on_password(ACCOUNT_NAME, PASSWORD, TWO_FACTOR, TWO_FACTOR_TYPE, MACHINE_ID,OS_VALUE, SENTRY)
    msg_to_send = str(websocket.send.call_args[0][0])
    assert ACCOUNT_NAME in msg_to_send
    assert str(USED_SERVER_CELL_ID) in msg_to_send
    assert MACHINE_ID.decode('utf-8') in msg_to_send
    assert str(OS_VALUE) in msg_to_send
    assert str(PRIVATE_IP) in msg_to_send
    assert HOST_NAME in msg_to_send
    assert CLIENT_LANGUAGE in msg_to_send
    assert TWO_FACTOR in msg_to_send
