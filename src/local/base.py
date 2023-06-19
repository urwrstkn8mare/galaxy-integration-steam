import glob
from itertools import count
from logging import getLogger
import os
from typing import Iterable, List, Optional
from galaxy.api.types import LocalGame, LocalGameState

from .shared import load_vdf

log = getLogger(__name__)


class BaseClient:

    @staticmethod
    def get_app_states_from_registry(app_dict):
        app_states = {}
        for game, game_data in app_dict.items():
            state = LocalGameState.None_
            for k, v in game_data.items():
                if k.lower() == "running" and str(v) == "1":
                    state |= LocalGameState.Running
                if k.lower() == "installed" and str(v) == "1":
                    state |= LocalGameState.Installed
            app_states[game] = state

        return app_states

    def get_configuration_folder() -> Optional[str]:
        raise NotImplementedError
    
    def get_custom_library_folders(self, config_path: str) -> Optional[List[str]]:
        """Parses library folders config file and returns a list of folders paths"""
        try:
            config = load_vdf(config_path)
            result = []
            for i in count(1):
                library_folders = config["LibraryFolders"]
                numerical_vdf_key = str(i)
                library_folder = library_folders.get(numerical_vdf_key)
                if library_folder is None:
                    break
                try:
                    library_path = library_folder["path"]
                except TypeError:
                    library_path = library_folder
                result.append(os.path.join(library_path, "steamapps"))
            return result
        except (OSError, SyntaxError, KeyError):
            log.exception("Failed to parse %s", config_path)
            return None

    def get_library_folders(self) -> Iterable[str]:
        configuration_folder = self.get_configuration_folder()
        if not configuration_folder:
            return []
        steam_apps_folder = os.path.join(configuration_folder, "steamapps")  # default location
        library_folders_config = os.path.join(steam_apps_folder, "libraryfolders.vdf")
        library_folders = self.get_custom_library_folders(library_folders_config) or []
        return [steam_apps_folder] + library_folders

    @staticmethod
    def get_app_manifests(library_folders: Iterable[str]) -> Iterable[str]:
        for library_folder in library_folders:
            escaped_path = glob.escape(library_folder)
            yield from glob.iglob(os.path.join(escaped_path, "*.acf"))

    @staticmethod
    def app_id_from_manifest_path(path):
        return os.path.basename(path)[len('appmanifest_'):-4]

    def get_installed_games(self, library_paths: Iterable[str]) -> Iterable[str]:
        for app_manifest_path in self.get_app_manifests(library_paths):
            app_id = self.app_id_from_manifest_path(app_manifest_path)
            if app_id:
                yield app_id

    def registry_apps_as_dict():
        raise NotImplementedError

    def local_games_list(self):
        local_games = []
        try:
            library_folders = self.get_library_folders()
            log.debug("Checking library folders: %s", str(library_folders))
            apps_ids = self.get_installed_games(library_folders)
            app_states = self.get_app_states_from_registry(self.registry_apps_as_dict())
            for app_id in apps_ids:
                app_state = app_states.get(app_id)
                if app_state is None:
                    continue
                local_game = LocalGame(app_id, app_state)
                local_games.append(local_game)
        except:
            log.exception("Failed to get local games list")
        finally:
            return local_games

    def get_state_changes(old_list, new_list):
        old_dict = {x.game_id: x.local_game_state for x in old_list}
        new_dict = {x.game_id: x.local_game_state for x in new_list}
        result = []
        # removed games
        result.extend(LocalGame(id, LocalGameState.None_) for id in old_dict.keys() - new_dict.keys())
        # added games
        result.extend(local_game for local_game in new_list if local_game.game_id in new_dict.keys() - old_dict.keys())
        # state changed
        result.extend(
            LocalGame(id, new_dict[id]) for id in new_dict.keys() & old_dict.keys() if new_dict[id] != old_dict[id])
        return result

    def get_client_executable() -> Optional[str]:
        raise NotImplementedError
    
    def is_uri_handler_installed(protocol) -> bool:
        raise NotImplementedError
    
    def get_steam_registry_monitor():
        raise NotImplementedError


    


    


   


    
