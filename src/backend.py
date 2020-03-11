import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Tuple
from urllib.parse import urlparse

import aiohttp
from galaxy.api.errors import AccessDenied, AuthenticationRequired, UnknownBackendResponse
from galaxy.http import HttpClient
from requests_html import HTML
from yarl import URL
import json


logger = logging.getLogger(__name__)


class UnfinishedAccountSetup(Exception):
    pass


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

    async def get_profile(self):
        url = "https://steamcommunity.com/"
        text = await get_text(await self._http_client.get(url, allow_redirects=True))

        def parse(text):
            html = HTML(html=text)
            profile_url = html.find("a.user_avatar", first=True)
            if not profile_url:
                logger.error("Can not parse backend response - no a.user_avatar")
                raise UnknownBackendResponse()
            try:
                return profile_url.attrs["href"]
            except KeyError:
                logger.exception("Can not parse backend response")
                return UnknownBackendResponse()

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, parse, text)

    async def get_profile_data(self, url):
        text = await get_text(await self._http_client.get(url, allow_redirects=True))

        def parse(text, user_profile_url):
            html = HTML(html=text)
            # find persona_name
            div = html.find("div.profile_header_centered_persona", first=True)
            if not div:
                fallback_div = html.find("div.welcome_header_ctn")
                if fallback_div:
                    logger.info("Fresh account without set up steam profile.")
                    raise UnfinishedAccountSetup()
                logger.error("Can not parse backend response - no div.profile_header_centered_persona")
                raise UnknownBackendResponse()
            span = div.find("span.actual_persona_name", first=True)
            if not span:
                logger.error("Can not parse backend response - no span.actual_persona_name")
                raise UnknownBackendResponse()
            persona_name = span.text

            # find steam id
            variable = 'g_steamID = "'
            start = text.find(variable)
            if start == -1:
                logger.error("Can not parse backend response - no g_steamID variable")
                raise UnknownBackendResponse()
            start += len(variable)
            end = text.find('";', start)
            steam_id = text[start:end]

            # find miniprofile id
            profile_link = f'{user_profile_url}" data-miniprofile="'
            start = text.find(profile_link)
            if start == -1:
                logger.error("Can not parse backend response - no steam profile href")
                raise UnknownBackendResponse()

            return steam_id, persona_name

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, parse, text, url)

    async def get_games(self, steam_id):
        url = "https://steamcommunity.com/profiles/{}/games/?tab=all".format(steam_id)

        # find js array with games
        text = await get_text(await self._http_client.get(url))
        variable = "var rgGames ="
        start = text.find(variable)
        if start == -1:
            raise UnknownBackendResponse()
        start += len(variable)
        end = text.find(";\r\n", start)
        array = text[start:end]

        try:
            games = json.loads(array)
        except json.JSONDecodeError:
            logger.exception("Can not parse backend response")
            raise UnknownBackendResponse()

        return games

    async def setup_steam_profile(self, profile_url):
        url = profile_url.split('/home')[0]
        url += '/edit?welcomed=1'
        await self._http_client.get(url, allow_redirects=True)

    async def get_authentication_data(self) -> Tuple[int, int, str, str]:
        url = "https://steamcommunity.com/chat/clientjstoken"
        response = await self._http_client.get(url)
        try:
            data = await response.json()
            return int(data["steamid"]), int(data["accountid"]), data["account_name"], data["token"]
        except (ValueError, KeyError):
            logger.exception("Can not parse backend response")
            raise UnknownBackendResponse()

    async def get_servers(self) -> List[str]:
        url = "http://api.steampowered.com/ISteamDirectory/GetCMList/v1/?cellid=0"
        response = await self._http_client.get(url)
        try:
            data = await response.json()
            return data['response']['serverlist_websockets']
        except (ValueError, KeyError) :
            logging.exception("Can not parse backend response")
            raise UnknownBackendResponse()
