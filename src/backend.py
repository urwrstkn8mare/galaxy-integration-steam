import logging
from datetime import datetime, timezone
from typing import List
from urllib.parse import urlparse

import aiohttp
from galaxy.api.errors import AccessDenied, AuthenticationRequired, UnknownBackendResponse
from galaxy.http import HttpClient
from yarl import URL


logger = logging.getLogger(__name__)


def is_absolute(url):
    return bool(urlparse(url).netloc)


async def get_text(response: aiohttp.ClientResponse) -> str:
    return await response.text(encoding="utf-8", errors="replace")


class CookieJar(aiohttp.CookieJar):
    def __init__(self):
        super().__init__()
        self._cookies_updated_callback = None

    def set_cookies_updated_callback(self, callback):
        self._cookies_updated_callback = callback

    def update_cookies(self, cookies, url=URL()):
        super().update_cookies(cookies, url)
        if cookies and self._cookies_updated_callback:
            self._cookies_updated_callback(list(self))


class AuthenticatedHttpClient(HttpClient):
    def __init__(self):
        self._auth_lost_callback = None
        self._cookie_jar = CookieJar()
        super().__init__(cookie_jar=self._cookie_jar)

    def set_auth_lost_callback(self, callback):
        self._auth_lost_callback = callback

    def set_cookies_updated_callback(self, callback):
        self._cookie_jar.set_cookies_updated_callback(callback)

    def update_cookies(self, cookies):
        self._cookie_jar.update_cookies(cookies)

    async def get(self, *args, **kwargs):
        try:
            response = await super().request("GET", *args, **kwargs)
        except AuthenticationRequired:
            self._auth_lost()

        html = await get_text(response)
        # "Login" button in menu
        if html.find('class="menuitem" href="https://store.steampowered.com/login/') != -1:
            self._auth_lost()

        return response

    def _auth_lost(self):
        if self._auth_lost_callback:
            self._auth_lost_callback()
        raise AccessDenied()


class SteamHttpClient:
    def __init__(self, http_client):
        self._http_client = http_client


    @staticmethod
    def parse_date(text_time):
        def try_parse(text, date_format):
            d = datetime.strptime(text, date_format)
            return datetime.combine(d.date(), d.time(), timezone.utc)

        formats = (
            "Unlocked %d %b, %Y @ %I:%M%p",
            "Unlocked %d %b @ %I:%M%p",
            "Unlocked %b %d, %Y @ %I:%M%p",
            "Unlocked %b %d @ %I:%M%p"
        )
        for date_format in formats:
            try:
                date = try_parse(text_time, date_format)
                if date.year == 1900:
                    date = date.replace(year=datetime.utcnow().year)
                return date
            except ValueError:
                continue

        logger.error("Unexpected date format: {}. Please report to the developers".format(text_time))
        raise UnknownBackendResponse()

    async def get_servers(self, cell_id) -> List[str]:
        url = f"http://api.steampowered.com/ISteamDirectory/GetCMList/v1/?cellid={cell_id}"
        response = await self._http_client.get(url)
        try:
            data = await response.json()
            return data['response']['serverlist_websockets']
        except (ValueError, KeyError) :
            logging.exception("Can not parse backend response")
            raise UnknownBackendResponse()
