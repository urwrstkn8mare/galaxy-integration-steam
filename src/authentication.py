import os
from galaxy.api.types import NextStep
import pathlib

_DIRNAME = pathlib.Path(os.path.dirname(os.path.realpath(__file__))).as_uri()


class START_URI():
    LOGIN = os.path.join(_DIRNAME, os.path.join(r'custom_login', 'index.html?view=login'))
    LOGIN_FAILED = os.path.join(_DIRNAME, os.path.join(r'custom_login', 'index.html?view=login?errored=true'))
    TWO_FACTOR_MAIL = os.path.join(_DIRNAME, os.path.join(r'custom_login', 'index.html?view=steamguard'))
    TWO_FACTOR_MAIL_FAILED = os.path.join(_DIRNAME, os.path.join(r'custom_login', 'index.html?view=steamguard?errored=true'))
    TWO_FACTOR_MOBILE = os.path.join(_DIRNAME, os.path.join(r'custom_login', 'index.html?view=steamauthenticator'))
    TWO_FACTOR_MOBILE_FAILED = os.path.join(_DIRNAME, os.path.join(r'custom_login', 'index.html?view=steamauthenticator?errored=true'))


class END_URI():
    LOGIN_FINISHED = '.*login_finished.*'
    TWO_FACTOR_MAIL_FINISHED = '.*two_factor_mail_finished.*'
    TWO_FACTOR_MOBILE_FINISHED = '.*two_factor_mobile_finished.*'


_NEXT_STEP = {
    "window_title": "Login to Steam",
    "window_width": 500,
    "window_height": 460,
    "start_uri": None,
    "end_uri_regex": None
}


def next_step_response(start_uri, end_uri_regex):
    next_step = _NEXT_STEP
    next_step['start_uri'] = start_uri
    next_step['end_uri_regex'] = end_uri_regex
    return NextStep("web_session", next_step)






