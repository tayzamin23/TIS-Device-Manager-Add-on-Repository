# generator.py
from typing import Dict, List

# Example mapping: model byte -> (device_type, default_channels)
# Extend with the model bytes you capture from your hardware replies.
MODEL_MAP = {
    0x05: ("rcu_8out", 8),     # example model id for 8-out relay
    0x07: ("dimmer_4ch", 4),   # example dimmer
    0x10: ("temp_sensor", 1),  # example sensor
    # Add new entries once you observe 'model' bytes from real devices
}

def build_device_entry(parsed_device: dict) -> dict:
    """Return a consistent device entry to store in project devices list."""
    model = parsed_device.get("model")
    device_type = MODEL_MAP.get(model, ("unknown", 0))[0]
    return {
        "name": f"tis_{parsed_device['subnet']}_{parsed_device['device_id']}",
        "ip": parsed_device.get("ip"),
        "subnet": parsed_device.get("subnet"),
        "device_id": parsed_device.get("device_id"),
        "type": device_type,
        "model": parsed_device.get("model"),
        "raw": parsed_device.get("raw"),
    }

def auto_create_appliances_for_device(parsed_device: dict) -> List[dict]:
    """
    Generate appliance entries (simple default mapping).
    Each appliance dict matches your Project schema: name, type, device, channels
    """
    model = parsed_device.get("model")
    device_type, default_channels = MODEL_MAP.get(model, ("unknown", 0))

    appliances = []
    subnet = parsed_device["subnet"]
    device_id = parsed_device["device_id"]
    device_ref = f"{subnet},{device_id}"

    if device_type.startswith("rcu"):
        for ch in range(1, max(1, default_channels) + 1):
            appliances.append({
                "name": f"{device_type}_{subnet}_{device_id}_ch{ch}",
                "type": "switch",
                "device": device_ref,
                "channels": {"channel": ch}
            })
    elif device_type.startswith("dimmer"):
        for ch in range(1, max(1, default_channels) + 1):
            appliances.append({
                "name": f"{device_type}_{subnet}_{device_id}_ch{ch}",
                "type": "light",
                "device": device_ref,
                "channels": {"channel": ch}
            })
    elif device_type.startswith("temp") or device_type.startswith("sensor"):
        appliances.append({
            "name": f"{device_type}_{subnet}_{device_id}",
            "type": "sensor",
            "device": device_ref,
            "channels": {"channel": 1}
        })
    else:
        # fallback: create generic switch entities for hints
        hint = parsed_device.get("channels_hint") or 1
        for ch in range(1, max(1, hint) + 1):
            appliances.append({
                "name": f"unknown_{subnet}_{device_id}_ch{ch}",
                "type": "switch",
                "device": device_ref,
                "channels": {"channel": ch}
            })

    return appliances
