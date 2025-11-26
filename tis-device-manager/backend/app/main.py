# main.py
from fastapi import FastAPI, Depends, HTTPException, Request, Response, Cookie
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError
from pathlib import Path
from typing import Optional
import bcrypt
import time
import asyncio
import logging

from app import scanner, store, ha_publisher, generator, listener, scanner as scanner_module

# Basic config
SECRET_KEY = "THIS_IS_NOT_SECRET_CHANGE_IT"
ALGORITHM = "HS256"
TOKEN_EXPIRY = 7 * 24 * 3600  # 7 days

frontend_path = Path("/app/frontend")
app = FastAPI(title="TIS Device Manager")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Logging
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)

def create_token(email: str):
    payload = {"email": email, "exp": time.time() + TOKEN_EXPIRY}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["email"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

def get_current_user(session: Optional[str] = Cookie(None)):
    if not session:
        raise HTTPException(status_code=401, detail="Not logged in")
    return verify_token(session)

DEFAULT_ADMIN = {"email": "admin@mail.com", "password": bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode()}

@app.post("/api/admin/login")
async def api_admin_login(form: OAuth2PasswordRequestForm = Depends()):
    if form.username != DEFAULT_ADMIN["email"]:
        raise HTTPException(401, "Invalid user")
    if not bcrypt.checkpw(form.password.encode(), DEFAULT_ADMIN["password"].encode()):
        raise HTTPException(401, "Wrong password")
    token = create_token(form.username)
    resp = JSONResponse({"success": True})
    resp.set_cookie("session", token, httponly=True, samesite="lax", max_age=TOKEN_EXPIRY)
    return resp

@app.post("/api/admin/logout")
async def api_logout():
    resp = JSONResponse({"success": True})
    resp.delete_cookie("session")
    return resp

@app.get("/")
async def index():
    return FileResponse(frontend_path / "login.html")

@app.get("/admin/dashboard")
async def dashboard(user=Depends(get_current_user)):
    return FileResponse(frontend_path / "dashboard.html")

@app.get("/admin/devices")
async def devices_page(user=Depends(get_current_user)):
    return FileResponse(frontend_path / "devices.html")

@app.get("/admin/appliances")
async def appliances_page(user=Depends(get_current_user)):
    return FileResponse(frontend_path / "appliances.html")


# API: discover IP-COM (narrow range) or accept explicit ip_com param
@app.get("/api/scan")
async def api_scan(base_ip: str = "192.168.110.", start: int = 1, end: int = 254, ip_com: Optional[str] = None, user=Depends(get_current_user)):
    """
    If ip_com provided -> discover bus via that IP.
    Otherwise scan small range for IP-COM device(s) and then discover bus via first found IP.
    """
    project = store.load_project()
    devices = project.get("devices", [])
    appliances = project.get("appliances", [])

    if ip_com:
        # discover bus via this IP-COM
        discovered = scanner.discover_bus_via_ip_com(ip_com, timeout=1.0)
        found = [{"ip": ip_com, "discovered": discovered}]
    else:
        # find IP-COM devices in the provided range (fast)
        found_ips = scanner.find_ip_comport_in_range(base_ip, start, end, timeout=0.45)
        if not found_ips:
            return {"found": [], "message": "No IP-COM found in the range. Provide ip_com param to /api/scan?ip_com=192.168.110.205"}
        # use first IP found to discover bus
        ip_com_found = found_ips[0]
        discovered = scanner.discover_bus_via_ip_com(ip_com_found, timeout=1.0)
        found = [{"ip": ip_com_found, "discovered": discovered}]

    # Add discovered devices to project + auto create appliances
    added_devices = 0
    added_appliances = 0
    for entry in found:
        for dev in entry.get("discovered", []):
            # build device entry
            dev_entry = generator.build_device_entry(dev)
            exists = any(d.get("subnet") == dev_entry["subnet"] and d.get("device_id") == dev_entry["device_id"] for d in devices)
            if not exists:
                devices.append(dev_entry)
                added_devices += 1
                # auto-create appliances
                new_aps = generator.auto_create_appliances_for_device(dev)
                # avoid adding duplicates by name
                for ap in new_aps:
                    if not any(a.get("name") == ap["name"] for a in appliances):
                        appliances.append(ap)
                        added_appliances += 1

    project["devices"] = devices
    project["appliances"] = appliances
    store.save_project(project)

    return {"found": found, "devices_added": added_devices, "appliances_added": added_appliances}


@app.get("/api/devices")
async def api_devices(user=Depends(get_current_user)):
    return store.load_project().get("devices", [])


@app.get("/api/project")
async def api_project(user=Depends(get_current_user)):
    return store.load_project()


from pydantic import BaseModel
class ApplianceIn(BaseModel):
    name: str
    type: str
    device: str
    channels: dict

@app.post("/api/appliances")
async def api_create_appliance(appliance: ApplianceIn, user=Depends(get_current_user)):
    project = store.load_project()
    aps = project.get("appliances", [])
    aps.append(appliance.dict())
    project["appliances"] = aps
    store.save_project(project)
    return appliance


@app.post("/api/publish")
async def api_publish(host: str, token: str, user=Depends(get_current_user)):
    project = store.load_project()
    appliances = project.get("appliances", [])
    created = await ha_publisher.publish_entities(host, token, appliances)
    # Store minimal mapping from device->entity for real-time updates
    # mapping stored as list of dicts under key 'mappings' for listener to use
    mapping = []
    for ap in appliances:
        name = ap.get("name")
        safe = name.replace(" ", "_").lower()
        entity_id = f"tis.{''.join(ch for ch in safe if ch.isalnum() or ch == '_')}"
        # device reference like "subnet,device"
        device_ref = ap.get("device")
        ch = ap.get("channels", {}).get("channel")
        mapping.append({
            "device_ref": device_ref,
            "channel": ch,
            "entity_id": entity_id,
            "type": ap.get("type")
        })
    project["mappings"] = mapping
    store.save_project(project)
    return {"created": created, "mappings_stored": len(mapping)}


# startup listener to receive live frames
@app.on_event("startup")
async def startup_event():
    # handler for incoming frames
    from app import scanner as scanner_mod, store as store_mod, ha_publisher as ha_pub

    project = store.load_project()
    app.state.ha_host = None
    app.state.ha_token = None

    async def on_frame(data: bytes, addr):
        parsed = scanner_mod.parse_tis_reply(data)
        if not parsed:
            return
        # we expect mappings to be present in project.json if publish was used
        proj = store_mod.load_project()
        mappings = proj.get("mappings", [])
        # mapping device_ref e.g. "1,48"
        dev_ref = f"{parsed['subnet']},{parsed['device_id']}"
        # naive: if payload contains channel info, attempt to get channel from payload[10] or channels_hint
        ch_hint = parsed.get("channels_hint") or None

        # find entries matching device_ref (and possibly channel)
        for m in mappings:
            if m.get("device_ref") == dev_ref:
                ent = m.get("entity_id")
                typ = m.get("type")
                # derive state from parsed info using heuristics - default to "on" for switches
                state = "on" if typ in ("switch", "light") else "unknown"
                # If channel info exists and mapping has channel, you could match specific channel changes here.
                # For now we simply push a state change (can be improved when we decode event frames)
                if app.state.ha_host and app.state.ha_token:
                    try:
                        await ha_pub.update_entity_state(app.state.ha_host, app.state.ha_token, ent, state)
                    except Exception:
                        logger.exception("Failed to update HA for %s", ent)

    # start the UDP listener (runs on same port 6000)
    try:
        transport, protocol = await listener.start_listener(lambda d, a: asyncio.create_task(on_frame(d, a)))
        app.state.tis_transport = transport
        logger.info("TIS listener started on UDP port 6000")
    except Exception:
        logger.exception("Failed to start TIS listener")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        transport = app.state.tis_transport
        if transport:
            transport.close()
    except Exception:
        pass
