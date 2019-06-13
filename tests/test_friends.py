from backend import SteamHttpClient
from galaxy.api.types import FriendInfo
from galaxy.api.errors import AuthenticationRequired
from tests.async_mock import AsyncMock, MagicMock
import pytest


@pytest.mark.asyncio
async def test_not_authenticated(plugin):
    with pytest.raises(AuthenticationRequired):
        await plugin.get_friends()


@pytest.mark.asyncio
async def test_no_friends(authenticated_plugin, backend_client, steam_id):
    backend_client.get_friends.return_value = {}

    assert [] == await authenticated_plugin.get_friends()
    backend_client.get_friends.assert_called_once_with(steam_id)


@pytest.mark.asyncio
async def test_multiple_friends(authenticated_plugin, backend_client, steam_id):
    backend_client.get_friends.return_value = {
        "76561198040630463": "crak",
        "76561198053830887": "Danpire"
    }

    result = await authenticated_plugin.get_friends()
    assert result == [
        FriendInfo("76561198040630463", "crak"),
        FriendInfo("76561198053830887", "Danpire")
    ]
    backend_client.get_friends.assert_called_once_with(steam_id)


@pytest.fixture
def http_response_mock():
    mock = MagicMock(spec=())
    mock.text = AsyncMock()
    return mock


@pytest.fixture
def http_client_mock():
    mock = MagicMock(spec=())
    mock.get = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_profile_parsing(http_client_mock, http_response_mock, steam_id):
    http_response_mock.text.return_value = '''
    <div class="profile_friends search_results" id="search_results">
        <div class="selectable friend_block_v2 persona offline " data-steamid="76561198056089614">
            <div class="friend_block_content">На камазе!<br>
                <span class="friend_small_text"></span>
                <span class="friend_last_online_text">Last Online 189 days ago</span>
            </div>
        </div>
    </div>'''
    http_client_mock.get.return_value = http_response_mock

    assert {"76561198056089614": "На камазе!"} == await SteamHttpClient(http_client_mock).get_friends(steam_id)
