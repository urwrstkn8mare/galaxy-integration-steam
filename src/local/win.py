import os
import shlex
import winreg
from contextlib import suppress
from logging import getLogger
from typing import Dict, Iterable, List, Optional

from galaxy.api.types import LocalGame, LocalGameState
from galaxy.registry_monitor import RegistryMonitor

from .base import BaseClient
from .shared import create_games_dict

log = getLogger(__name__)


HKEY_CURRENT_USER = 0x80000001


def get_reg_val(name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            return str(winreg.QueryValueEx(key, name)[0])
    except OSError:
        log.warning("Steam not installed")


def registry_apps():
        try:
            apps = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam\Apps")
        except OSError as e:
            log.info("Steam Apps registry cannot be read: %s", str(e))
            return {}

        sub_key_index = 0

        while True:
            try:
                sub_key_name = winreg.EnumKey(apps, sub_key_index)
            except OSError:
                # OSError marks end of the enumeration: https://docs.python.org/3/library/winreg.html#winreg.EnumKey
                break
            try:
                sub_key_dict = dict()
                with winreg.OpenKey(apps, sub_key_name) as sub_key:
                    value_index = 0
                    while True:
                        try:
                            v = winreg.EnumValue(sub_key, value_index)
                            sub_key_dict[v[0]] = v[1]
                            value_index += 1
                        except OSError:
                            break
                    winreg.CloseKey(sub_key)
                yield sub_key_name, sub_key_dict
                sub_key_index += 1
            except OSError:
                log.exception("Failed to parse Steam registry")
                break

        winreg.CloseKey(apps)


class WinClient(BaseClient):
    def __init__(self) -> None:
        super().__init__()
        self._regmon = RegistryMonitor(HKEY_CURRENT_USER, r"Software\Valve\Steam\Apps")
        self._states_last = create_games_dict()
        
    def is_updated(self) -> bool:
        return self._regmon.is_updated()
    
    def _states_latest(self) -> Optional[Dict[str, LocalGameState]]:
        if self.is_updated():
            states = {}
            for game, game_data in registry_apps():
                state = LocalGameState.None_    
                for k, v in game_data.items():
                    if k.lower() == "running" and str(v) == "1":
                        state |= LocalGameState.Running
                    if k.lower() == "installed" and str(v) == "1":
                        state |= LocalGameState.Installed
                states[game] = state
            return states
        
    def latest(self) -> List[LocalGame]:
        self._states_last = self._states_latest() or self._states_last
        for m in self.manifests():
            self._states_last[m.id()] |= LocalGameState.Installed
        return [LocalGame(k,v) for k,v in self._states_last.items()]

    def changed(self) -> Iterable[LocalGame]:
        new = self._states_latest()
        if new is None:
            return
        old = self._states_last
        for id in old.keys() - new.keys():
            yield LocalGame(id, LocalGameState.None_)
        for id, state in new.items() - old.items():
            yield LocalGame(id, state)
        self._states_last = new

    @staticmethod
    def get_configuration_folder():
        return get_reg_val("SteamPath")
    
    @staticmethod
    def _is_uri_handler_installed():
        with suppress(OSError, ValueError), winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"{}\shell\open\command".format("steam")) as key:
            executable_template = winreg.QueryValue(key, None)
            splitted_exec = shlex.split(executable_template)
            if splitted_exec:
                return os.path.exists(splitted_exec[0])
            
        return False
    
    def _get_steam_shutdown_cmd(self):
        exe = get_reg_val("SteamExe")
        if exe:
            return f'"{exe}" -shutdown -silent'
        
    def close(self):
        super().close()
        self._regmon.close()