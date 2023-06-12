import asyncio
from asyncio.futures import Future
import ssl
from contextlib import suppress
from typing import Callable, Optional, Any, Dict

import websockets
from galaxy.api.errors import BackendNotAvailable, BackendTimeout, BackendError, InvalidCredentials, NetworkError, AccessDenied, AuthenticationRequired

import logging
from traceback import format_exc
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
from websockets.typing import Data

from .protocol.protocol_parser import ProtocolParser, FutureInfo

logger = logging.getLogger(__name__)

logging.getLogger("websockets").setLevel(logging.WARNING)



def asyncio_future() -> Future:
    loop = asyncio.get_event_loop()
    return loop.create_future()

class SteamNetworkModel:
    def __init__(self):
        self._websocket : WebSocketClientProtocol = None
        self._parser : ProtocolParser = None
    """ Class that deals with the "model" aspect of our integration with Steam Network. 

    Since our "model" is external, the majority of this class is sending and receiving messages along a websocket. The exact calls sent to and received from steam are handled by a helper. This class simply calls the helper's various functions and parses the results. These results are then returned to the Controller 

    This replaces WebsocketClient and ProtocolClient in the old code
    """
    async def run(self):
        while True:
            try:
                await self._ensure_connected()

                run_task = asyncio.create_task(self._receive_loop())
                auth_lost = create_future_factory()
                auth_task = asyncio.create_task(self._all_auth_calls(auth_lost))
                pending = None
                try:
                    done, pending = await asyncio.wait({run_task, auth_task}, return_when=asyncio.FIRST_COMPLETED)
                    if auth_task in done:
                        await auth_task

                    done, pending = await asyncio.wait({run_task, auth_lost}, return_when=asyncio.FIRST_COMPLETED)
                    if auth_lost in done:
                        try:
                            await auth_lost
                        except (InvalidCredentials, AccessDenied) as e:
                            logger.warning(f"Auth lost by a reason: {repr(e)}")
                            await self._close_socket()
                            await self._close_protocol_client()
                            run_task.cancel()
                            run_task = None
                            break

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
                raise
            except websockets.exceptions.ConnectionClosedOK as e:
                logger.debug(format_exc())
                logger.debug("Expected WebSocket disconnection")
            except websockets.exceptions.ConnectionClosedError as error:
                logger.warning("WebSocket disconnected (%d: %s), reconnecting...", error.code, error.reason)
            except websockets.exceptions.InvalidState as error:
                logger.warning(f"WebSocket is trying to connect... {repr(error)}")
            except (BackendNotAvailable, BackendTimeout, BackendError) as error:
                logger.warning(f"{repr(error)}. Trying with different CM...")
                self._websocket_list.add_server_to_ignored(self._current_ws_address, timeout_sec=BLACKLISTED_CM_EXPIRATION_SEC)
            except NetworkError as error:
                logger.error(
                    f"Failed to establish authenticated WebSocket connection: {repr(error)}, retrying after %d seconds",
                    RECONNECT_INTERVAL_SECONDS
                )
                await sleep(RECONNECT_INTERVAL_SECONDS)
                continue
            except AuthenticationRequired:
                logger.error("Authentication lost mid use. Restarting the socket, auth, and run loops")
                #Interface checks if user name is info cache and raises an authentication required if it's note there. 
                #Clearing the cache here will result in that error being raised, which lets gog know to redo auth.
                self._user_info_cache.Clear() 
            except Exception as e:
                logger.error(f"Failed to establish authenticated WebSocket connection {repr(e)}")
                logger.error(format_exc())
                raise

            await self._close_socket()
            await self._close_protocol_client()

    async def _receive_loop(self):
        try:
            async for message in self._websocket:
                await self._process_packet(message)
        except (ConnectionClosed, ConnectionClosedError) as e:
            pass


    async def _process_packet(self, message: Data):
        await self._parser.process_packet(message)
