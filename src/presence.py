from galaxy.api.consts import PresenceState
from galaxy.api.types import UserPresence

from protocol.consts import EPersonaState
from protocol.types import UserInfo

def from_user_info(user_info: UserInfo) -> UserPresence:
    if user_info.state == EPersonaState.Online:
        state = PresenceState.Online
    elif user_info.state == EPersonaState.Offline:
        state = PresenceState.Offline
    elif user_info.state == EPersonaState.Away:
        state = PresenceState.Away
    elif user_info.state == EPersonaState.Busy:
        state = PresenceState.Away
    else:
        state = PresenceState.Unknown

    game_id = str(user_info.game_id) if user_info.game_id is not None and user_info.game_id != 0 else None

    game_title = user_info.game_name if user_info.game_name is not None and user_info.game_name else None

    status = None
    if user_info.rich_presence is not None:
        status = user_info.rich_presence.get("status")

    return UserPresence(
        presence_state=state,
        game_id=game_id,
        game_title=game_title,
        in_game_status=status
    )
