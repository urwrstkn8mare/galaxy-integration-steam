import asyncio
import time
import logging
import ssl
from operator import itemgetter
from typing import Dict, List, Any

import websockets
import certifi

from backend import SteamHttpClient


logger = logging.getLogger(__name__)

class ServersCache:
    def __init__(self, backend_client: SteamHttpClient, persistent_cache: Dict[str, Any], persistent_cache_update_event):
        self._backend_client = backend_client
        self._persistent_cache = persistent_cache
        self._persistent_cache_update_event = persistent_cache_update_event

    def _read_cache(self):
        if 'servers_cache' not in self._persistent_cache:
            logger.debug("servers_cache entry was not found in cache")
            return None

        cache = self._persistent_cache['servers_cache']

        if 'timeout' not in cache:
            logger.debug("timeout was not found in servers_cache entry")
            return None

        if 'servers' not in cache:
            logger.debug("servers was not found in servers_cache entry")
            return None

        if time.time() > cache['timeout']:
            logger.debug("Found data in servers_cache entry but it is outdated")
            return None

        servers = cache['servers']
        logger.debug("Found servers in servers_cache entry %s", str(servers))

        return servers

    def _store_cache(self, servers: Dict[str, int]):

        logger.debug("storing servers in cache %s", str(servers))

        servers_cache = {
            'timeout': time.time() + 86400 * 30,
            'servers': servers
        }

        self._persistent_cache['servers_cache'] = servers_cache
        self._persistent_cache_update_event.set()

    async def _test_servers(self, raw_server_list: List[str]) -> Dict[str, int]:
        async def test_server(server):
            try:
                start_time = time.time()
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_context.load_verify_locations(certifi.where())
                websocket = await asyncio.wait_for(websockets.connect(server, ssl=ssl_context), 5)
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

    async def get(self):
        sorted_servers = self._read_cache()

        if not sorted_servers:
            raw_server_list = await self._backend_client.get_servers()
            logger.debug("Got servers from backend: %s", str(raw_server_list))
            servers = await self._test_servers(
                ["wss://{}/cmsocket/".format(raw_server) for raw_server in raw_server_list]
            )
            if not servers:
                return []
            sorted_servers = sorted(servers.items(), key=itemgetter(1))
            self._store_cache(sorted_servers)

        return [server for (server, ping) in sorted_servers]
