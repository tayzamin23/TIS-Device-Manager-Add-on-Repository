# ha_publisher.py
import httpx
import re

def _normalize_name(name: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "", name.replace(" ", "_").lower())
    if not safe:
        safe = "unnamed"
    return safe

async def publish_entities(host: str, token: str, appliances: list):
    host = host.rstrip("/")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    created = []
    async with httpx.AsyncClient(verify=False, timeout=10) as client:
        for ap in appliances:
            safe = _normalize_name(ap.get("name", "unnamed"))
            entity_id = f"tis.{safe}"
            typ = ap.get("type", "switch")
            state = "off" if typ in ("switch", "light") else "unknown"
            attributes = {
                "friendly_name": ap.get("name"),
                "tis_device": ap.get("device"),
                "tis_channels": ap.get("channels"),
                "custom_type": typ,
            }
            url = f"{host}/api/states/{entity_id}"
            payload = {"state": state, "attributes": attributes}
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code in (200, 201):
                created.append(entity_id)
    return created

async def update_entity_state(host: str, token: str, entity_id: str, state: str, attributes: dict = None):
    host = host.rstrip("/")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"state": state}
    if attributes:
        payload["attributes"] = attributes
    async with httpx.AsyncClient(verify=False, timeout=8) as client:
        url = f"{host}/api/states/{entity_id}"
        r = await client.post(url, headers=headers, json=payload)
        return r.status_code, r.text

