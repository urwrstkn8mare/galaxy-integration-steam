import logging
import ssl
from typing import List

from backend import SteamHttpClient

logger = logging.getLogger(__name__)


class WebSocketList:
    def __init__(self,
                 steam_http_client: SteamHttpClient,
                 ssl_context: ssl.SSLContext,
                 ):
        self._steam_http_client = steam_http_client
        self._ssl_context = ssl_context

    async def get(self, cell_id: int) -> List[str]:
        servers = await self._steam_http_client.get_servers(cell_id)
        logger.debug("Got servers from backend: %s", str(servers))

        sockets = [f"wss://{server}/cmsocket/" for server in servers]

        if not sockets:
            return []

        return sockets
