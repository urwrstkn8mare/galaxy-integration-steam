from datetime import datetime, timezone

import pytest
from galaxy.api.types import Achievement
from galaxy.api.errors import AuthenticationRequired

from backend import SteamHttpClient


@pytest.fixture()
def push_cache(authenticated_plugin, mocker):
    return mocker.patch.object(authenticated_plugin, "push_cache")


@pytest.mark.asyncio
async def test_not_authenticated(plugin):
    with pytest.raises(AuthenticationRequired):
        await plugin.prepare_achievements_context(["12", "13"])

@pytest.mark.asyncio
async def test_get_achievements_success(authenticated_plugin, backend_client, steam_id):
    authenticated_plugin._stats_cache = {"236850": {'achievements': [{'unlock_time': 1551887210, 'name': 'name 1'},
                                                                     {'unlock_time': 1551887134, 'name': 'name 2'}]}}
    achievements = await authenticated_plugin.get_unlocked_achievements("236850", None)
    assert achievements == [
            Achievement(1551887210, None, "name 1"),
            Achievement(1551887134, None, "name 2")
        ]

@pytest.mark.asyncio
async def test_initialize_cache(create_authenticated_plugin, backend_client, steam_id, miniprofile, login):

    plugin = await create_authenticated_plugin(steam_id, login,miniprofile,{})
    plugin._stats_cache = {"17923": {'achievements': [{'unlock_time': 123,'name':'name'}]}}
    achievements = await plugin.get_unlocked_achievements("17923", None)
    assert achievements == [
        Achievement(123, None , "name")
    ]
    backend_client.get_achievements.assert_not_called()

@pytest.mark.asyncio
async def test_no_game_time(authenticated_plugin):
    assert await authenticated_plugin.get_unlocked_achievements("17923", None) == []


@pytest.mark.parametrize("input_time, parsed_date", [
    ("Unlocked 22 Jan @ 12:12am", datetime(datetime.utcnow().year, 1, 22, 0, 12, tzinfo=timezone.utc)),
    ("Unlocked Feb 1 @ 12:12am", datetime(datetime.utcnow().year, 2, 1, 0, 12, tzinfo=timezone.utc)),
    ("Unlocked 9 Jun, 2017 @ 11:35pm", datetime(2017, 6, 9, 23, 35, tzinfo=timezone.utc)),
    ("Unlocked Feb 20, 2015 @ 9:24pm", datetime(2015, 2, 20, 21, 24, tzinfo=timezone.utc))
])
def test_unlock_time_parsing(input_time, parsed_date):
    assert parsed_date == SteamHttpClient.parse_date(input_time)

@pytest.mark.asyncio
async def test_trailing_whitespace(authenticated_plugin):
    authenticated_plugin._stats_cache = {"236850": {'achievements': [{'unlock_time': 1551887210, 'name': 'name 1 '},
                                                                     {'unlock_time': 1551887134, 'name': 'name 2    '}]}}
    achievements = await authenticated_plugin.get_unlocked_achievements("236850", None)
    assert achievements == [
        Achievement(1551887210, None, "name 1"),
        Achievement(1551887134, None, "name 2")
    ]
