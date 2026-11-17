"""Privacy-conscious local action history for JARVIS.

Only action names, timestamps and outcomes are stored. User prompts, arguments,
file contents, passwords, URLs and command output are deliberately excluded.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

MAX_ENTRIES = 500


def _path() -> Path:
    root = Path(os.getenv("APPDATA", str(Path.home()))) / "JARVIS"
    root.mkdir(parents=True, exist_ok=True)
    return root / "activity.jsonl"


def record(action: str, succeeded: bool) -> None:
    """Append a minimal audit event; never persist tool arguments or output."""
    item = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "action": str(action)[:80],
        "outcome": "completed" if succeeded else "failed_or_cancelled",
    }
    path = _path()
    try:
        existing = path.read_text(encoding="utf-8").splitlines()[-(MAX_ENTRIES - 1):]
    except (OSError, UnicodeError):
        existing = []
    with path.open("w", encoding="utf-8") as handle:
        for line in existing:
            handle.write(line + "\n")
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def report(limit: int = 100) -> str:
    """Return recent minimal audit events."""
    try:
        lines = _path().read_text(encoding="utf-8").splitlines()[-max(1, min(int(limit), MAX_ENTRIES)):]
    except FileNotFoundError:
        return "No JARVIS actions have been recorded yet."
    except (OSError, UnicodeError) as exc:
        return f"Could not read local action history: {exc}"
    rows = []
    for line in lines:
        try:
            item = json.loads(line)
            rows.append(f"{item.get('at', '?')} · {item.get('action', 'unknown')} · {item.get('outcome', 'unknown')}")
        except (json.JSONDecodeError, TypeError):
            continue
    return "\n".join(rows) if rows else "No valid action history entries found."
