import httpx

async def publish_entities(host: str, token: str, appliances: list):
# host example: http://homeassistant.local:8123
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
created = []
async with httpx.AsyncClient() as client:
for a in appliances:
# Example we will create a simple REST call to create a 'template' sensor via config entry.
# Real integrations should use the Home Assistant REST API or integration discovery mechanisms.
# This is a placeholder showing how you would call HA API if needed.
# For local custom_components the normal route is to write entities via the integration platform.
created.append(a)
return created
