from collections import defaultdict
from contextlib import contextmanager
from logging import getLogger
from platform import system
from typing import Any, Dict

import vdf
from galaxy.api.types import LocalGameState

log = getLogger(__name__)


# Get Windows OS

if system() not in ["Windows", "Darwin"]:
    raise RuntimeError("OS not supported: " + system())

IS_WIN = system() == "Windows"


# VDF stuff

class CaseInsensitiveDict(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super().__getitem__(key.lower())

@contextmanager
def load_vdf(path: str) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            yield vdf.load(f, mapper=CaseInsensitiveDict)
    except OSError:
        log.exception("Failed to read VDF: " + path)
    except KeyError:
        log.exception("Failed to parse VDF: " + path)


# other

def create_games_dict() -> Dict[str, LocalGameState]:
    return defaultdict(lambda:LocalGameState.None_)