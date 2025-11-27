"""
Async UDP listener used later in Home Assistant add-on mode.
"""

import asyncio

async def start_listener(callback, host="0.0.0.0", port=6000):
    loop = asyncio.get_running_loop()

    class UDPProto(asyncio.DatagramProtocol):
        def datagram_received(self, data, addr):
            result = callback(data, addr)
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPProto(),
        local_addr=(host, port)
    )
    return transport, protocol
