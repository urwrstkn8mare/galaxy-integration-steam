from .protocol_client import UserActionRequired

class SteamPollingData:
    def __init__(self, cid: int, sid: int, rid:bytes, intv:float, confMeth:UserActionRequired, eem: str):
        self._client_id : int = cid     #the id assigned to us.
        self._steam_id : int = sid       #the id of the user that signed in
        self._request_id : bytes = rid  #unique request id. needed for the polling function.
        self._interval : float = intv   #interval to poll on.
        self._confirmation_method: UserActionRequired = confMeth #shorthand for confirmation type being used. The auth 
        self._extended_error_message : str #used for errors. 

    @property
    def client_id(self):
        return self._client_id

    @property
    def steam_id(self):
        return self._steam_id

    @property
    def request_id(self):
        return self._request_id

    @property
    def interval(self):
        return self._interval

    @property
    def confirmation_method(self):
        return self._confirmation_method

    @property
    def extended_error_message(self):
        return self._extended_error_message