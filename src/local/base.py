import asyncio
import enum
import glob
import os
import subprocess
import webbrowser
from abc import ABC, abstractmethod
from contextlib import suppress
from logging import getLogger
from typing import Iterable, Optional

from attr import dataclass
from galaxy.api.types import LocalGame

from .shared import load_vdf

log = getLogger(__name__)


class StateFlags(enum.Flag):
    """StateFlags from appmanifest.acf file"""
    Invalid = 0
    Uninstalled = 1
    UpdateRequired = 2
    FullyInstalled = 4
    Encrypted = 8
    Locked = 16
    FilesMissing = 32
    AppRunning = 64
    FilesCorrupt = 128
    UpdateRunning = 256
    UpdatePaused = 512
    UpdateStarted = 1024
    Uninstalling = 2048
    BackupRunning = 4096
    Reconfiguring = 65536
    Validating = 131072
    AddingFiles = 262144
    Preallocating = 524288
    Downloading = 1048576
    Staging = 2097152
    Committing = 4194304
    UpdateStopping = 8388608


@dataclass
class Manifest:
    path: str
    
    def id(self):
        return os.path.basename(self.path)[len('appmanifest_'):-4]
    
    def app_size(self):
        with load_vdf(self.path) as manifest:
            app_state = manifest["AppState"]
            if StateFlags.FullyInstalled in StateFlags(int(app_state["StateFlags"])):
                return int(app_state["SizeOnDisk"])
            else:
                return int(app_state["BytesDownloaded"])


class BaseClient(ABC):

    # os dependant

    @abstractmethod
    def get_configuration_folder() -> Optional[str]:
        pass
    
    @abstractmethod
    def _is_uri_handler_installed() -> bool:
        pass
    
    @abstractmethod
    def _get_steam_shutdown_cmd():
        pass
    
    @abstractmethod
    def latest() -> Iterable[LocalGame]:
        pass

    @abstractmethod
    def changed() -> Iterable[LocalGame]:
        pass
    
    @abstractmethod
    def is_updated(self) -> bool:
        pass
    
    # os independent

    def _get_library_folders(self) -> Iterable[str]:
        configuration_folder = self.get_configuration_folder()
        if configuration_folder:
            # yield configuration_folder # default location
            config_path = os.path.join(configuration_folder, "steamapps", "libraryfolders.vdf")
            log.info("Finding library folders from: " + config_path)
            with load_vdf(config_path) as config:
                for library_folder in config["LibraryFolders"].values():
                    with suppress(TypeError):
                        library_folder = library_folder["path"]
                    if type(library_folder) is str:
                        yield library_folder

    def manifests(self) -> Iterable[Manifest]:
        for library_folder in self._get_library_folders():
            log.info("Getting app manifests in: " + library_folder)
            for path in glob.iglob(os.path.join(
                glob.escape(library_folder), 
                "steamapps",
                "*.acf"
            )):
                yield Manifest(path)
    
    def steam_cmd(self, command, game_id):
        if game_id == "499450": #witcher 3 hack?
            game_id = "292030"
        if self._is_uri_handler_installed():
            webbrowser.open(f"steam://{command}/{game_id}") 
        else:
            log.warning("Steam URI Handler not installed!")
            webbrowser.open("https://store.steampowered.com/about/")

    async def steam_shutdown(self):
        cmd = self._get_steam_shutdown_cmd()
        if cmd:
            log.debug("Running command '%s'", cmd)
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            await proc.communicate()
    
    def close(self):
        pass