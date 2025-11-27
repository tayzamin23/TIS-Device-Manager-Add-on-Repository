#!/usr/bin/env python3
"""
UDP sniffer for TIS protocol (port 6000).
Run this on the PC where official TIS Device Manager runs,
then press Scan in the official software.
"""

import socket, binascii, datetime, argparse, sys

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=6000)
parser.add_argument("--outfile", default="tis_packets.log")
parser.add_argument("--bind", default="0.0.0.0")
parser.add_argument("--count", type=int, default=0)
args = parser.parse_args()

PORT = args.port
OUT = args.outfile
BIND = args.bind
COUNT_LIMIT = args.count

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    sock.bind((BIND, PORT))
except Exception as e:
    print("ERROR: Cannot bind to UDP port", PORT)
    print("Reason:", e)
    print("If official TIS software is running, stop it first.")
    sys.exit(1)

print(f"Sniffer listening on UDP {BIND}:{PORT}")
print(f"Logging to {OUT}")

cnt = 0
with open(OUT, "a") as f:
    while True:
        data, addr = sock.recvfrom(65535)
        ts = datetime.datetime.now().isoformat()
        hexdata = binascii.hexlify(data).decode()

        entry = f"{ts} {addr[0]}:{addr[1]} -> {BIND}:{PORT} (len={len(data)})\n{hexdata}\n\n"
        f.write(entry)
        f.flush()
        print(entry)

        cnt += 1
        if COUNT_LIMIT and cnt >= COUNT_LIMIT:
            break
