from .enums import UserActionRequired, TwoFactorMethod

class SteamPollingData:
    """ Contains the data needed to poll the steam api for login success.
   
    For the most part, this data is immutable, but the client id can update if two-factor authentication times out. 
    """
    #def __init__(self, cid: int, sid: int, rid:bytes, intv:float, confMeth:UserActionRequired, confMsg: str, eem: str):
    def __init__(self, cid: int, sid: int, rid:bytes, intv:float, confMeth:TwoFactorMethod, confMsg: str, eem: str):
        self._client_id : int = cid     #the id assigned to us.
        self._steam_id : int = sid       #the id of the user that signed in
        self._request_id : bytes = rid  #unique request id. needed for the polling function.
        self._interval : float = intv   #interval to poll on.
        self._confirmation_method: TwoFactorMethod = confMeth #shorthand for confirmation type being used. The auth 
        self._confirmation_message: str = confMsg #the message Steam sent us along with the confirmation method we're using. This may be something like "we sent a message to q******@g****.com"
        self._extended_error_message : str = eem #used for errors. 

    @property
    def client_id(self):
        return self._client_id

    @client_id.setter
    def client_id(self, arg:int):
        self._client_id = arg

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
    def confirmation_message(self):
        return self._confirmation_message

    @property
    def extended_error_message(self):
        return self._extended_error_message
