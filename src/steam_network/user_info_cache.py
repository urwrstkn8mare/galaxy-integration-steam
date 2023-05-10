import asyncio
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class UserInfoCache:
    def __init__(self):
        self._steam_id: Optional[int] = None
        self._account_username: Optional[str] = None
        self._persona_name: Optional[str] = None
        self._refresh_token : Optional[str] = None
        self._access_token : Optional[str] = None
        
        self._changed = False
        
        self.initialized = asyncio.Event()

    def _check_initialized(self):
        if self._steam_id and self._account_username and self._persona_name and self._refresh_token:
            logger.info("User info cache initialized")
            self.initialized.set()
            self._changed = True

    def to_dict(self):
        creds = {
            'steam_id': base64.b64encode(str(self._steam_id).encode('utf-8')).decode('utf-8'),
            'refresh_token': base64.b64encode(str(self._refresh_token).encode('utf-8')).decode('utf-8'),
            'account_username': base64.b64encode(str(self._account_username).encode('utf-8')).decode('utf-8'),
            'persona_name': base64.b64encode(str(self._persona_name).encode('utf-8')).decode('utf-8')
        }
        return creds

    def from_dict(self, lookup):
        for key in lookup.keys():
            if lookup[key]:
                logger.info(f"Loaded {key} from stored credentials")

        if 'steam_id' in lookup:
            self._steam_id = int(base64.b64decode(lookup['steam_id']).decode('utf-8'))

        if 'account_username' in lookup:
            self._account_username = base64.b64decode(lookup['account_username']).decode('utf-8')

        if 'persona_name' in lookup:
            self._persona_name = base64.b64decode(lookup['persona_name']).decode('utf-8')

        if 'refresh_token' in lookup:
            self._token = base64.b64decode(lookup['refresh_token']).decode('utf-8')

    @property
    def changed(self):
        if self._changed:
            self._changed = False
            return True
        return False

    @property
    def steam_id(self):
        return self._steam_id

    @steam_id.setter
    def steam_id(self, val):
        if self._steam_id != val and self.initialized.is_set():
            self._changed = True
        self._steam_id = val
        if not self.initialized.is_set():
            self._check_initialized()

    @property
    def account_username(self):
        return self._account_username

    @account_username.setter
    def account_username(self, val):
        if self._account_username != val and self.initialized.is_set():
            self._changed = True
        self._account_username = val
        if not self.initialized.is_set():
            self._check_initialized()

    @property
    def persona_name(self):
        return self._persona_name

    @persona_name.setter
    def persona_name(self, val):
        if self._persona_name != val and self.initialized.is_set():
            self._changed = True
        self._persona_name = val
        if not self.initialized.is_set():
            self._check_initialized()

    @property
    def access_token(self):
        return self._access_token

    @access_token.setter
    def access_token(self, val):
        if self._access_token != val and self.initialized.is_set():
            self._changed = True
        self._access_token = val
        if not self.initialized.is_set():
            self._check_initialized()

    @property
    def refresh_token(self):
        return self._refresh_token

    @refresh_token.setter
    def refresh_token(self, val):
        if self._refresh_token != val and self.initialized.is_set():
            self._changed = True
        self._refresh_token = val
        if not self.initialized.is_set():
            self._check_initialized()
