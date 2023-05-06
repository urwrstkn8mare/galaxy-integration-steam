import os
import pathlib

from galaxy.api.types import NextStep
import yarl
import urllib

from typing import Optional, Dict
import enum

import logging

#a constant. this is the path to the current directory, as a uri. this typically means adding file:/// to the beginning
DIRNAME = yarl.URL(pathlib.Path(os.path.dirname(os.path.realpath(__file__))).as_uri())
#another constant. the path to "index.html" relative to the current directory.
WEBPAGE_RELATIVE_PATH = r'/custom_login/index.html'

logger = logging.getLogger(__name__)

#defines the modes we will send to the 'websocket' queue
class AuthCall:

    RSA =          'rsa'
    LOGIN =        'login'
    UPDATE_TWO_FACTOR =   'two-factor-update'
    POLL_TWO_FACTOR =   'poll-two-factor'

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



class StartUri:
    __INDEX = DIRNAME / 'custom_login' / 'index.html'  

    GET_USER =                                                __INDEX % {'view': 'user'}
    GET_USER_FAILED =                                         __INDEX % {'view': 'user', 'errored': 'true'}
    LOGIN =                                                   __INDEX % {'view': 'login'}
    LOGIN_FAILED =                                            __INDEX % {'view': 'login', 'errored': 'true'}
    TWO_FACTOR_MAIL =                                         __INDEX % {'view': 'steamguard'}
    TWO_FACTOR_MAIL_FAILED =                                  __INDEX % {'view': 'steamguard', 'errored': 'true'}
    TWO_FACTOR_MOBILE =                                       __INDEX % {'view': 'steamauthenticator'}
    TWO_FACTOR_MOBILE_FAILED =                                __INDEX % {'view': 'steamauthenticator', 'errored': 'true'}
    PP_PROMPT__PROFILE_IS_NOT_PUBLIC =                        __INDEX % {'view': 'pp_prompt__profile_is_not_public'}
    PP_PROMPT__NOT_PUBLIC_GAME_DETAILS_OR_USER_HAS_NO_GAMES = __INDEX % {'view': 'pp_prompt__not_public_game_details_or_user_has_no_games'}
    PP_PROMPT__UNKNOWN_ERROR =                                __INDEX % {'view': 'pp_prompt__unknown_error'}

    @classmethod 
    def add_username(username: str) -> str:
        return "&username=" + urllib.parse.quote_plus(username)


class EndUriRegex:
    USER_FINISHED =              '.*user_finished.*'
    LOGIN_FINISHED =             '.*login_finished.*'
    TWO_FACTOR_MAIL_FINISHED =   '.*two_factor_mail_finished.*'
    TWO_FACTOR_MOBILE_FINISHED = '.*two_factor_mobile_finished.*'
    PUBLIC_PROMPT_FINISHED =     '.*public_prompt_finished.*'

class EndUriConst:
    USER_FINISHED =              'user_finished'
    LOGIN_FINISHED =             'login_finished'
    TWO_FACTOR_MAIL_FINISHED =   'two_factor_mail_finished'
    TWO_FACTOR_MOBILE_FINISHED = 'two_factor_mobile_finished'
    PUBLIC_PROMPT_FINISHED =     'public_prompt_finished'

_NEXT_STEP = {
    "window_title": "Login to Steam",
    "window_width": 500,
    "window_height": 460,
    "start_uri": None,
    "end_uri_regex": None
}

def next_step_response_simple(display: DisplayUriHelper, username: str, errored:bool = False) -> NextStep:
    next_step = _NEXT_STEP
    next_step['start_uri'] = display.GetStartUri(username, errored)
    next_step['end_uri_regex'] = display.GetEndUriRegex()

    return NextStep("web_session", next_step)

def next_step_response(start_uri, end_uri_regex=EndUriRegex.LOGIN_FINISHED):
    next_step = _NEXT_STEP
    next_step['start_uri'] = str(start_uri)
    next_step['end_uri_regex'] = end_uri_regex
    return NextStep("web_session", next_step)
