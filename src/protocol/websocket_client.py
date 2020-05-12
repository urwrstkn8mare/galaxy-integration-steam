import asyncio
import logging
import ssl
from typing import Optional

import websockets
from galaxy.api.errors import BackendNotAvailable, BackendTimeout, BackendError, NetworkError

from backend import SteamHttpClient
from protocol.protocol_client import ProtocolClient, UserActionRequired
from servers_cache import ServersCache
from friends_cache import FriendsCache
from games_cache import GamesCache
from stats_cache import StatsCache
from user_info_cache import UserInfoCache
from contextlib import suppress
from times_cache import TimesCache


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
        stats_cache: StatsCache,
        times_cache: TimesCache,
        user_info_cache: UserInfoCache,
        _store_credentials
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
        self._user_info_cache = user_info_cache

        self._store_credentials = _store_credentials
        self.communication_queues = {'plugin': asyncio.Queue(), 'websocket': asyncio.Queue(), 'errors': asyncio.Queue()}
        self._times_cache = times_cache


    async def run(self):
        loop = asyncio.get_running_loop()
        while True:
            try:
                await self._ensure_connected()

                run_task = asyncio.create_task(self._protocol_client.run())
                auth_lost = loop.create_future()
                auth_task = asyncio.create_task(self._authenticate(auth_lost))
                pending = None
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
                    with suppress(asyncio.CancelledError):
                        if pending is not None:
                            for task in pending:
                                task.cancel()
                                await task
                    raise
            except asyncio.CancelledError as e:
                logger.warning(f"Websocket task cancelled {repr(e)}")
                await self.communication_queues['errors'].put(e)
                raise
            except websockets.ConnectionClosedOK:
                logger.debug("Expected WebSocket disconnection")
                await self._close_socket()
                await self._close_protocol_client()
                continue
            except websockets.ConnectionClosedError as error:
                logger.warning("WebSocket disconnected (%d: %s), reconnecting...", error.code, error.reason)
                await self._close_socket()
                await self._close_protocol_client()
                continue
            except (BackendNotAvailable, BackendTimeout, BackendError, NetworkError):
                logger.exception(
                    "Failed to establish authenticated WebSocket connection, retrying after %d seconds",
                    RECONNECT_INTERVAL_SECONDS
                )
                await asyncio.sleep(RECONNECT_INTERVAL_SECONDS)
                continue
            except Exception as e:
                logger.exception(f"Failed to establish authenticated WebSocket connection {repr(e)}")
                await self.communication_queues['errors'].put(e)
                raise

    async def _close_socket(self):
        if self._websocket is not None:
            logger.info("Closing websocket")
            await self._websocket.close()
            await self._websocket.wait_closed()
            self._websocket = None

    async def _close_protocol_client(self):
        is_socket_connected = True if self._websocket else False
        if self._protocol_client is not None:
            logger.info("Closing protocol client")
            await self._protocol_client.close(is_socket_connected)
            await self._protocol_client.wait_closed()
            self._protocol_client = None

    async def close(self):
        is_socket_connected = True if self._websocket else False
        if self._protocol_client is not None:
            await self._protocol_client.close(is_socket_connected)
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

    async def get_friends_nicknames(self):
        await self._friends_cache.wait_nicknames_ready()
        return self._friends_cache.get_nicknames()

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

    async def refresh_game_times(self):
        self._times_cache.start_game_times_import()
        await self._protocol_client.import_game_times()

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
                    self._protocol_client = ProtocolClient(self._websocket, self._friends_cache, self._games_cache, self._translations_cache, self._stats_cache, self._times_cache,self._user_info_cache)
                    return
                except (asyncio.TimeoutError, OSError, websockets.InvalidURI, websockets.InvalidHandshake):
                    continue

            logger.exception(
                "Failed to connect to any server, reconnecting in %d seconds...",
                RECONNECT_INTERVAL_SECONDS
            )
            await asyncio.sleep(RECONNECT_INTERVAL_SECONDS)

    async def _authenticate(self, auth_lost_future):
        async def auth_lost_handler(error):
            logger.warning("WebSocket client authentication lost")
            auth_lost_future.set_exception(error)
        password = None
        two_factor = None
        try:
            # TODO: Remove - Steamcommunity auth element
            if self._user_info_cache.old_flow:
                steam_id, miniprofile_id, account_name, token = await self._backend_client.get_authentication_data()
                return await self._protocol_client.authenticate_web_auth(steam_id, miniprofile_id, account_name, token, auth_lost_handler)

            if self._user_info_cache.token:
                ret_code = await self._protocol_client.authenticate_token(self._user_info_cache.steam_id, self._user_info_cache.account_username, self._user_info_cache.token, auth_lost_handler)
            else:
                ret_code = None
                while ret_code != UserActionRequired.NoActionRequired:
                    if ret_code != None:
                        await self.communication_queues['plugin'].put({'auth_result': ret_code})
                        logger.info(f"Put {ret_code} in the queue, waiting for other side to receive")
                    response = await self.communication_queues['websocket'].get()
                    logger.info(f" Got {response.keys()} from queue")
                    if 'password' in response:
                        password = response['password']
                    if 'two_factor' in response:
                        two_factor = response['two_factor']
                    logger.info(f'Authenticating with {"username" if self._user_info_cache.account_username else ""}, {"password" if password else ""}, {"two_factor" if two_factor else ""}')
                    ret_code = await self._protocol_client.authenticate_password(self._user_info_cache.account_username, password, two_factor, self._user_info_cache.two_step, auth_lost_handler)
                    logger.info(f"Response from auth {ret_code}")
            logger.info("Finished authentication")
            password = None
            await self.communication_queues['plugin'].put({'auth_result': ret_code})
        except Exception as e:
            await self.communication_queues['errors'].put(e)
            raise e


