"""
Simple broadcast scanner for TIS devices.
Will be improved after we decode real packet structure.
"""

import socket
from .tis_protocol import build_frame, parse_frame

def broadcast_discover(broadcast_ip="255.255.255.255", port=6000, timeout=2.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("0.0.0.0", 0))

    # Discovery frame guess: AA AA FF FF 01 (needs confirmation from sniffer)
    frame = build_frame(0xAA, 0xAA, 0xFF, 0xFF, 0x01)

    sock.sendto(frame, (broadcast_ip, port))
    sock.settimeout(timeout)

    devices = []
    try:
        while True:
            data, addr = sock.recvfrom(4096)
            parsed = parse_frame(data)
            devices.append((addr, parsed, data))
    except socket.timeout:
        pass

    return devices
