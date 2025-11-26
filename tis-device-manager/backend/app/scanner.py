# scanner.py
import socket
import struct
from typing import List, Optional, Tuple

# Proper TIS discovery request frame (header + length + broadcast subnet+device + cmd + padding)
DISCOVERY_PACKET = b"\xAA\xAA\xAA\xAA" + struct.pack("<H", 10) + b"\xFF\xFF\x33\x00" + (b"\x00" * 6)
TIS_PORT = 6000

def _is_valid_frame(data: bytes) -> bool:
    return len(data) >= 12 and data[0:4] == b"\xAA\xAA\xAA\xAA"


def parse_tis_reply(data: bytes) -> Optional[dict]:
    """
    Parse a TIS device reply frame into a dict.
    This extracts: subnet, device_id, command, model byte (if present), fw byte (if present),
    and returns raw hex.
    """
    try:
        if not _is_valid_frame(data):
            return None

        length = struct.unpack_from("<H", data, 4)[0]
        subnet = data[6]
        device_id = data[7]
        command = struct.unpack_from("<H", data, 8)[0]
        payload = data[10:]

        model = None
        fw = None
        channels_hint = None

        if len(payload) >= 1:
            model = payload[0]
        if len(payload) >= 2:
            fw = payload[1]
        # heuristic: some replies encode channel count or other hints in payload[4] or payload[5]
        if len(payload) >= 6:
            channels_hint = payload[4]

        return {
            "subnet": int(subnet),
            "device_id": int(device_id),
            "command": int(command),
            "model": int(model) if model is not None else None,
            "fw": int(fw) if fw is not None else None,
            "channels_hint": int(channels_hint) if channels_hint is not None else None,
            "raw": data.hex()
        }
    except Exception:
        return None


def probe_ip_for_tis(ip: str, timeout: float = 0.6) -> Tuple[bool, Optional[dict]]:
    """
    Send a discovery packet to a single IP and wait for one reply.
    If a TIS reply is returned, parse and return it.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(DISCOVERY_PACKET, (ip, TIS_PORT))
        data, addr = sock.recvfrom(1024)
        parsed = parse_tis_reply(data)
        if parsed:
            parsed["ip"] = addr[0]
            parsed["port"] = addr[1]
            return True, parsed
        return False, None
    except socket.timeout:
        return False, None
    except Exception:
        return False, None
    finally:
        try:
            sock.close()
        except:
            pass


def find_ip_comport_in_range(base_ip: str = "192.168.110.", start: int = 1, end: int = 254, timeout: float = 0.45) -> List[str]:
    """
    Brute force discovery of the IP-COM device: returns list of IPs that respond with TIS frames.
    Use a narrow range (e.g., 192.168.110.1..254) for faster results.
    """
    def _ip(i: int) -> str:
        return f"{base_ip.rstrip('.')}.{i}"

    found = []
    for i in range(start, end + 1):
        ip = _ip(i)
        ok, parsed = probe_ip_for_tis(ip, timeout=timeout)
        if ok:
            found.append(ip)
    return found


def discover_bus_via_ip_com(ip_com_ip: str, timeout: float = 1.0) -> List[dict]:
    """
    Send a discovery frame TO THE IP-COM address and read all replies from the bus until timeout.
    Returns list of parsed device dicts (subnet/device/model/etc).
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    discovered = []
    try:
        sock.sendto(DISCOVERY_PACKET, (ip_com_ip, TIS_PORT))

        while True:
            try:
                data, addr = sock.recvfrom(2048)
                parsed = parse_tis_reply(data)
                if parsed:
                    parsed["ip"] = addr[0]
                    parsed["port"] = addr[1]
                    discovered.append(parsed)
            except socket.timeout:
                break
    finally:
        try:
            sock.close()
        except:
            pass

    # deduplicate by subnet+device_id
    unique = {}
    for d in discovered:
        key = (d["subnet"], d["device_id"])
        if key not in unique:
            unique[key] = d
    return list(unique.values())


# Small CLI support for local testing
if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "discover"
    if mode == "find":
        base = sys.argv[2] if len(sys.argv) > 2 else "192.168.110."
        print("Searching IP-COM in range", base + "1..50")
        print(find_ip_comport_in_range(base, 1, 50))
    else:
        ip = sys.argv[2] if len(sys.argv) > 2 else "192.168.110.205"
        print("Discovering bus via", ip)
        print(discover_bus_via_ip_com(ip))
