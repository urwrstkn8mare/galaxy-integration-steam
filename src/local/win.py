from logging import getLogger
from typing import Optional
import winreg

from .base import BaseClient

log = getLogger(__name__)


def get_reg_val(name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            return str(winreg.QueryValueEx(key, name)[0])
    except OSError:
        log.warning("Steam not installed")


class WinClient(BaseClient):
    @staticmethod
    def registry_apps_as_dict():
        try:
            apps = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam\Apps")
        except OSError as e:
            log.info("Steam Apps registry cannot be read: %s", str(e))
            return {}

        apps_dict = dict()
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
                apps_dict[sub_key_name] = sub_key_dict
                sub_key_index += 1
            except OSError:
                log.exception("Failed to parse Steam registry")
                break

        winreg.CloseKey(apps)

        return apps_dict

    @staticmethod
    def get_client_executable() -> Optional[str]:
        return get_reg_val("SteamExe")

    @staticmethod
    def get_configuration_folder():
        return get_reg_val("SteamPath")