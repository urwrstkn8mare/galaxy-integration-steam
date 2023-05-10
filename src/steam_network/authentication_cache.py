from typing import Optional
from .enums import TwoFactorMethod


class AuthenticationCache:
    """ Cache designed to carry authentication-related information between the websocket and interface code. 

    This 'cache' is not designed to persist in any manner. it's simply a data-storage device. 
    """
    def __init__(self):
        self._two_factor_method : Optional[TwoFactorMethod] = None
        self._error_message: Optional[str] = None #used to display specific errors. Things like "passcode expired" or "password incorrect" or "username does not exist"
        self._status_message: Optional[str] = None #used to display status-related information to the user. this may be something like: "confirmation email sent to 'user@domain.com'"

    @property
    def two_factor_method(self):
        return self._two_factor_method

    @two_factor_method.setter
    def two_factor_method(self, val):
        self._two_factor_method = val

    @property
    def error_message(self):
        return self._error_message

    @error_message.setter
    def error_message(self, val):
        self._error_message = val

    @property
    def status_message(self):
        return self._status_message

    @status_message.setter
    def status_message(self, val):
        self._status_message = val
