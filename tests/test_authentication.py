
import pytest

from unittest.mock import MagicMock
from user_info_cache import UserInfoCache
from galaxy.unittest.mock import AsyncMock
from protocol.websocket_client import UserActionRequired
from galaxy.api.types import Authentication

_STEAM_ID = 123
_ACCOUNT_ID = 23
_ACCOUNT_USERNAME = "😋学中文Не́кот"
_PERSONA_NAME = "Ptester"
_TOKEN = "token"
_SENTRY = b""

serialized_creds = {'steam_id': 'MTIz', 'account_id': 'MjM=', 'token': 'dG9rZW4=',
                    'account_username': '8J+Yi+WtpuS4reaWh9Cd0LXMgdC60L7Rgg==', 'persona_name': 'UHRlc3Rlcg==',
                    'sentry': ''}


@pytest.mark.asyncio
async def test_credentials_cache_store():
    user_info_cache = UserInfoCache()
    user_info_cache.steam_id = _STEAM_ID
    user_info_cache.account_id = _ACCOUNT_ID
    user_info_cache.account_username = _ACCOUNT_USERNAME
    user_info_cache.persona_name = _PERSONA_NAME
    user_info_cache.token = _TOKEN

    assert user_info_cache.initialized.is_set()
    assert serialized_creds == user_info_cache.to_dict()


@pytest.mark.asyncio
async def test_credentials_cache_load():
    user_info_cache = UserInfoCache()
    user_info_cache.from_dict(serialized_creds)

    assert user_info_cache.steam_id == _STEAM_ID
    assert user_info_cache.account_id == _ACCOUNT_ID
    assert user_info_cache.account_username == _ACCOUNT_USERNAME
    assert user_info_cache.persona_name == _PERSONA_NAME
    assert user_info_cache.token == _TOKEN
    assert user_info_cache.sentry == b""


@pytest.mark.asyncio
async def test_login_finished(authenticated_plugin):
    credentials = {}
    credentials['end_uri'] = 'login_finished?username=abc&password=cba'

    plugin_queue_mock = AsyncMock()
    websocket_queue_mock = AsyncMock()
    websocket_queue_mock.get.return_value = MagicMock()
    error_queue_mock = AsyncMock()
    error_queue_mock.get.return_value = MagicMock()
    authenticated_plugin._steam_client.communication_queues = {'plugin': plugin_queue_mock, 'websocket': websocket_queue_mock,
                                   'errors': error_queue_mock}

    authenticated_plugin._get_websocket_auth_step = AsyncMock()
    authenticated_plugin._get_websocket_auth_step.return_value = UserActionRequired.NoActionRequired

    authenticated_plugin.store_credentials = MagicMock()
    authenticated_plugin._user_info_cache = MagicMock()

    assert isinstance(await authenticated_plugin.pass_login_credentials("", credentials, {}), Authentication)
    authenticated_plugin._get_websocket_auth_step.assert_called()
    authenticated_plugin.store_credentials.assert_called()


@pytest.mark.asyncio
async def test_login_two_step(authenticated_plugin):
    credentials = {}
    credentials['end_uri'] = 'two_factor_mobile_finished?code=abc'

    plugin_queue_mock = AsyncMock()
    websocket_queue_mock = AsyncMock()
    websocket_queue_mock.get.return_value = MagicMock()
    error_queue_mock = AsyncMock()
    error_queue_mock.get.return_value = MagicMock()
    authenticated_plugin._steam_client.communication_queues = {'plugin': plugin_queue_mock, 'websocket': websocket_queue_mock,
                                   'errors': error_queue_mock}

    authenticated_plugin._auth_data = MagicMock()

    authenticated_plugin._get_websocket_auth_step = AsyncMock()
    authenticated_plugin._get_websocket_auth_step.return_value = UserActionRequired.NoActionRequired

    authenticated_plugin.store_credentials = MagicMock()
    authenticated_plugin._user_info_cache = MagicMock()

    assert isinstance(await authenticated_plugin.pass_login_credentials("", credentials, {}), Authentication)
    authenticated_plugin._get_websocket_auth_step.assert_called()
    authenticated_plugin.store_credentials.assert_called()