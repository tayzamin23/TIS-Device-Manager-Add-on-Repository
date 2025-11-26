# listener.py
import asyncio
from typing import Callable, Optional
import logging
TIS_PORT = 6000
logger = logging.getLogger(__name__)

class TISProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_frame: Optional[Callable[[bytes, tuple], None]] = None):
        self.on_frame = on_frame

    def connection_made(self, transport):
        self.transport = transport
        logger.info("TIS UDP listener ready")

    def datagram_received(self, data: bytes, addr):
        if len(data) >= 4 and data[0:4] == b"\xAA\xAA\xAA\xAA":
            if self.on_frame:
                try:
                    self.on_frame(data, addr)
                except Exception:
                    logger.exception("Error in on_frame handler")

async def start_listener(on_frame: Callable[[bytes, tuple], None], host: str = "0.0.0.0", port: int = TIS_PORT):
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: TISProtocol(on_frame=on_frame),
        local_addr=(host, port),
    )
    return transport, protocol
