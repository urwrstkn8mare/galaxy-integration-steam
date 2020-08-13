import asyncio
import json
import time
import logging
from operator import itemgetter
import ssl
from typing import Dict, List, Any

import websockets

from backend import SteamHttpClient
from persistent_cache_state import PersistentCacheState


logger = logging.getLogger(__name__)

class ServersCache:
    def __init__(
        self,
        backend_client: SteamHttpClient,
        ssl_context: ssl.SSLContext,
        persistent_cache: Dict[str, Any],
        persistent_cache_state: PersistentCacheState
    ):
        self._backend_client = backend_client
        self._ssl_context = ssl_context
        self._persistent_cache = persistent_cache
        self._persistent_cache_state = persistent_cache_state

    def _read_cache(self):

        cache = json.loads(self._persistent_cache.get('servers_cache', 'null'))

        if cache is None:
            logger.debug("servers_cache entry was not found in cache")
            return dict()

        for cell_id in cache.copy():

            if 'timeout' not in cache[cell_id]:
                logger.debug(f"timeout was not found in servers_cache entry {cache[cell_id]}")
                cache.pop(cell_id, None)

            if 'servers' not in cache[cell_id]:
                logger.debug(f"servers was not found in servers_cache entry {cache[cell_id]}")
                cache.pop(cell_id, None)

            if time.time() > cache[cell_id]['timeout']:
                logger.debug(f"Found data in servers_cache entry but it is outdated {cache[cell_id]}")
                cache.pop(cell_id, None)

        logger.debug(f"Using server cache {str(cache)}")

        return cache

    def _store_cache(self, servers: Dict[str, int], cell_id: str):

        logger.debug(f"storing servers in cache {str(servers)} at cell {cell_id}")
        cache = self._read_cache()

        cache[cell_id] = {
            'timeout': time.time() + 86400 * 30,
            'servers': servers
        }

        self._persistent_cache['servers_cache'] = json.dumps(cache)
        self._persistent_cache_state.modified = True

    async def _test_servers(self, raw_server_list: List[str]) -> Dict[str, int]:
        async def test_server(server):
            try:
                start_time = time.time()
                websocket = await asyncio.wait_for(websockets.connect(server, ssl=self._ssl_context), 5)
                time_to_connect = time.time() - start_time
                time_to_connect = int(time_to_connect*1000)
                await websocket.close()
                logger.debug("Got ping %i for server %s", time_to_connect, server)
                return server, time_to_connect
            except (asyncio.TimeoutError, OSError, websockets.InvalidURI, websockets.InvalidHandshake):
                logger.debug("Failed to connect to %s", server)
                return server, None

        tests = [test_server(raw_server) for raw_server in raw_server_list]

        res = await asyncio.gather(*tests)

        return {server: ping for server, ping in res if ping is not None}

    async def get(self, used_cell_id: str):
        cache = self._read_cache()
        try:
            sorted_servers = cache[used_cell_id]['servers']
        except KeyError:
            raw_server_list = await self._backend_client.get_servers(used_cell_id)
            logger.debug("Got servers from backend: %s", str(raw_server_list))
            servers = await self._test_servers(
                ["wss://{}/cmsocket/".format(raw_server) for raw_server in raw_server_list]
            )
            if not servers:
                return []
            sorted_servers = sorted(servers.items(), key=itemgetter(1))
            self._store_cache(sorted_servers, used_cell_id)

        return [server for (server, ping) in sorted_servers]
