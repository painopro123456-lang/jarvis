"""Private, local JARVIS memory. Stored in the user's AppData folder."""
from __future__ import annotations
import json, os
from pathlib import Path
from datetime import datetime

def _path() -> Path:
    root = Path(os.getenv("APPDATA", str(Path.home()))) / "JARVIS"
    root.mkdir(parents=True, exist_ok=True)
    return root / "memory.json"

def load() -> dict:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"preferences": {}, "notes": []}
    except Exception:
        return {"preferences": {}, "notes": []}

def remember(note: str) -> str:
    data = load()
    data.setdefault("notes", []).append({"text": note[:1000], "created": datetime.now().isoformat(timespec="seconds")})
    data["notes"] = data["notes"][-200:]
    _path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return "I'll remember that locally on this PC."

def set_preference(key: str, value: str) -> str:
    data = load()
    data.setdefault("preferences", {})[key[:80]] = value[:500]
    _path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return "Preference saved locally."

def summary() -> str:
    data = load()
    prefs = data.get("preferences", {})
    notes = data.get("notes", [])[-12:]
    lines = [f"Preference · {k}: {v}" for k, v in prefs.items()]
    lines += [f"Memory · {n.get('text','')}" for n in notes]
    return "\n".join(lines) if lines else "JARVIS has no saved memories yet."

def clear() -> str:
    _path().write_text(json.dumps({"preferences": {}, "notes": []}, indent=2), encoding="utf-8")
    return "Local JARVIS memory cleared."
