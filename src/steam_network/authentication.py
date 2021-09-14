import os
import pathlib

from galaxy.api.types import NextStep
import yarl


DIRNAME = yarl.URL(pathlib.Path(os.path.dirname(os.path.realpath(__file__))).as_uri())


class StartUri:
    __INDEX = DIRNAME / 'custom_login' / 'index.html'  

    LOGIN =                    __INDEX % {'view': 'login'}
    LOGIN_FAILED =             __INDEX % {'view': 'login', 'errored': 'true'}
    TWO_FACTOR_MAIL =          __INDEX % {'view': 'steamguard'}
    TWO_FACTOR_MAIL_FAILED =   __INDEX % {'view': 'steamguard', 'errored': 'true'}
    TWO_FACTOR_MOBILE =        __INDEX % {'view': 'steamauthenticator'}
    TWO_FACTOR_MOBILE_FAILED = __INDEX % {'view': 'steamauthenticator', 'errored': 'true'}
    PUBLIC_PROFILE_PROMPT =    __INDEX % {'view': 'publicprofileprompt'}


class EndUri:
    LOGIN_FINISHED =             '.*login_finished.*'
    TWO_FACTOR_MAIL_FINISHED =   '.*two_factor_mail_finished.*'
    TWO_FACTOR_MOBILE_FINISHED = '.*two_factor_mobile_finished.*'
    PUBLIC_PROMPT_FINISHED =     '.*public_prompt_finished.*'


_NEXT_STEP = {
    "window_title": "Login to Steam",
    "window_width": 500,
    "window_height": 460,
    "start_uri": None,
    "end_uri_regex": None
}


def next_step_response(start_uri, end_uri_regex=EndUri.LOGIN_FINISHED):
    next_step = _NEXT_STEP
    next_step['start_uri'] = str(start_uri)
    next_step['end_uri_regex'] = end_uri_regex
    return NextStep("web_session", next_step)
