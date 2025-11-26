# ha_publisher.py
import httpx
import asyncio
import re
from typing import List

async def publish_entities(host: str, token: str, appliances: List[dict]):
    """
    Publish appliances to Home Assistant by creating states for entity ids.
    host: e.g. "http://homeassistant.local:8123"
    token: Long-lived access token
    """
    created = []
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    host = host.rstrip("/")

    async with httpx.AsyncClient(verify=False, timeout=10) as client:
        tasks = []
        for ap in appliances:
            tasks.append(_create_or_update_entity(client, host, headers, ap))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, dict) and r.get("entity_id"):
                created.append(r["entity_id"])
    return created

def _normalize_name(name: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "", name.replace(" ", "_").lower())
    if not safe:
        safe = "unnamed"
    return safe

async def _create_or_update_entity(client: httpx.AsyncClient, host: str, headers: dict, ap: dict):
    name = ap.get("name", "unnamed")
    safe = _normalize_name(name)
    entity_id = f"tis.{safe}"

    typ = ap.get("type", "switch")
    initial = "off" if typ in ("switch", "light") else "unknown"

    attributes = {
        "friendly_name": ap.get("name"),
        "tis_device": ap.get("device"),
        "tis_channels": ap.get("channels"),
        "custom_type": typ,
    }

    url = f"{host}/api/states/{entity_id}"
    payload = {"state": initial, "attributes": attributes}

    r = await client.post(url, headers=headers, json=payload)
    if r.status_code in (200, 201):
        return {"entity_id": entity_id}
    else:
        # return error info for debugging
        text = None
        try:
            text = r.text
        except Exception:
            text = "<no text>"
        return {"error": r.status_code, "text": text, "entity_id": entity_id}


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
