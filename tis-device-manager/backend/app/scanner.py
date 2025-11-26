import socket
from typing import List

# Simple network probe for hosts with open UDP/TCP at port 6000
# This is a placeholder. Replace with real TIS discovery logic.

def probe_udp(host: str, port: int = 6000, timeout=0.5) -> bool:
# Create a UDP socket and try to send an empty packet
try:
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(timeout)
sock.sendto(b"", (host, port))
# some devices may not respond — try to recv
try:
data, _ = sock.recvfrom(1024)
return True
except socket.timeout:
# no response; still may be alive — we'll treat send success as reachable
return True
except Exception:
return False
finally:
try:
sock.close()
except:
pass

def scan_range(base_ip: str, start=1, end=10) -> List[dict]:
# base_ip like '192.168.1.'
found = []
for i in range(start, end + 1):
ip = f"{base_ip}{i}"
try:
if probe_udp(ip):
found.append({"ip": ip, "port": 6000})
except Exception:
pass
return found
