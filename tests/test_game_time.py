from galaxy.api.types import GameTime
from galaxy.api.errors import AuthenticationRequired
import pytest


@pytest.mark.asyncio
async def test_not_authenticated(plugin):
    with pytest.raises(AuthenticationRequired):
        await plugin.prepare_game_times_context(["13", "23"])


@pytest.mark.asyncio
async def test_prepare_game_times_context(authenticated_plugin, backend_client):
    """last played only"""
    backend_client.get_games.return_value = [
        {
            "appid": 281990,
            "hours_forever": "1.3",
            "last_played": 1549385509
        },
        {
            "appid": 236850,
            "hours_forever": "1,447",
            "last_played": 1549385500
        }
    ]
    context = await authenticated_plugin.prepare_game_times_context(["281990", "236850"])
    assert context == {
        "236850": 1549385500,
        "281990": 1549385509
    }

@pytest.mark.asyncio
async def test_import(authenticated_plugin):
    context = {
        "236850": 1549385500,
        "281990": 1549385509
    }
    authenticated_plugin._stats_cache = {"281990": {'time': 78}, "236850": {'time': 86820}}
    assert await authenticated_plugin.get_game_time("236850", context) == GameTime("236850", 86820, 1549385500)
    assert await authenticated_plugin.get_game_time("281990", context) == GameTime("281990", 78, 1549385509)


@pytest.mark.asyncio
async def test_missing_game_time(authenticated_plugin):
    context = {}
    game_time = await authenticated_plugin.get_game_time("281990", context)
    assert game_time == GameTime("281990", None, None)

