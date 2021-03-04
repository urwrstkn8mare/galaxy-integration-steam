from typing import AsyncGenerator

from websocket_cache_persistence import WebSocketCachePersistence
from websocket_list import WebSocketList


class WebSocketCache:
    def __init__(self, websocket_cache_persistence: WebSocketCachePersistence, websocket_list: WebSocketList):
        self._websocket_cache_persistence = websocket_cache_persistence
        self._websocket_list = websocket_list

    async def get(self, cell_id: int) -> AsyncGenerator[str, None]:
        cached_socket = self._websocket_cache_persistence.read(cell_id)
        if cached_socket is not None:
            yield cached_socket

        sockets = await self._websocket_list.get_ordered_by_ping(cell_id)
        for socket in sockets:
            self._websocket_cache_persistence.write(cell_id, socket)
            yield socket
