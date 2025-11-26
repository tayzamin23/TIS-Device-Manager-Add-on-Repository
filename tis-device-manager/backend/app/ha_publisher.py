import httpx

async def publish_entities(host, token, appliances):
    url = f"{host}/api/states"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    created = []

    async with httpx.AsyncClient(verify=False, timeout=5) as client:
        for ap in appliances:
            entity_id = f"tis.{ap['name'].replace(' ','_').lower()}"
            data = {
                "entity_id": entity_id,
                "attributes": ap
            }
            r = await client.post(url, headers=headers, json=data)
            created.append(entity_id)

    return created
