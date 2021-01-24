import asyncio
import logging
import ssl
import time
from operator import itemgetter
from typing import List, Tuple, Dict, Any

import websockets

from backend import SteamHttpClient

logger = logging.getLogger(__name__)


class WebSocketList:
    def __init__(self, steam_http_client: SteamHttpClient, ssl_context: ssl.SSLContext):
        self._steam_http_client = steam_http_client
        self._ssl_context = ssl_context

    async def get_ordered_by_ping(self, cell_id: int) -> List[str]:
        servers = await self._steam_http_client.get_servers(cell_id)

        sockets_with_ping = await self._test_sockets(
                [f"wss://{server}/cmsocket/" for server in servers]
            )

        if not sockets_with_ping:
            return []

        sorted_sockets = sorted(sockets_with_ping.keys(), key=itemgetter(1))
        return sorted_sockets

    async def _test_sockets(self, sockets: List[str]) -> Dict[str, int]:
        tests = [self._measure_ping(socket) for socket in sockets]

        res = await asyncio.gather(*tests)

        return {server: ping for server, ping in res if ping is not None}

    async def _measure_ping(self, socket) -> Tuple[str, Any]:
        try:
            start_time = time.time()
            websocket = await asyncio.wait_for(websockets.connect(socket, ssl=self._ssl_context), 5)
            time_to_connect = time.time() - start_time
            time_to_connect = int(time_to_connect * 1000)
            await websocket.close()
            logger.debug("Got ping %i for server %s", time_to_connect, socket)
            return socket, time_to_connect
        except (asyncio.TimeoutError, OSError, websockets.InvalidURI, websockets.InvalidHandshake):
            logger.debug("Failed to connect to %s", socket)
            return socket, None
