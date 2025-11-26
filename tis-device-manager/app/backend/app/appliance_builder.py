# appliance_builder.py
"""
Auto-create appliance rules. Extend MODEL_MAP with model byte -> (name, channels, type)
"""
MODEL_MAP = {
    # Example model bytes - add real ones after you capture raw frames
    0x05: ("rcu_8out", 8, "switch"),
    0x07: ("dimmer_4ch", 4, "light"),
    0x10: ("temp_sensor", 1, "sensor"),
}

def build_device_entry(parsed_device: dict) -> dict:
    model = parsed_device.get("model")
    m = MODEL_MAP.get(model, ("unknown", 0, "unknown"))
    return {
        "name": f"tis_{parsed_device['subnet']}_{parsed_device['device_id']}",
        "ip": parsed_device.get("ip"),
        "subnet": parsed_device.get("subnet"),
        "device_id": parsed_device.get("device_id"),
        "type": m[0],
        "model": parsed_device.get("model"),
        "raw": parsed_device.get("raw"),
    }

def auto_create_appliances_for_device(parsed_device: dict):
    model = parsed_device.get("model")
    mname, channels, d_type = MODEL_MAP.get(model, ("unknown", parsed_device.get("channels_hint") or 1, "switch"))
    appliances = []
    subnet = parsed_device["subnet"]
    device_id = parsed_device["device_id"]
    device_ref = f"{subnet},{device_id}"
    for ch in range(1, max(1, channels) + 1):
        ap = {
            "name": f"{mname}_{subnet}_{device_id}_ch{ch}",
            "type": d_type,
            "device": device_ref,
            "channels": {"channel": ch}
        }
        appliances.append(ap)
    return appliances
