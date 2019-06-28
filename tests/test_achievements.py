import asyncio
from datetime import datetime, timezone
from unittest.mock import call

from galaxy.api.types import Achievement
from galaxy.api.errors import AuthenticationRequired, BackendError
import pytest

import serialization
from backend import SteamHttpClient
from cache import Cache

async def wait_for_tasks():
    """wait until all tasks are finished"""
    for _ in range(4):
        await asyncio.sleep(0)

@pytest.fixture()
def import_success(authenticated_plugin, mocker):
    return mocker.patch.object(authenticated_plugin, "game_achievements_import_success")

@pytest.fixture()
def import_failure(authenticated_plugin, mocker):
    return mocker.patch.object(authenticated_plugin, "game_achievements_import_failure")

@pytest.fixture()
def import_finished(authenticated_plugin, mocker):
    return mocker.patch.object(authenticated_plugin, "achievements_import_finished")

@pytest.fixture()
def push_cache(authenticated_plugin, mocker):
    return mocker.patch.object(authenticated_plugin, "push_cache")

@pytest.mark.asyncio
class TestGetUnlockedAchievements:
    async def test_not_authenticated(self, plugin):
        with pytest.raises(AuthenticationRequired):
            await plugin.get_unlocked_achievements("12")

    async def test_no_games(self, authenticated_plugin, backend_client, steam_id):
        backend_client.get_achievements.return_value = []

        game_id = "154"
        result = await authenticated_plugin.get_unlocked_achievements(game_id)
        assert result == []
        backend_client.get_achievements.assert_called_with(steam_id, game_id)

    async def test_multiple_games(self, authenticated_plugin, backend_client, steam_id):
        # only fields important for the logic
        backend_client.get_achievements.return_value = [
            (1551887210, "name 1"),
            (1551887134, "name 2")
        ]

        game_id = "564"
        result = await authenticated_plugin.get_unlocked_achievements(game_id)
        assert result == [
            Achievement(1551887210, None, "name 1"),
            Achievement(1551887134, None, "name 2")
        ]
        backend_client.get_achievements.assert_called_with(steam_id, game_id)


