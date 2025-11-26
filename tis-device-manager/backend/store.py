import json
from pathlib import Path

PROJECT_FILE = Path('/data/project.json')

def load_project():
if PROJECT_FILE.exists():
return json.loads(PROJECT_FILE.read_text())
return {"name": "untitled", "devices": [], "appliances": []}

def save_project(obj):
PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
PROJECT_FILE.write_text(json.dumps(obj, indent=2))
return True
