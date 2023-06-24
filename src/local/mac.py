from contextlib import suppress
from functools import lru_cache
import glob
from logging import getLogger
import os
from typing import Dict, Iterable, Optional, Union
from CoreServices.LaunchServices import LSCopyDefaultHandlerForURLScheme 
from AppKit import NSWorkspace
from galaxy.api.types import LocalGame, LocalGameState 
from file_read_backwards import FileReadBackwards

from .shared import load_vdf
from .base import BaseClient

log = getLogger(__name__)


CONFIG_FOLDER = os.path.expanduser("~/Library/Application Support/Steam")
CLIENT_EXE = "/Applications/Steam.app/Contents/MacOS/steam_osx"
CONTENTLOG = os.path.join(CONFIG_FOLDER, "logs/content_log.txt")
STATE_MAPPING = { # order matters !
    "Uninstalled": LocalGameState.None_,
    "App Running": LocalGameState.Running,
    "Fully Installed": LocalGameState.Installed
}


class ContentLog:
    def __init__(self, path):
        self.path = path
        self._last_size = 0

    def all_lines(self):
        with FileReadBackwards(self.path, encoding="ascii") as f:
            self._last_size = f.iterator._FileReadBackwardsIterator__buf.read_position # file size
            yield from f

    def is_updated(self):
        return self._size() != self._last_size

    def new_lines(self):
        size = self._size()
        if size != self._last_size:
            with FileReadBackwards(self.path, encoding="ascii") as f:
                for l in f:
                    yield l
                    if f.iterator._FileReadBackwardsIterator__buf.read_position <= self._last_size:
                        break
            self._last_size = size

    def _size(self):
        try:
            st = os.stat(self.path)
        except OSError:
            log.warning("Couldn't get size of content_log.txt!")
            return 0
        return st.st_size


class MacClient(BaseClient):
    def __init__(self) -> None:
        self._contentlog = ContentLog(CONTENTLOG)
        self.is_updated = self._contentlog.is_updated

    def _states(self, lines):
        ids = [m.id() for m in self.manifests()]
        for line in lines:
            words = line.strip().split()[2:]
            if len(words) >= 6:
                if words[0] == "AppID":
                    app_id = words[1]
                    with suppress(ValueError):
                        ids.remove(app_id)
                    if words[2] + words[3] == "statechanged":
                        states = words[5].split(",")
                        for k,v in STATE_MAPPING.items():
                            if k in states:
                                yield LocalGame(app_id, v)
                    if len(ids) == 0:
                        break
                            
    def latest(self) -> Iterable[LocalGame]:
        # should we make sure all manifests are always detected as installed?
        yield from self._states(self._contentlog.all_lines()) 

    def changed(self) -> Iterable[LocalGame]:
        yield from self._states(self._contentlog.new_lines())

    @staticmethod
    def get_client_executable():
        if os.access(CLIENT_EXE, os.X_OK):
            return CLIENT_EXE
        log.warning("Steam not installed")

    @staticmethod
    def get_configuration_folder():
        if os.path.isdir(CONFIG_FOLDER):
            return CONFIG_FOLDER
        log.warning("Steam not installed")

    @staticmethod
    def _is_uri_handler_installed():
        bundle_id = LSCopyDefaultHandlerForURLScheme("steam")
        if bundle_id:
            return NSWorkspace.sharedWorkspace().absolutePathForAppBundleWithIdentifier_(bundle_id) is not None
        return False
    
    @staticmethod
    def _get_steam_shutdown_cmd():
        return "osascript -e 'quit app \"Steam\"'"
    