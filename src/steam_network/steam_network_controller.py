from .steam_network_model import SteamNetworkModel
from .steam_network_view import SteamNetworkView


class SteamNetworkController:
    def __init__(self) -> None:
        self._model = SteamNetworkModel()
        self._view = SteamNetworkView()
        pass

    """Acts as the middle-man between GOG and Steam. 
    
    This includes standard MVC with the user during the login process as well as sending/retrieving game data between GOG and Steam.

    This replaces the old BackendSteamNetwork. 
    """
    pass

    def handshake_complete(self):
        logger.info("Handshake complete")