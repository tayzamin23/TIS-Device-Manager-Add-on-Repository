from fastapi import FastAPI, HTTPException
from app.models import Device, Appliance, Project
from app import scanner, store, ha_publisher
from typing import List


app = FastAPI(title="TIS Device Manager API")


@app.get('/api/scan')
async def api_scan(base_ip: str = '192.168.1.'):
found = scanner.scan_range(base_ip, 1, 254)
return {"found": found}


@app.get('/api/devices')
async def api_devices():
return store.load_project().get('devices', [])


@app.post('/api/appliances')
async def api_create_appliance(appliance: Appliance):
project = store.load_project()
aps = project.get('appliances', [])
aps.append(appliance.dict())
project['appliances'] = aps
store.save_project(project)
return appliance


@app.get('/api/project')
async def api_get_project():
return store.load_project()


@app.post('/api/project')
async def api_save_project(proj: Project):
store.save_project(proj.dict())
return {"success": True}


@app.post('/api/publish')
async def api_publish(host: str, token: str):
project = store.load_project()
appliances = project.get('appliances', [])
created = await ha_publisher.publish_entities(host, token, appliances)
return {"created": created}
