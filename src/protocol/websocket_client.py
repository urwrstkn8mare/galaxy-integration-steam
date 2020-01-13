import asyncio
import logging
import ssl
from typing import Optional

import websockets
from galaxy.api.errors import BackendNotAvailable, BackendTimeout, BackendError, NetworkError

from backend import SteamHttpClient
from protocol.protocol_client import ProtocolClient
from servers_cache import ServersCache
from friends_cache import FriendsCache
from games_cache import GamesCache
from stats_cache import StatsCache


logger = logging.getLogger(__name__)
# do not log low level events from websockets
logging.getLogger("websockets").setLevel(logging.WARNING)

RECONNECT_INTERVAL_SECONDS = 20


class WebSocketClient:
    def __init__(
        self,
        backend_client: SteamHttpClient,
        ssl_context: ssl.SSLContext,
        servers_cache: ServersCache,
        friends_cache: FriendsCache,
        games_cache: GamesCache,
        translations_cache: dict,
        stats_cache: StatsCache
    ):
        self._backend_client = backend_client
        self._ssl_context = ssl_context
        self._servers_cache = servers_cache
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._protocol_client: Optional[ProtocolClient] = None

        self._friends_cache = friends_cache
        self._games_cache = games_cache
        self._translations_cache = translations_cache
        self._stats_cache = stats_cache

    async def run(self):
        loop = asyncio.get_running_loop()
        while True:
            try:
                await self._ensure_connected()

                run_task = asyncio.create_task(self._protocol_client.run())
                auth_lost = loop.create_future()
                auth_task = asyncio.create_task(self._authenticate(auth_lost))
                try:
                    done, pending = await asyncio.wait({run_task, auth_task}, return_when=asyncio.FIRST_COMPLETED)
                    if auth_task in done:
                        await auth_task

                    done, pending = await asyncio.wait({run_task, auth_lost}, return_when=asyncio.FIRST_COMPLETED)
                    if auth_lost in done:
                        await auth_lost

                    assert run_task in done
                    await run_task
                    break
                except Exception:
                    for task in pending:
                        task.cancel()
                    raise
            except asyncio.CancelledError:
                raise
            except websockets.ConnectionClosedOK:
                logger.debug("Expected WebSocket disconnection")
                break
            except websockets.ConnectionClosedError as error:
                logger.warning("WebSocket disconnected (%d: %s), reconnecting...", error.code, error.reason)
                await self._disconnect()
                continue
            except (BackendNotAvailable, BackendTimeout, BackendError, NetworkError):
                logger.exception(
                    "Failed to establish authenticated WebSocket connection, retrying after %d seconds",
                    RECONNECT_INTERVAL_SECONDS
                )
                await asyncio.sleep(RECONNECT_INTERVAL_SECONDS)
                continue
            except Exception:
                logger.exception("Failed to establish authenticated WebSocket connection")
                break

    async def close(self):
        if self._protocol_client is not None:
            await self._protocol_client.close()
        if self._websocket is not None:
            await self._websocket.close()

    async def wait_closed(self):
        if self._protocol_client is not None:
            await self._protocol_client.wait_closed()
        if self._websocket is not None:
            await self._websocket.wait_closed()

    async def get_friends(self):
        await self._friends_cache.wait_ready()
        return [str(user_id) for user_id in self._friends_cache.get_keys()]

    async def get_friends_info(self, users):
        await self._friends_cache.wait_ready()
        result = {}
        for user_id in users:
            int_user_id = int(user_id)
            user_info = self._friends_cache.get(int_user_id)
            if user_info is not None:
                result[user_id] = user_info
        return result

    async def refresh_game_stats(self, game_ids):
        self._stats_cache.start_game_stats_import(game_ids)
        await self._protocol_client.import_game_stats(game_ids)

    async def retrieve_collections(self):
        return await self._protocol_client.retrieve_collections()

    async def _ensure_connected(self):
        if self._protocol_client is not None:
            return  # already connected

        while True:
            servers = await self._servers_cache.get()
            for server in servers:
                try:
                    self._websocket = await asyncio.wait_for(websockets.connect(server, ssl=self._ssl_context), 5)
                    self._protocol_client = ProtocolClient(self._websocket, self._friends_cache, self._games_cache, self._translations_cache, self._stats_cache)
                    return
                except (asyncio.TimeoutError, OSError, websockets.InvalidURI, websockets.InvalidHandshake):
                    continue

            logger.exception(
                "Failed to connect to any server, reconnecting in %d seconds...",
                RECONNECT_INTERVAL_SECONDS
            )
            await asyncio.sleep(RECONNECT_INTERVAL_SECONDS)

    async def _disconnect(self):
        if self._protocol_client is not None:
            await self._protocol_client.close()
            await self._protocol_client.wait_closed()
            self._protocol_client = None
        if self._websocket is not None:
            await self._websocket.close()
            await self._websocket.wait_closed()
            self._websocket = None

    async def _authenticate(self, auth_lost_future):
        async def auth_lost_handler(error):
            logger.warning("WebSocket client authentication lost")
            auth_lost_future.set_exception(error)

        steam_id, miniprofile_id, account_name, token = await self._backend_client.get_authentication_data()
        await self._protocol_client.authenticate(steam_id, miniprofile_id, account_name, token, auth_lost_handler)
