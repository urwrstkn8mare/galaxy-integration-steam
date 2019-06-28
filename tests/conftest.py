from unittest.mock import MagicMock

import pytest

from plugin import SteamPlugin

from tests.async_mock import AsyncMock

@pytest.fixture
def backend_client():
    mock = MagicMock(spec=())
    mock.get_profile = AsyncMock()
    mock.get_profile_data = AsyncMock()
    mock.get_games = AsyncMock()
    mock.get_achievements = AsyncMock()
    mock.get_friends = AsyncMock()
    mock.set_cookie_jar = MagicMock()
    mock.set_auth_lost_callback = MagicMock()
    mock.set_cookies_updated_callback = MagicMock()
    return mock

@pytest.fixture()
async def create_plugin(backend_client, mocker):
    created_plugins = []
    def function():
        mocker.patch("plugin.SteamHttpClient", return_value=backend_client)
        plugin = SteamPlugin(MagicMock(), MagicMock(), None)
        created_plugins.append(plugin)
        return plugin

    yield function

    for plugin in created_plugins:
        plugin.shutdown()

@pytest.fixture()
async def plugin(create_plugin):
    return create_plugin()

@pytest.fixture()
def steam_id():
    return "156"

@pytest.fixture()
def login():
    return "tester"

@pytest.fixture()
async def create_authenticated_plugin(create_plugin, backend_client, mocker):
    async def function(steam_id, login, cache):
        mocker.patch.object(SteamPlugin, "persistent_cache", new_callable=mocker.PropertyMock, return_value=cache)
        plugin = create_plugin()
        backend_client.get_profile.return_value = "http://url"
        backend_client.get_profile_data.return_value = steam_id, login
        credentials = {
            "cookies": [
                {
                    "name": "cookie",
                    "value": "value",
                    "domain": "steamcommunity.com",
                    "path": "/"
                }
            ]
        }
        plugin.handshake_complete()
        await plugin.authenticate(credentials)

        return plugin

    return function

@pytest.fixture()
async def authenticated_plugin(create_authenticated_plugin, steam_id, login):
    return await create_authenticated_plugin(steam_id, login, {})
