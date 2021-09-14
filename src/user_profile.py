import json
import logging
import re
from typing import List

import aiohttp
from bs4 import BeautifulSoup, Tag


logger = logging.getLogger(__name__)


async def get_text(response: aiohttp.ClientResponse) -> str:
    return await response.text(encoding="utf-8", errors="replace")


class UserProfileChecker:
    _BASE_URL = 'https://steamcommunity.com'

    def __init__(self, http_client):
        self._http_client = http_client

    async def check_is_public_by_custom_url(self, username) -> bool:
        url = self._BASE_URL + f'/id/{username}/games/?tab=all'
        return await self._verify_is_public(url)

    async def check_is_public_by_steam_id(self, steam_id) -> bool:
        if not steam_id:
            raise ValueError(f"Incorrect Steam64 ID value: {steam_id}")
        url = self._BASE_URL + f'/profiles/{steam_id}/games/?tab=all'
        return await self._verify_is_public(url)

    async def _verify_is_public(self, url: str) -> bool:
        profile_data = await self._fetch_profile_data(url)

        if not self._parse_user_games(str(profile_data.string)):
            raise NotPublicGameDetailsOrUserHasNoGames
        return True

    async def _fetch_profile_data(self, url) -> Tag:
        text = await get_text(await self._http_client.get(url))
        parsed_html = BeautifulSoup(text, 'html.parser')
        page = parsed_html.find("div", class_="responsive_page_template_content")
        if not page:
            raise ParseError
        if page.find("div", class_="error_ctn"):
            raise ProfileDoesNotExist
        if page.find("div", class_="profile_private_info"):
            raise ProfileIsNotPublic
        if not page.find("script", language="javascript"):
            raise ParseError
        return page.find("script", language="javascript")

    @staticmethod
    def _parse_user_games(profile_data: str) -> List:
        pattern = re.compile('var rgGames = (.*?);')
        js_games = pattern.search(profile_data)
        games = json.loads(js_games.groups()[0])
        return games


class ProfileDoesNotExist(Exception):
    pass


class ProfileIsNotPublic(Exception):
    pass


class ParseError(Exception):
    pass


class NotPublicGameDetailsOrUserHasNoGames(Exception):
    pass
