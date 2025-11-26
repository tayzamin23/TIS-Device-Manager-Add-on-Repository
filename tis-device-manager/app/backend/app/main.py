# main.py
from fastapi import FastAPI, Depends, HTTPException, Cookie
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pathlib import Path
from typing import Optional
import bcrypt, time, asyncio, logging
from jose import jwt, JWTError

# >>> FIX: import StaticFiles from starlette (not fastapi.staticfiles)
from starlette.staticfiles import StaticFiles

from app import scanner, store, ha_publisher, appliance_builder, listener, tis_protocol, config

frontend_path = Path("/app/frontend")
app = FastAPI(title="TIS Device Manager")

# mount static files (frontend)
app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

logger = logging.getLogger("uvicorn")
SECRET_KEY = "THIS_IS_NOT_SECRET_CHANGE_IT"
ALGORITHM = "HS256"
TOKEN_EXPIRY = 7 * 24 * 3600

DEFAULT_ADMIN = {"email": "admin@mail.com", "password": bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode()}

def create_token(email: str):
    payload = {"email": email, "exp": int(time.time() + TOKEN_EXPIRY)}
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

@app.get("/api/scan")
async def api_scan(base_ip: str = config.IP_COM_DEFAULT_BASE, start: int = config.IP_COM_SCAN_START, end: int = config.IP_COM_SCAN_END, ip_com: Optional[str] = None, user=Depends(get_current_user)):
    project = store.load_project()
    devices = project.get("devices", [])
    appliances = project.get("appliances", [])
    ip_coms = []

    if ip_com:
        ip_coms = [ip_com]
    else:
        # auto discover IP-COMs in the configured base subnet
        ip_coms = scanner.find_ip_comport_in_range(base_ip, start, end)

    if not ip_coms:
        return {"found": [], "message": "No IP-COM found in the range. Provide ip_com param."}

    found = []
    added_devices = 0
    added_appliances = 0

    for ipc in ip_coms:
        discovered = scanner.discover_bus_via_ip_com(ipc, timeout=config.BUS_DISCOVER_TIMEOUT)
        found.append({"ip": ipc, "discovered": discovered})

        if ipc not in project.get("ip_com", []):
            project.setdefault("ip_com", []).append(ipc)

        for dev in discovered:
            dev_entry = appliance_builder.build_device_entry(dev)
            if not any(d.get("subnet") == dev_entry["subnet"] and d.get("device_id") == dev_entry["device_id"] for d in devices):
                devices.append(dev_entry)
                added_devices += 1
                new_aps = appliance_builder.auto_create_appliances_for_device(dev)
                for a in new_aps:
                    if not any(x.get("name") == a["name"] for x in appliances):
                        appliances.append(a)
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
    mapping = []
    for ap in appliances:
        name = ap.get("name")
        safe = "".join(ch for ch.replace(" ", "_").lower() if (ch.isalnum() or ch == "_"))
        entity_id = f"tis.{safe}"
        device_ref = ap.get("device")
        ch = ap.get("channels", {}).get("channel")
        mapping.append({"device_ref": device_ref, "channel": ch, "entity_id": entity_id, "type": ap.get("type")})
    project["mappings"] = mapping
    project["ha_host"] = host
    project["ha_token"] = token
    store.save_project(project)
    # Save host/token into app state for listener updates
    app.state.ha_host = host
    app.state.ha_token = token
    return {"created": created, "mappings_stored": len(mapping)}

# Startup: start UDP listener
@app.on_event("startup")
async def startup_event():
    proj = store.load_project()
    app.state.ha_host = proj.get("ha_host")
    app.state.ha_token = proj.get("ha_token")
    async def on_frame(data, addr):
        parsed = tis_protocol.parse_device_info_frame(data)
        if not parsed:
            return
        # lookup mapping
        proj_local = store.load_project()
        mappings = proj_local.get("mappings", [])
        dev_ref = f"{parsed['subnet']},{parsed['device_id']}"
        for m in mappings:
            if m.get("device_ref") == dev_ref:
                ent = m.get("entity_id")
                typ = m.get("type")
                state = "on" if typ in ("switch", "light") else "unknown"
                if app.state.ha_host and app.state.ha_token:
                    try:
                        await ha_publisher.update_entity_state(app.state.ha_host, app.state.ha_token, ent, state)
                    except Exception:
                        logger.exception("Failed to update HA for %s", ent)
    try:
        transport, proto = await listener.start_listener(lambda d,a: asyncio.create_task(on_frame(d,a)))
        app.state.tis_transport = transport
        logger.info("TIS listener started")
    except Exception:
        logger.exception("Failed starting TIS listener")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        t = app.state.tis_transport
        if t:
            t.close()
    except Exception:
        pass
