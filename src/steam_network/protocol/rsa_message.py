from .consts import EResult

from datetime import datetime

class RSAMessage:
    """ Class Designed to nicely display the information retrieved from an RSA request so we can use it with type hinting and not go insane
    """
    def __init__(this, result: EResult, mod : int, exponent : int,timestamp : int):
        this._result : EResult = result
        this._mod :int = mod
        this._exp : int = exponent
        this._timestamp : int = timestamp
        this._dt : datetime = datetime.fromtimestamp(timestamp)

    @property
    def mod(self):
        return self._mod

    @property
    def exp(self):
        return self._exp

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def timestamp_as_datetime(self):
        return self._dt
