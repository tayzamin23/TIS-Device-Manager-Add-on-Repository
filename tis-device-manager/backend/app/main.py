from fastapi import FastAPI, Depends, HTTPException, Request, Response, Cookie
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError
from pathlib import Path
from typing import Optional

import bcrypt
import time

from app.models import Device, Appliance, Project
from app import scanner, store, ha_publisher


# =====================================
# CONFIG
# =====================================

SECRET_KEY = "THIS_IS_NOT_SECRET_CHANGE_IT"
ALGORITHM = "HS256"
TOKEN_EXPIRY = 7 * 24 * 3600  # 7 days

frontend_path = Path("/app/frontend")

app = FastAPI(title="TIS Device Manager")

app.mount("/static", StaticFiles(directory=frontend_path), name="static")


# =====================================
# AUTH FUNCTIONS
# =====================================

def create_token(email: str):
    payload = {
        "email": email,
        "exp": time.time() + TOKEN_EXPIRY
    }
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


# =====================================
# ADMIN LOGIN
# =====================================

DEFAULT_ADMIN = {
    "email": "admin@mail.com",
    "password": bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode()
}


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


# =====================================
# FRONTEND ROUTING
# =====================================

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


# =====================================
# API ENDPOINTS
# =====================================

@app.get("/api/scan")
async def api_scan(base_ip: str = "192.168.1.", user=Depends(get_current_user)):
    found = scanner.scan_range(base_ip, 1, 254)
    return {"found": found}


@app.get("/api/devices")
async def api_devices(user=Depends(get_current_user)):
    return store.load_project().get("devices", [])


@app.get("/api/project")
async def api_project(user=Depends(get_current_user)):
    return store.load_project()


@app.post("/api/project")
async def api_save_project(proj: Project, user=Depends(get_current_user)):
    store.save_project(proj.dict())
    return {"success": True}


@app.post("/api/appliances")
async def api_create_appliance(appliance: Appliance, user=Depends(get_current_user)):
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
    return {"created": created}
