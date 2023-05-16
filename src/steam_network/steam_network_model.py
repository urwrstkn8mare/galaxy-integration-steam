import asyncio
from asyncio.futures import Future
import logging
import ssl
from contextlib import suppress
from typing import Callable, Optional, Any, Dict

import websockets

from rsa import PublicKey, encrypt

class SteamNetworkModel:
    """ Class that deals with the "model" aspect of our integration with Steam Network. 

    Since our "model" is external, the majority of this class is sending and receiving messages along a websocket. The exact calls sent to and received from steam are handled by a helper. This class simply calls the helper's various functions and parses the results. These results are then returned to the Controller 

    This replaces WebsocketClient and ProtocolClient in the old code
    """
    pass
