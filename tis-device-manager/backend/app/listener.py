# listener.py
import asyncio
from typing import Callable, Optional

TIS_PORT = 6000

class TISProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_frame: Optional[Callable[[bytes, tuple], None]] = None):
        self.on_frame = on_frame
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        # call handler for TIS frames (only frames with 0xAAAA.. header)
        if len(data) >= 4 and data[0:4] == b"\xAA\xAA\xAA\xAA":
            if self.on_frame:
                try:
                    self.on_frame(data, addr)
                except Exception:
                    pass

async def start_listener(on_frame: Callable[[bytes, tuple], None], host: str = "0.0.0.0", port: int = TIS_PORT):
    """
    Start an asyncio UDP listener. Caller should store the transport/protocol to close on shutdown.
    """
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: TISProtocol(on_frame=on_frame),
        local_addr=(host, port),
    )
    return transport, protocol
