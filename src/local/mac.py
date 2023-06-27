import os
from logging import getLogger
from typing import Dict, Iterable, List

from AppKit import NSWorkspace
from CoreServices.LaunchServices import LSCopyDefaultHandlerForURLScheme
from file_read_backwards import FileReadBackwards
from galaxy.api.types import LocalGame, LocalGameState

from .base import BaseClient
from .shared import create_games_dict

log = getLogger(__name__)


CONFIG_FOLDER = os.path.expanduser("~/Library/Application Support/Steam")
CONTENTLOG = os.path.join(CONFIG_FOLDER, "logs/content_log.txt")
STATE_MAPPING = { # order matters !
    "Uninstalled": LocalGameState.None_,
    "App Running": LocalGameState.Installed | LocalGameState.Running,
    "Fully Installed": LocalGameState.Installed
}
MAX_PARSE = 100000 # ¯\_(ツ)_/¯


class ContentLog:
    def __init__(self, path):
        self.path = path
        self._last_size = 0
        self._last_line = None

    def all_lines(self):
        with FileReadBackwards(self.path, encoding="ascii") as f:
            self._last_size = self._size()
            self._last_line = f.readline().strip()
            yield self._last_line
            yield from f

    def is_updated(self):
        return self._size() != self._last_size

    def new_lines(self):
        size = self._size()
        if size != self._last_size:
            with FileReadBackwards(self.path, encoding="ascii") as f:
                new_last_line = f.readline().strip()
                yield new_last_line
                for l in f:
                    if l == self._last_line:
                        break
                    yield l
                self._last_line = new_last_line
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
        super().__init__()
        self._contentlog = ContentLog(CONTENTLOG)

    def is_updated(self) -> bool:
        return self._contentlog.is_updated()

    def _states(self, lines): # lines is an iterable
        yielded = set()
        for i, line in enumerate(lines):
            if i == MAX_PARSE:
                break
            words = line.strip().split(maxsplit=7)[2:]
            if len(words) == 6:
                if words[0] == "AppID":
                    app_id = words[1]
                    if app_id not in yielded:
                        if words[2] + words[3] == "statechanged":
                            states = words[5].split(",")
                            for k,v in STATE_MAPPING.items():
                                if k in states:
                                    yield app_id, v
                                    yielded.add(app_id)
                                    break
                            
    def latest(self) -> List[LocalGame]:
        games = create_games_dict()
        for m in self.manifests():
            games[m.id()] = LocalGameState.Installed
        for id, state in self._states(self._contentlog.all_lines()):
            games[id] |= state
        return [LocalGame(k,v) for k,v in games.items()]

    def changed(self) -> Iterable[LocalGame]:
        return (LocalGame(id, v) for id, v in self._states(self._contentlog.new_lines()))

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
    