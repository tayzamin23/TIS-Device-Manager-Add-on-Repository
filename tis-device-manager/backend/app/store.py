import json
from pathlib import Path

PROJECT_FILE = Path("/app/project.json")

def load_project():
    if not PROJECT_FILE.exists():
        return {"devices": [], "appliances": []}
    return json.loads(PROJECT_FILE.read_text())

def save_project(data):
    PROJECT_FILE.write_text(json.dumps(data, indent=2))
