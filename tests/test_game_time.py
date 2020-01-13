from galaxy.api.types import GameTime
from galaxy.api.errors import AuthenticationRequired
import pytest


@pytest.mark.asyncio
async def test_not_authenticated(plugin):
    with pytest.raises(AuthenticationRequired):
        await plugin.prepare_game_times_context(["13", "23"])


@pytest.mark.asyncio
async def test_import(authenticated_plugin, backend_client):
    authenticated_plugin._stats_cache = {"281990": {'time': 78}, "236850": {'time': 86820}}
    assert await authenticated_plugin.get_game_time("281990",None) == GameTime("281990", 78, None)
    assert await authenticated_plugin.get_game_time("236850",None) == GameTime("236850", 86820, None)


@pytest.mark.asyncio
async def test_missing_game_time(authenticated_plugin, backend_client):
    game_time = await authenticated_plugin.get_game_time("281990", None)
    assert game_time == GameTime("281990",None,None)
