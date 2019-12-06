import pytest

from protocol.consts import EPersonaState
from protocol.types import UserInfo
from presence import from_user_info

from galaxy.api.errors import AuthenticationRequired, UnknownError
from galaxy.api.consts import PresenceState
from galaxy.api.types import UserPresence


@pytest.mark.parametrize(
    "user_info,user_presence",
    [
        # Empty
        (
                UserInfo(),
                UserPresence(presence_state=PresenceState.Unknown)
        ),
        # Offline
        (
                UserInfo(state=EPersonaState.Offline),
                UserPresence(presence_state=PresenceState.Offline)
        ),
        # User online not playing a game
        (
                UserInfo(state=EPersonaState.Online, game_id=0, game_name="", rich_presence={}),
                UserPresence(presence_state=PresenceState.Online, game_id=None, game_title=None, in_game_status=None)
        ),
        # User online playing a game
        (
                UserInfo(state=EPersonaState.Online, game_id=1512, game_name="abc", rich_presence={"status": "menu"}),
                UserPresence(
                    presence_state=PresenceState.Online, game_id="1512", game_title="abc", in_game_status="menu"
                )
        )
    ]
)
def test_from_user_info(user_info, user_presence):
    assert from_user_info(user_info) == user_presence


CONTEXT = {
    "76561198040630463": UserInfo(name="John", state=EPersonaState.Offline),
    "76561198053830887": UserInfo(name="Jan", state=EPersonaState.Online, game_id=124523113)
}

@pytest.mark.asyncio
async def test_not_authenticated(plugin):
    with pytest.raises(AuthenticationRequired):
        await plugin.get_friends()


@pytest.mark.asyncio
async def test_prepare_user_presence_context(authenticated_plugin, steam_client):
    steam_client.get_friends_info.return_value = CONTEXT
    assert await authenticated_plugin.prepare_user_presence_context(
        ["76561198040630463", "76561198053830887"]
    ) == CONTEXT
    steam_client.get_friends_info.assert_called_once_with(["76561198040630463", "76561198053830887"])


@pytest.mark.asyncio
async def test_get_user_presence_success(authenticated_plugin, steam_client):
    presence = await authenticated_plugin.get_user_presence("76561198040630463", CONTEXT)
    assert presence == UserPresence(presence_state=PresenceState.Offline)

    presence = await authenticated_plugin.get_user_presence("76561198053830887", CONTEXT)
    assert presence == UserPresence(presence_state=PresenceState.Online, game_id="124523113")


@pytest.mark.asyncio
async def test_get_user_presence_not_friend(authenticated_plugin, steam_client):
    with pytest.raises(UnknownError):
        await authenticated_plugin.get_user_presence("123151", {})
