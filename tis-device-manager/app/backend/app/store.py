# store.py
import json
from pathlib import Path

PROJECT_FILE = Path("/app/project.json")

def load_project():
    if not PROJECT_FILE.exists():
        return {"devices": [], "appliances": [], "mappings": [], "ip_com": []}
    try:
        return json.loads(PROJECT_FILE.read_text())
    except Exception:
        return {"devices": [], "appliances": [], "mappings": [], "ip_com": []}

def save_project(data):
    PROJECT_FILE.write_text(json.dumps(data, indent=2))
