import enum
from platform import system
from typing import Any, Dict
import vdf


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

def load_vdf(path: str) -> Dict[str, Any]:
    return vdf.load(open(path, encoding="utf-8", errors="replace"), mapper=CaseInsensitiveDict)


# 

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