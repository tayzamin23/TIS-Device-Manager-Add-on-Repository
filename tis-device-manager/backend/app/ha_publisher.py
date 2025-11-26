import httpx

async def publish_entities(host: str, token: str, appliances: list):
    # host example: http://homeassistant.local:8123
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    created = []

    async with httpx.AsyncClient() as client:
        for a in appliances:
            # Placeholder for real HA entity creation
            created.append(a)

    return created
