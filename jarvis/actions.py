"""Explicit, allow-listed user actions. No arbitrary shell execution."""
from __future__ import annotations

import os
import subprocess
import webbrowser
from pathlib import Path


APP_ALIASES = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "task manager": "taskmgr.exe",
    "file explorer": "explorer.exe",
    "settings": "ms-settings:",
}


def open_target(target: str) -> str:
    key = target.strip().lower()
    if key in APP_ALIASES:
        value = APP_ALIASES[key]
        if value.startswith("ms-"):
            os.startfile(value)
        else:
            subprocess.Popen([value], shell=False)
        return f"Opening {target}."
    if key in {"downloads", "documents", "desktop"}:
        folder = {"downloads": Path.home() / "Downloads",
                  "documents": Path.home() / "Documents",
                  "desktop": Path.home() / "Desktop"}[key]
        os.startfile(str(folder))
        return f"Opening your {target} folder."
    if key in {"browser", "web browser"}:
        webbrowser.open("https://www.google.com")
        return "Opening your default browser."
    raise ValueError("I can open Notepad, Calculator, Paint, Task Manager, File Explorer, Settings, your common folders, or your browser.")


def start_defender_quick_scan() -> str:
    """Start a Microsoft Defender quick scan; never changes protection settings."""
    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\\Program Files"))
        / "Windows Defender" / "MpCmdRun.exe",
        Path(os.environ.get("ProgramData", r"C:\\ProgramData"))
        / "Microsoft" / "Windows Defender" / "Platform",
    ]
    exe = next((p for p in candidates if p.is_file()), None)
    if exe is None and candidates[1].is_dir():
        versions = sorted(candidates[1].glob("*/MpCmdRun.exe"), reverse=True)
        exe = versions[0] if versions else None
    if exe is None:
        raise RuntimeError("Microsoft Defender command-line scanner was not found. Check Windows Security.")
    subprocess.Popen([str(exe), "-Scan", "-ScanType", "1"],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return "Microsoft Defender quick scan started. You can continue using the PC."
