from logging import getLogger
import os
from typing import Optional

from .shared import load_vdf
from .base import BaseClient

log = getLogger(__name__)


CONFIG_FOLDER = os.path.expanduser("~/Library/Application Support/Steam")
CLIENT_EXE = "/Applications/Steam.app/Contents/MacOS/steam_osx"

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