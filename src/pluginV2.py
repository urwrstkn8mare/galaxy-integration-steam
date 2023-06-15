import platform
import asyncio
import logging
import traceback
import sys

from typing import Dict, List, Any, AsyncGenerator, Union, Optional


from galaxy.api.types import Game, Subscription, SubscriptionGame, Achievement, NextStep, Authentication, GameTime, UserPresence, GameLibrarySettings, UserInfo
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.consts import Platform


from .version import __version__


def is_windows():
    return platform.system().lower() == "windows"


class SteamPlugin(Plugin):
    """Class that implements the steam plugin in a way that GOG Galaxy recognizes.

    Functionality is implemented by implementing abstract functions defined in the Plugin class from the galaxy api. All functions are called from GOG Galaxy Client unless specified otherwise.
    Functionality that requires communication with Steam is handled by a dedicated SteamNetworkController instance within this class. 
    Functionality that interacts with the user's operating system, such as install size, launching a game, etc are handled in this class directly. 

    Background tasks are responsible for obtaining and caching information that GOG Galaxy Client will use in the future, but is not currently requesting. Steam occasionally gives us updates without us asking for them.
    """
    def __init__(self, reader, writer, token):
        super().__init__(Platform.Steam, __version__, reader, writer, token)

    #features are normally auto-detected. Since we only support one form of login, we can allow this behavior. 


    #region startup, login, and shutdown

    def handshake_complete(self):
        """ Called when the handshake between GOG Galaxy Client and this plugin has completed. 

        This means that GOG Galaxy Client recognizes our plugin and is communicating with us.
        Any initialization required on the client that is necessary for the plugin to work is now complete.
        This means things like the persistent cache are now available to us.
        """
        pass
    
    async def authenticate(self, stored_credentials : Dict[str, Any] = None) -> Union[Authentication, NextStep]:
        """ Called when the plugin attempts to log the user in. This occurs at the start, after the handshake.
 
        stored_credentials are a mapping of a name to data of any type that were saved from previous session(s)
        Returns either an Authentication object, which represents a successfuly login (from stored credentials) \
or a NextStep object, which tells GOG to display a webpage with the information necessary to get further login information from the user.
        """
        pass

    async def pass_login_credentials(self, _ : str, credentials: Dict[str, str], cookies : List[Dict[str, str]]):
        """ Called when a webpage generated from a NextStep object completes.
        
        this function contains an unused string that is deprecated. it's value is not defined. 
        credentials contain the URL Parameters obtained from the end uri that caused the webpage to complete as a tuple of name and value.
        cookies is a list of cookies that may have been saved and available to the end uri. A cookie is a collection of tuples of name and value.

        Returns either an Authentication object, which represents a successfuly login or a NextStep object, \
with a new webpage to display, in the event the user improperly input their information, or needs to provide additional information such as 2FA.

        This function may be called multiple times when the user is logging in, depending on 2FA or failed login attempts.
        """
        pass


    async def shutdown(self):
        """Called when the plugin is removed from GOG Galaxy. 
        
        This is a more extreme form of close, as we are expected to disable any extra things we needed to do to make the connection that aren't removed by clearing the cache.
        For this code, this means revoking our token so it cannot be used to log in anymore. 
        """
        pass

    #endregion End startup, login, and shutdown. 

    #region owned games and subscriptions
    async def get_owned_games(self) -> List[Game]:
        """ Get a list of games the user currently owns. 

        This is synchronous and blocking. I'm not sure why.
        """
        pass

    async def get_subscriptions(self) -> List[Subscription]:
        """ Get a list of subscriptions sources the user currently subscribes to. This is not the games themselves. 

        This is just the steam family share as far as i can tell. 
        """
        pass

    async def prepare_subscription_games_context(self, subscription_names: List[str]) -> None:
        """ Start a batch process to get all subscription games for the list of available subscription sources.

        For Steam, there is only one source of subscriptions: Steam Family Share. This is the only one we need to process.
        Steam has one call that obtains all games at once, whether they are owned or subscription; however, it does tell us which a given game is.
        Preparing for subscription games will also begin preparing for owned games, and vice versa. \
If preparations for one of these functions has been started when the other is called, this call will have no effect.
        """
        pass
    #note to self, raise StopIterator to kill a generator. there is no "yield break" in python.
    
    async def get_subscription_games(self, subscription_name: str, context: None) -> AsyncGenerator[List[SubscriptionGame], None]:
        """ Get a list of games asynchronously that the user has subscribed to.
        
        If the string is not "Steam Family Share" this value will return nothing. Context is unused. 
        """

    def subscription_games_import_complete(self):
        """ Updates all the imported games so they are written to the database cache.

        This is called after all subscription games are successfully imported. 
        """
        pass

    #endregion
    #region Achievements

    #as of this writing, there is no way to batch import achievements for multiple games. so this function does not add any functionality and actually bottlenecks the code. 
    #this is therefore unused. Should this ever change, the logic can be optimized by retrieving that info here and then caching it so the get_unlocked_achievements does not do anything.
    #async def prepare_achievements_context(self, game_ids: List[str]) -> Any:

    #as of this writing, prepare_achievements_context is not overridden and therefore returns None. That result is then passed in here, so the value here is also None.
    async def get_unlocked_achievements(self, game_id: str, context: None) -> List[Achievement]:
        """Get the unlocked achievements for the provided game id. 

        Games are imported one at a time because a batch import does not exist. Context is therefore None here. 
        """
        pass


    def achievements_import_complete(self):
        """Called when get_unlocked_achievements has been called on all game_ids. Normally, 
        """
        pass
    #endregion
    #region Play Time
    async def prepare_game_times_context(self, game_ids: List[str]) -> Any:
        pass

    async def get_game_time(self, game_id: str, context: Dict[int, int]) -> GameTime:
        pass

    def game_times_import_complete(self):
        pass
    #endregion
    #region User-defined settings applied to their games
    async def prepare_game_library_settings_context(self, game_ids: List[str]) -> Any:
        pass

    async def get_game_library_settings(self, game_id: str, context: Any) -> GameLibrarySettings:
        pass

    def game_library_settings_import_complete(self):
        pass
    #endregion
    #region friend info
    async def get_friends(self) -> List[UserInfo]:
        pass

    async def prepare_user_presence_context(self, user_ids: List[str]) -> Any:
        pass

    async def get_user_presence(self, user_id: str, context: Any) -> UserPresence:
        pass

    def user_presence_import_complete(self):
        pass
    #endregion
    
    



    

    def tick(self):
        pass

    #region get info about and/or update games on local system:

    async def get_local_games(self):
        pass

    async def install_game(self, game_id : str):
        pass

    async def uninstall_game(self, game_id:str):
        pass

    async def prepare_local_size_context(self, game_ids: List[str]) -> Dict[str, str]:
        pass

    async def get_local_size(self, game_id: str, context: Dict[str, str]) -> Optional[int]:
        """ Returns the amount of space, in bytes, the game specificed by the game_id takes up on user storage. If it cannot be determined, returns None.

        This is called by the GOG Galaxy client. 
        """

    #endregion get info about and/or update games on local system:

    #region launching/closing games.

    async def launch_game(self, game_id: str):
        """ Launches the steam game with the given steam id.

        This is called by the GOG Galaxy client
        """
        pass

    async def shutdown_platform_client(self) -> None:
        """
        Shuts down the steam client. Launched automatically when a game starts, but can closed on game exit, depending on user settings.

        This is called by the GOG Galaxy client. 
        """
        pass
    #endregion

def main():
    """ Program entry point. starts the entire plugin. 
    
    Usually not necessary because we are a plugin, but useful for testing
    """
    create_and_run_plugin(SteamPlugin, sys.argv)

#subprocessess check. clever! necessary for parallel processing on windows since it doesn't have "fork"
if __name__ == "__main__":
    main()