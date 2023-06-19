from logging import getLogger
import os
from CoreServices.LaunchServices import LSCopyDefaultHandlerForURLScheme
from AppKit import NSWorkspace

from .shared import load_vdf
from .base import BaseClient

log = getLogger(__name__)


CONFIG_FOLDER = os.path.expanduser("~/Library/Application Support/Steam")
CLIENT_EXE = "/Applications/Steam.app/Contents/MacOS/steam_osx"


class FileRegistryMonitor:

    def __init__(self, filename):
        self._filename = filename
        self._stat = self._get_stat()

    def _get_stat(self):
        try:
            st = os.stat(self._filename)
        except OSError:
            return (0, 0)
        return (st.st_size, st.st_mtime_ns)

    def is_updated(self):
        current_stat = self._get_stat()
        changed = self._stat != current_stat
        self._stat = current_stat
        return changed

    def close(self):
        pass


class MacClient(BaseClient):
    def registry_apps_as_dict(self):
        config_folder = self.get_configuration_folder()

        if config_folder is not None:
            try:
                registry = load_vdf(os.path.join(config_folder, "registry.vdf"))
                return registry["Registry"]["HKCU"]["Software"]["Valve"]["Steam"]["Apps"]
            except OSError:
                log.exception("Failed to read Steam registry")
            except KeyError:
                log.exception("Failed to parse Steam registry")
        
        return {}


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
    def is_uri_handler_installed(protocol):
        bundle_id = LSCopyDefaultHandlerForURLScheme(protocol)
        if bundle_id:
            return NSWorkspace.sharedWorkspace().absolutePathForAppBundleWithIdentifier_(bundle_id) is not None
        return False
    
    @staticmethod
    def get_steam_registry_monitor():
        return FileRegistryMonitor(os.path.expanduser("~/Library/Application Support/Steam/registry.vdf"))