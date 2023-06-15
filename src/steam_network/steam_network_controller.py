from typing import Optional, Dict

from .caches.user_info_cache import UserInfoCache
from .steam_network_model import SteamNetworkModel
from .steam_network_view import SteamNetworkView


class SteamNetworkController:
    def __init__(self) -> None:
        self._model = SteamNetworkModel()
        self._view = SteamNetworkView()
        pass

    """Acts as the middle-man between GOG and Steam. 
    
    This includes standard MVC with the user during the login process as well as sending/retrieving game data between GOG and Steam.

    This replaces the old BackendSteamNetwork. This does not handle data that does not need to be retrieved from the user or Steam, such as launching games, checking install sizes, etc.
    """
    pass

    def handshake_complete(self):

        logger.info("Handshake complete")

    def check_stored_credentials_changed(): Optional[Dict[str, str]]
        """
        Check if the stored credentials have changed since the last time this was called. 
        
        If so, returns the User Info Cache as a Dictionary so it can be written to the cache. If not, returns None
        This function is used by the tick function to periodically update the user information stored in the database. 
        """