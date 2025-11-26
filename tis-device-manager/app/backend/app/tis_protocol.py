# tis_protocol.py
import struct

# Build discovery packet: header + length + broadcast subnet+device + cmd33 + padding
DISCOVERY_PACKET = b"\xAA\xAA\xAA\xAA" + struct.pack("<H", 10) + b"\xFF\xFF\x33\x00" + (b"\x00" * 6)

def is_tis_frame(data: bytes) -> bool:
    return isinstance(data, (bytes, bytearray)) and len(data) >= 12 and data[0:4] == b"\xAA\xAA\xAA\xAA"

def parse_device_info_frame(data: bytes) -> dict:
    """
    Conservative parser for device info reply frames.
    Returns dict with keys: subnet, device_id, command, model, fw, channels_hint, raw
    """
    if not is_tis_frame(data):
        return {}
    length = struct.unpack_from("<H", data, 4)[0]
    subnet = data[6]
    device_id = data[7]
    command = struct.unpack_from("<H", data, 8)[0]
    payload = data[10:]
    model = payload[0] if len(payload) >= 1 else None
    fw = payload[1] if len(payload) >= 2 else None
    channels_hint = payload[4] if len(payload) >= 6 else None
    return {
        "subnet": int(subnet),
        "device_id": int(device_id),
        "command": int(command),
        "model": int(model) if model is not None else None,
        "fw": int(fw) if fw is not None else None,
        "channels_hint": int(channels_hint) if channels_hint is not None else None,
        "raw": data.hex()
    }
