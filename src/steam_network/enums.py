from typing import Optional, Dict, Tuple, Union
import enum

import yarl
import urllib

import os
import pathlib

import logging

from .protocol.messages.steammessages_auth_pb2 import CAuthentication_AllowedConfirmation, EAuthSessionGuardType 
from pprint import pformat

#a constant. this is the path to the current directory, as a uri. this typically means adding file:/// to the beginning
DIRNAME = yarl.URL(pathlib.Path(os.path.dirname(os.path.realpath(__file__))).as_uri())
#another constant. the path to "index.html" relative to the current directory.
WEBPAGE_RELATIVE_PATH = r'/custom_login/index.html'

logger = logging.getLogger(__name__)

#defines the modes we will send to the 'websocket' queue
class AuthCall:

    RSA =               'rsa'
    LOGIN =             'login'
    UPDATE_TWO_FACTOR = 'two-factor-update'
    POLL_TWO_FACTOR =   'poll-two-factor'
    DONE =              'done'

class DisplayUriHelper(enum.Enum):
    GET_USER = 0
    LOGIN = 1
    TWO_FACTOR_MAIL = 2
    TWO_FACTOR_MOBILE = 3

    def _add_view(self, args:Dict[str,str]) -> Dict[str, str] : 
        if (self == self.LOGIN):
            args["view"] = "login"
        elif (self == self.TWO_FACTOR_MAIL):
            args["view"] = "steamguard"
        elif (self == self.TWO_FACTOR_MOBILE):
            args["view"] = "steamauthenticator"
        else:
            args["view"] = "user"
        return args;

    def _get_errored(self, args: Dict[str,str], errored: bool, verbose: bool = False) -> Dict[str, str]:
        if (errored):
            args["errored"] = "true"
        elif (verbose):
            args["errored"] = "false"
        return args

    def GetStartUri(self, username: Optional[str] = None, errored : bool = False) -> str:
        #imho this is the most intuitive way of getting the start url. it's not the most "Pythonic" of means, but it is infinitely more readable.

        #url params go into a dict. urllib.urlencode will autmatically convert a dict to a string of properly concatenated url params ('&'). 
        #it also escapes any characters that HTTP does not like, which is why we aren't doing it manually. 
        args : Dict[str, str] = {}
        #the path to index.html, with a question and a placeholder for all the url parameters. 
        result : str = str(DIRNAME) + WEBPAGE_RELATIVE_PATH + "?"
        args = self._add_view(args)
        args = self._get_errored(args, errored, False)
        if (self == self.LOGIN):
            if (username is None):
                raise ValueError("username cannot be null in login view")
            else:
                args["username"] = username
        #now, convert the dict of url params to a string. replace the placeholder with this string. return the result. 
        return result + urllib.parse.urlencode(args)
    
    def EndUri(self) -> str:
         if (self == self.LOGIN):
             return 'login_finished'
         elif (self == self.TWO_FACTOR_MAIL):
             return 'two_factor_mail_finished'
         elif (self == self.TWO_FACTOR_MOBILE):
             return 'two_factor_mobile_finished'
         else:
             return 'user_finished'

    def GetEndUriRegex(self):
        return ".*" + self.EndUri() + ".*";

class UserActionRequired(enum.IntEnum):
    NoActionRequired = 0
    EmailTwoFactorInputRequired = 1
    PhoneTwoFactorInputRequired = 2
    PhoneTwoFactorConfirmRequired = 3
    PasswordRequired = 4
    TwoFactorExpired = 5
    InvalidAuthData = 6


#def to_UserAction(auth_enum : Union[EAuthSessionGuardType, CAuthentication_AllowedConfirmation]) -> UserActionRequired:
def to_UserAction(auth_enum) -> UserActionRequired:
    if (isinstance(auth_enum, CAuthentication_AllowedConfirmation)):
        auth_enum = auth_enum.confirmation_type
    ret_val, _ = _to_UserAction(auth_enum, None)
    return ret_val
    
#def _to_UserAction(auth_enum : EAuthSessionGuardType, msg: Optional[str]) -> Tuple[UserActionRequired, str]:
def _to_UserAction(auth_enum, msg: Optional[str]) -> Tuple[UserActionRequired, str]:
    if (auth_enum == EAuthSessionGuardType.k_EAuthSessionGuardType_None):
        return (UserActionRequired.NoActionRequired, msg)
    elif (auth_enum == EAuthSessionGuardType.k_EAuthSessionGuardType_EmailCode):
        return (UserActionRequired.EmailTwoFactorInputRequired, msg)
    elif (auth_enum == EAuthSessionGuardType.k_EAuthSessionGuardType_DeviceCode):
        return (UserActionRequired.PhoneTwoFactorInputRequired, msg)
    elif (auth_enum == EAuthSessionGuardType.k_EAuthSessionGuardType_DeviceConfirmation):
        return (UserActionRequired.PhoneTwoFactorConfirmRequired, msg)
    else: #if (k_EAuthSessionGuardType_Unknown, k_EAuthSessionGuardType_LegacyMachineAuth, k_EAuthSessionGuardType_MachineToken, k_EAuthSessionGuardType_EmailConfirmation, or an invalid number
        return (UserActionRequired.InvalidAuthData, msg)

def to_UserActionWithMessage(allowed_confirmation : CAuthentication_AllowedConfirmation) -> Tuple[UserActionRequired, str]:
    return _to_UserAction(allowed_confirmation.confirmation_type, allowed_confirmation.associated_message)

def to_CAuthentication_AllowedConfirmation(actionRequired : UserActionRequired) -> CAuthentication_AllowedConfirmation:
    
    if (actionRequired == UserActionRequired.NoActionRequired):
        return CAuthentication_AllowedConfirmation.k_EAuthSessionGuardType_None
    elif (actionRequired == UserActionRequired.EmailTwoFactorInputRequired):
        return CAuthentication_AllowedConfirmation.auth_k_EAuthSessionGuardType_EmailCode
    elif (actionRequired == UserActionRequired.PhoneTwoFactorInputRequired):
        return CAuthentication_AllowedConfirmation.k_EAuthSessionGuardType_DeviceCode
    elif (actionRequired == UserActionRequired.PhoneTwoFactorConfirmRequired):
        return CAuthentication_AllowedConfirmation.k_EAuthSessionGuardType_DeviceConfirmation
    else: #if UserActionRequired.InvalidAuthData or an invalid number
        return CAuthentication_AllowedConfirmation.k_EAuthSessionGuardType_Unknown