import asyncio
from unittest.mock import call

from galaxy.api.types import GameTime
from galaxy.api.errors import AuthenticationRequired, BackendError, UnknownError
import pytest

async def wait_for_tasks():
    """wait until all tasks are finished"""
    for _ in range(4):
        await asyncio.sleep(0)

@pytest.fixture()
def import_success(authenticated_plugin, mocker):
    return mocker.patch.object(authenticated_plugin, "game_time_import_success")

@pytest.fixture()
def import_failure(authenticated_plugin, mocker):
    return mocker.patch.object(authenticated_plugin, "game_time_import_failure")

@pytest.fixture()
def import_finished(authenticated_plugin, mocker):
    return mocker.patch.object(authenticated_plugin, "game_times_import_finished")


@pytest.mark.asyncio
class TestGetGameTimes:
    async def test_not_authenticated(self, plugin):
        with pytest.raises(AuthenticationRequired):
            await plugin.get_game_times()

    async def test_no_games(self, authenticated_plugin, backend_client, steam_id):
        backend_client.get_games.return_value = []

        result = await authenticated_plugin.get_game_times()
        assert result == []
        backend_client.get_games.assert_called_with(steam_id)

    @pytest.mark.parametrize("backend_response, result", [
        (
            {
                "appid": 281990,
                "hours_forever": "1.3",
                "last_played": 1549385500
            },
            GameTime("281990", 78, 1549385500)
        ),
        (
            {
                "appid": 610080,
                "hours_forever": "1,447",
                "last_played": 1549385500
            },
            GameTime("610080", 86820, 1549385500)
        )
    ])
    async def test_game_time(self, authenticated_plugin, backend_client, steam_id, backend_response, result):
        # only fields important for the logic
        backend_client.get_games.return_value = [backend_response]

        assert [result] == await authenticated_plugin.get_game_times()

        backend_client.get_games.assert_called_with(steam_id)

    async def test_no_game_time(self, authenticated_plugin, backend_client, steam_id):
        # only fields important for the logic
        backend_client.get_games.return_value = [
            {
                "appid": 281990,
                "last_played": 1549385500
            }
        ]

        result = await authenticated_plugin.get_game_times()
        assert result == [
            GameTime("281990", 0, 1549385500)
        ]
        backend_client.get_games.assert_called_with(steam_id)


@pytest.mark.asyncio
class TestStartGameTimesImport:
    async def test_not_authenticated(self, plugin):
        with pytest.raises(AuthenticationRequired):
            await plugin.start_game_times_import(["13", "23"])

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
        await authenticated_plugin.start_game_times_import(["281990", "236850"])

        await wait_for_tasks()

        backend_client.get_games.assert_called_once()
        expected_notifications = [
            call(GameTime("281990", 78, 1549385500)),
            call(GameTime("236850", 86820, 1549385500))
        ]
        import_success.assert_has_calls(expected_notifications, any_order=True)
        import_finished.assert_called_once_with()

    async def test_get_games_failure(self, authenticated_plugin, backend_client, import_failure, import_finished):
        error = BackendError()
        backend_client.get_games.side_effect = error

        await authenticated_plugin.start_game_times_import(["281990", "236850"])

        # wait until all tasks are finished
        await asyncio.sleep(0)

        expected_notifications = [
            call("281990", error),
            call("236850", error)
        ]
        import_failure.assert_has_calls(expected_notifications, any_order=True)
        import_finished.assert_called_with()

    async def test_missing_game_time(self, authenticated_plugin, backend_client, import_failure, import_finished):
        backend_client.get_games.return_value = []

        await authenticated_plugin.start_game_times_import(["281990"])

        # wait until all tasks are finished
        await asyncio.sleep(0)

        import_failure.assert_called_once_with("281990", UnknownError())
        import_finished.assert_called_once_with()
