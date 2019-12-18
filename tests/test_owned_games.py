from galaxy.api.types import Game, LicenseInfo
from galaxy.api.consts import LicenseType
from galaxy.api.errors import AuthenticationRequired
from galaxy.unittest.mock import AsyncMock
from unittest.mock import MagicMock
import pytest

@pytest.mark.asyncio
async def test_not_authenticated(plugin):
    with pytest.raises(AuthenticationRequired):
        await plugin.get_owned_games()

@pytest.mark.asyncio
async def test_no_games(authenticated_plugin, backend_client, miniprofile):
    backend_client.get_owned_ids.return_value = []
    authenticated_plugin._games_cache = MagicMock()
    authenticated_plugin._games_cache.__iter__.return_value = [(281990, "Stellaris"), (236850, "Europa Universalis IV")]
    authenticated_plugin._games_cache.wait_ready = AsyncMock()
    result = await authenticated_plugin.get_owned_games()
    assert result == []
    backend_client.get_owned_ids.assert_called_with(miniprofile)

@pytest.mark.asyncio
async def test_multiple_games(authenticated_plugin, backend_client, miniprofile):
    # only fields important for the logic
    backend_client.get_owned_ids.return_value = [
        281990,
        236850,
    ]

    authenticated_plugin._games_cache = MagicMock()
    authenticated_plugin._games_cache.__iter__.return_value = [(281990, "Stellaris"), (236850, "Europa Universalis IV")]
    authenticated_plugin._games_cache.wait_ready = AsyncMock()
    result = await authenticated_plugin.get_owned_games()
    assert result == [
        Game("281990", "Stellaris", [], LicenseInfo(LicenseType.SinglePurchase, None)),
        Game("236850", "Europa Universalis IV", [], LicenseInfo(LicenseType.SinglePurchase, None))
    ]
    backend_client.get_owned_ids.assert_called_with(miniprofile)
