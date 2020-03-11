from galaxy.api.consts import PresenceState
from galaxy.api.types import UserPresence

from protocol.consts import EPersonaState
from protocol.types import ProtoUserInfo

import logging
logger = logging.getLogger(__name__)

def _translate_string(game_id, string, translations_cache):
    token_list = translations_cache[int(game_id)]
    for token in token_list.tokens:
        if token.name == string:
            return token.value

def presence_from_user_info(user_info: ProtoUserInfo, translations_cache: dict) -> UserPresence:
    if user_info.state == EPersonaState.Online:
        state = PresenceState.Online
    elif user_info.state == EPersonaState.Snooze:
        # In game afk, sitting in the main menu etc. Steam chat and others show this as online/in-game
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
        if status and status[0] == "#":
            if int(game_id) in translations_cache:
                status = _translate_string(game_id, status, translations_cache)
                num_params = user_info.rich_presence.get("num_params")
                if num_params and int(num_params) > 0:
                    for param in range(0, int(num_params)):
                        param_string = user_info.rich_presence.get(f"param{param}")
                        if param_string and param_string[0] == "#":
                            param_string = _translate_string(game_id, param_string, translations_cache)
                        presence_substring = f"%param{param}%"
                        status = status.replace("{"+presence_substring+"}", param_string)
                        status = status.replace(presence_substring, param_string)

            else:
                logger.info(f"Skipping not simple rich presence status {status}")
                status = None

    return UserPresence(
        presence_state=state,
        game_id=game_id,
        game_title=game_title,
        in_game_status=status
    )
