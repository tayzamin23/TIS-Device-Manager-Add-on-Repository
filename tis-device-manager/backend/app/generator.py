# generator.py
from typing import Dict, List

# A simple model -> device_type mapping (extend this table as you identify models)
MODEL_MAP = {
    # model_id: (device_type_str, default_channels)
    0x05: ("rcu", 8),   # example RCU 8-out
    0x07: ("dimmer", 4),
    0x10: ("sensor", 1),
    # add as you decode more device models
}

def build_device_entry(parsed_device: dict) -> dict:
    """Construct a consistent device entry for project.json devices list."""
    return {
        "name": f"tis_{parsed_device['subnet']}_{parsed_device['device_id']}",
        "ip": parsed_device.get("ip"),
        "subnet": parsed_device.get("subnet"),
        "device_id": parsed_device.get("device_id"),
        "type": MODEL_MAP.get(parsed_device.get("model"), ("unknown", 0))[0],
        "model": parsed_device.get("model"),
        "raw": parsed_device.get("raw"),
    }

def auto_create_appliances_for_device(parsed_device: dict) -> List[dict]:
    """
    Generate appliance entries for a parsed device.
    Returns list of appliance dicts to add to project.
    """
    model = parsed_device.get("model")
    device_type, default_channels = MODEL_MAP.get(model, ("unknown", 0))

    appliances = []

    base_name = f"{device_type}_{parsed_device['subnet']}_{parsed_device['device_id']}"

    if device_type == "rcu":
        # create N switches
        for ch in range(1, default_channels + 1):
            appliances.append({
                "name": f"{base_name}_ch{ch}",
                "type": "switch",
                "device": parsed_device.get("ip") or f"{parsed_device['subnet']},{parsed_device['device_id']}",
                "channels": {"channel": ch}
            })
    elif device_type == "dimmer":
        for ch in range(1, default_channels + 1):
            appliances.append({
                "name": f"{base_name}_dim{ch}",
                "type": "light",
                "device": parsed_device.get("ip") or f"{parsed_device['subnet']},{parsed_device['device_id']}",
                "channels": {"channel": ch}
            })
    elif device_type == "sensor":
        appliances.append({
            "name": f"{base_name}_sensor",
            "type": "sensor",
            "device": parsed_device.get("ip"),
            "channels": {"channel": 1}
        })
    else:
        # fallback: create a generic entity for each channel_hint if present
        ch_hint = parsed_device.get("channels_hint") or 1
        for ch in range(1, max(1, ch_hint) + 1):
            appliances.append({
                "name": f"{base_name}_ch{ch}",
                "type": "switch",
                "device": parsed_device.get("ip") or f"{parsed_device['subnet']},{parsed_device['device_id']}",
                "channels": {"channel": ch}
            })

    return appliances
