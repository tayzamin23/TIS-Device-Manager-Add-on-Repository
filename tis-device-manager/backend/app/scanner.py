# scanner.py
import socket
import struct
from typing import List, Tuple, Optional

# TIS/HDL discovery request (hex)
# Header (4 bytes) 0xAA repeated, length (2 bytes), subnet(1) device(1), command(2), padding...
# This exact discovery payload was used by official DM to request device info.
DISCOVERY_PACKET = bytes.fromhex("AAAAAAA A0A0 0A00 FFFF 3300 000000000000".replace(" ", ""))

# NOTE: above hex includes spaces removed. If you want a simpler explicit form:
# DISCOVERY_PACKET = b"\xAA\xAA\xAA\xAA\x0A\x00\xFF\xFF\x33\x00\x00\x00\x00\x00\x00\x00"

# For safety, also build a proper canonical packet in code:
DISCOVERY_PACKET = b"\xAA\xAA\xAA\xAA" + struct.pack("<H", 10) + b"\xFF\xFF\x33\x00" + (b"\x00" * 6)


def _is_valid_frame(data: bytes) -> bool:
    """Very small validation: starts with AA AA AA AA and has at least a minimum length."""
    return len(data) >= 12 and data[0:4] == b"\xAA\xAA\xAA\xAA"


def parse_tis_reply(data: bytes) -> Optional[dict]:
    """
    Parse a TIS device reply frame into a dict.
    Frame layout (bytes index):
      0-3   : header 0xAA 0xAA 0xAA 0xAA
      4-5   : length (little endian)  (we won't rely heavily on it)
      6     : subnet id
      7     : device id
      8-9   : command
      10..  : payload (model, fw, channels, etc.) - variable by device
    This parser tries to extract common fields we need: subnet, device_id, command, model, fw_version
    """
    try:
        if not _is_valid_frame(data):
            return None

        # length little-endian
        length = struct.unpack_from("<H", data, 4)[0]
        # minimal check
        if length + 6 > len(data):
            # sometimes devices respond with different lengths, but continue anyway
            pass

        subnet = data[6]
        device_id = data[7]
        command = struct.unpack_from("<H", data, 8)[0]  # two bytes
        # payload begins at offset 10
        payload = data[10:]

        # Basic decode heuristics (common fields are typically at fixed offsets)
        model = None
        fw = None
        channels = None

        if len(payload) >= 2:
            # Many devices include model id at payload[0] and fw at payload[1]
            model = payload[0]
            if len(payload) >= 2:
                fw = payload[1]

        # For some devices the payload contains channel counts etc - naive attempt:
        if len(payload) >= 6:
            channels = payload[4]  # heuristic only; may not exist for all models

        return {
            "subnet": int(subnet),
            "device_id": int(device_id),
            "command": int(command),
            "model": int(model) if model is not None else None,
            "fw": int(fw) if fw is not None else None,
            "channels_hint": int(channels) if channels is not None else None,
            "raw": data.hex()
        }
    except Exception:
        return None


def probe_tis_device(ip: str, port: int = 6000, timeout: float = 0.6) -> Tuple[bool, Optional[dict]]:
    """
    Send discovery packet to ip:port and wait for a reply.
    Returns (True, parsed_dict) if reply received and parsed, else (False, None).
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        # send discovery packet
        sock.sendto(DISCOVERY_PACKET, (ip, port))

        # try to read one packet
        data, addr = sock.recvfrom(1024)
        parsed = parse_tis_reply(data)
        if parsed:
            parsed["ip"] = addr[0]
            parsed["port"] = addr[1]
            return True, parsed
        else:
            # maybe device responded with non-TIS frame; treat as not found
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


def scan_range(base_ip: str, start: int = 1, end: int = 254, port: int = 6000, timeout: float = 0.6) -> List[dict]:
    """
    Scan base_ip (like '192.168.1.') from start..end and probe each host.
    Returns list of parsed device dicts.
    """
    found = []
    # sanitize base ip
    base = base_ip
    if not base.endswith("."):
        # allow user to pass '192.168.1' or '192.168.1.'
        base = base.rstrip(".") + "."

    for i in range(start, end + 1):
        ip = f"{base}{i}"
        ok, parsed = probe_tis_device(ip, port=port, timeout=timeout)
        if ok and parsed:
            found.append(parsed)
    return found


# Optional: small CLI test
if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else "192.168.1."
    print("Scanning:", base)
    results = scan_range(base, 1, 50, timeout=0.4)
    for r in results:
        print(r)
