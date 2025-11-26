import socket
from typing import List

def probe_udp(host: str, port: int = 6000, timeout=0.5) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(b"", (host, port))

        try:
            data, _ = sock.recvfrom(1024)
            return True
        except socket.timeout:
            return True
    except Exception:
        return False
    finally:
        try:
            sock.close()
        except:
            pass


def scan_range(base_ip: str, start=1, end=10) -> List[dict]:
    found = []
    for i in range(start, end + 1):
        ip = f"{base_ip}{i}"
        try:
            if probe_udp(ip):
                found.append({"ip": ip, "port": 6000})
        except Exception:
            pass
    return found
