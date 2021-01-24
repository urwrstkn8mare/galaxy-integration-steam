import ssl
from typing import Dict, Any, List

from backend import SteamHttpClient
from persistent_cache_state import PersistentCacheState
from websocket_cache_persistence import WebSocketCachePersistence
from websocket_list import WebSocketList


class WebSocketCache:
    def __init__(self,
                 persistent_cache: Dict[str, Any],
                 persistent_cache_state: PersistentCacheState,
                 steam_http_client: SteamHttpClient,
                 ssl_context: ssl.SSLContext,
                 ):
        self._websocket_cache_persistence = WebSocketCachePersistence(persistent_cache, persistent_cache_state)
        self._websocket_list = WebSocketList(steam_http_client, ssl_context)

    async def get(self, cell_id: int) -> List[str]:
        yield self._websocket_cache_persistence.read(cell_id)
        sockets = await self._websocket_list.get_ordered_by_ping(cell_id)
        for socket in sockets:
            self._websocket_cache_persistence.write(socket)
            yield socket
