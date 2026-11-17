"""Small local automation/routine registry; routines are explicit and user-triggered."""
from __future__ import annotations
import json, os
from pathlib import Path
from datetime import datetime

def _path():
    root=Path(os.getenv("APPDATA",str(Path.home())))/"JARVIS"
    root.mkdir(parents=True,exist_ok=True)
    return root/"routines.json"

def list_routines():
    try: data=json.loads(_path().read_text(encoding="utf-8"))
    except Exception: data=[]
    return data if isinstance(data,list) else []

def add_routine(name: str, instruction: str):
    items=list_routines()
    items.append({"name":name[:80],"instruction":instruction[:1000],"created":datetime.now().isoformat(timespec="seconds"),"enabled":False})
    _path().write_text(json.dumps(items[-100:],indent=2),encoding="utf-8")
    return "Routine saved disabled. Review it and enable/run it explicitly from the Automation page."

def report():
    items=list_routines()
    if not items: return "No routines saved. Ask JARVIS to create a routine, then review it here."
    return "\n".join(f"{i+1}. {x['name']} [{ 'enabled' if x.get('enabled') else 'disabled' }] — {x['instruction']}" for i,x in enumerate(items))
