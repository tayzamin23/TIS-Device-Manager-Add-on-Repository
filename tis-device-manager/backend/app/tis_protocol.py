"""
Minimal TIS protocol builder + parser.
This will be improved once real packets are captured.
"""

def build_frame(header1=0xAA, header2=0xAA, subnet=0x01, device=0x01, opcode=0x00, data=None):
    data = data or []
    frame = bytearray()
    frame.append(header1 & 0xFF)
    frame.append(header2 & 0xFF)
    frame.append(subnet & 0xFF)
    frame.append(device & 0xFF)
    frame.append(opcode & 0xFF)
    for b in data:
        frame.append(b & 0xFF)
    return bytes(frame)

def hexdump(b: bytes) -> str:
    return b.hex()

def parse_frame(b: bytes):
    if len(b) < 5:
        return None
    header = (b[0], b[1])
    subnet = b[2]
    device = b[3]
    opcode = b[4]
    payload = b[5:]
    return {
        "header": header,
        "subnet": subnet,
        "device": device,
        "opcode": opcode,
        "payload": payload
    }
