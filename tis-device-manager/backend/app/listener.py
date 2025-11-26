# listener.py
import asyncio
from typing import Callable, Optional
import struct

TIS_PORT = 6000

class TISProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_frame: Optional[Callable[[bytes, tuple], None]] = None):
        self.on_frame = on_frame

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        # basic filter
        if len(data) >= 4 and data[0:4] == b"\xAA\xAA\xAA\xAA":
            if self.on_frame:
                try:
                    self.on_frame(data, addr)
                except Exception:
                    pass

async def start_listener(on_frame: Callable[[bytes, tuple], None], host: str = "0.0.0.0", port: int = TIS_PORT):
    """Start listener that calls on_frame(data, addr) for each inbound TIS frame."""
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: TISProtocol(on_frame=on_frame),
        local_addr=(host, port)
    )
    return transport, protocol

# Example usage:
# async def on_frame(data, addr):
#     print("Got frame from", addr, data.hex())
#
# asyncio.run(start_listener(on_frame))