@pytest.mark.asyncio
class TestStartAchievementsImport:
    async def test_not_authenticated(self, plugin):
        with pytest.raises(AuthenticationRequired):
            await plugin.start_achievements_import(["12", "13"])

    async def test_import(self, authenticated_plugin, backend_client, import_success, import_failure, import_finished):
        backend_client.get_games.return_value = [
            {
                "appid": 281990,
                "hours_forever": "1.3",
                "last_played": 1549385500
            },
            {
                "appid": 236850,
                "hours_forever": "1,447",
                "last_played": 1549385500
            }
        ]
        backend_client.get_achievements.side_effect = [
            [
                (1551887210, "name 1"),
                (1551887134, "name 2")
            ],
            BackendError()
        ]
        await authenticated_plugin.start_achievements_import(["281990", "236850"])

        await wait_for_tasks()

        backend_client.get_games.assert_called_once()
        backend_client.get_achievements.call_args_list == [call("281990"), call("236850")]
        import_success.assert_called_once_with(
            "281990",
            [
                Achievement(1551887210, None, "name 1"),
                Achievement(1551887134, None, "name 2")
            ]
        )
        import_failure.assert_called_once_with("236850", BackendError())
        import_finished.assert_called_once_with()

    async def test_push_cache(self, authenticated_plugin, backend_client, push_cache):
        backend_client.get_games.return_value = [
            {
                "appid": 17923,
                "hours_forever": "3",
                "last_played": 1549385501
            }
        ]
        backend_client.get_achievements.return_value = [(1549383000, "name")]
        await authenticated_plugin.start_achievements_import(["17923"])
        await wait_for_tasks()
        push_cache.assert_called_once_with()

    async def test_valid_cache(self, authenticated_plugin, backend_client, import_success, import_finished, push_cache):
        backend_client.get_games.return_value = [
            {
                "appid": 17923,
                "hours_forever": "3",
                "last_played": 1549385501
            }
        ]
        backend_client.get_achievements.return_value = [(1549383000, "name")]
        await authenticated_plugin.start_achievements_import(["17923"])
        await wait_for_tasks()
        assert backend_client.get_games.call_count == 1
        assert backend_client.get_achievements.call_count == 1
        assert import_success.call_count == 1
        assert import_finished.call_count == 1
        assert push_cache.call_count == 1

        await authenticated_plugin.start_achievements_import(["17923"])
        await wait_for_tasks()
        assert backend_client.get_games.call_count == 2
        assert backend_client.get_achievements.call_count == 1 # no new calls to backend
        assert import_success.call_count == 2
        assert import_finished.call_count == 2

        assert push_cache.call_count == 1

    async def test_invalid_cache(self, authenticated_plugin, backend_client, import_success, import_finished, push_cache):
        backend_client.get_games.return_value = [
            {
                "appid": 17923,
                "hours_forever": "3",
                "last_played": 1549385501
            }
        ]
        backend_client.get_achievements.return_value = [(1549383000, "name")]
        await authenticated_plugin.start_achievements_import(["17923"])
        await wait_for_tasks()
        import_success.reset_mock()

        backend_client.get_games.return_value = [
            {
                "appid": 17923,
                "hours_forever": "3",
                "last_played": 1549385600
            }
        ]
        backend_client.get_achievements.return_value = [
            (1549383000, "name"),
            (1549385599, "namee")
        ]
        await authenticated_plugin.start_achievements_import(["17923"])
        await wait_for_tasks()
        import_success.assert_called_once_with(
            "17923",
            [
                Achievement(1549383000, None, "name"),
                Achievement(1549385599, None, "namee")
            ]
        )

    async def test_initialize_cache(self, create_authenticated_plugin, backend_client, steam_id, login, mocker):
        achievements_cache = Cache()
        achievements_cache.update("17923", [Achievement(1549383000, None, "name")], 1549385501)
        cache = {
            "achievements": serialization.dumps(achievements_cache)
        }
        plugin = await create_authenticated_plugin(steam_id, login, cache)
        import_success = mocker.patch.object(plugin, "game_achievements_import_success")
        import_finished = mocker.patch.object(plugin, "achievements_import_finished")

        backend_client.get_games.return_value = [
            {
                "appid": 17923,
                "hours_forever": "3",
                "last_played": 1549385501
            }
        ]
        await plugin.start_achievements_import(["17923"])
        await wait_for_tasks()
        assert backend_client.get_games.call_count == 1
        assert backend_client.get_achievements.call_count == 0
        import_success.assert_called_once_with(
            "17923",
            [
                Achievement(1549383000, None, "name")
            ]
        )
        assert import_finished.call_count == 1

    async def test_get_games_failure(self, authenticated_plugin, backend_client, import_failure, import_finished):
        error = BackendError()
        backend_client.get_games.side_effect = error

        await authenticated_plugin.start_achievements_import(["281990", "236850"])

        # wait until all tasks are finished
        await asyncio.sleep(0)

        expected_notifications = [
            call("281990", error),
            call("236850", error)
        ]
        import_failure.assert_has_calls(expected_notifications, any_order=True)
        import_finished.assert_called_with()

    async def test_no_game_time(self, authenticated_plugin, backend_client, import_success, import_finished):
        backend_client.get_games.return_value = []
        await authenticated_plugin.start_achievements_import(["281990"])

        await wait_for_tasks()

        backend_client.get_games.assert_called_once()
        import_success.assert_called_once_with("281990", [])
        import_finished.assert_called_once_with()

    async def test_zero_game_time(self, authenticated_plugin, backend_client, import_success, import_finished):
        backend_client.get_games.return_value = [
            {
                "appid": 17923,
                "hours_forever": "0",
                "last_played": 1549385501
            }
        ]
        await authenticated_plugin.start_achievements_import(["17923"])

        await wait_for_tasks()

        backend_client.get_games.assert_called_once()
        import_success.assert_called_once_with("17923", [])
        import_finished.assert_called_once_with()


@pytest.mark.parametrize("input_time, parsed_date", [
    ("Unlocked 22 Jan @ 12:12am", datetime(datetime.utcnow().year, 1, 22, 0, 12, tzinfo=timezone.utc)),
    ("Unlocked 9 Jun, 2017 @ 11:35pm", datetime(2017, 6, 9, 23, 35, tzinfo=timezone.utc)),
])
def test_unlock_time_parsing(input_time, parsed_date):
    assert parsed_date == SteamHttpClient.parse_date(input_time)