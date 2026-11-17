"""Third-party antivirus inventory and download-folder warning monitor.

This is a companion monitor, not an antivirus engine or an execution-blocking filter.
The installed security product must provide real-time blocking and quarantine.
"""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from datetime import datetime, timezone

RISKY_SUFFIXES = {
    ".exe", ".msi", ".msp", ".dll", ".scr", ".com", ".bat", ".cmd",
    ".ps1", ".psm1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh",
    ".hta", ".lnk", ".iso", ".img", ".jar", ".reg"
}


def antivirus_inventory() -> str:
    """Read antivirus registrations from Windows Security Center (not Defender-only)."""
    if platform.system() != "Windows":
        return "Third-party antivirus inventory is available only on Windows."
    script = (
        "$items=Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntivirusProduct "
        "-ErrorAction Stop | Select-Object displayName,productState,pathToSignedProductExe,pathToSignedReportingExe; "
        "$items | ConvertTo-Json -Depth 3 -Compress"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=25, shell=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Windows Security Center did not return antivirus registrations.")
    raw = result.stdout.strip()
    if not raw or raw == "null":
        return "Windows Security Center reports no registered antivirus product. Install and activate a reputable third-party antivirus."
    import json
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    rows = []
    for item in data:
        name = str(item.get("displayName") or "Unknown product")
        state = item.get("productState")
        # Security Center productState is vendor-defined bit data; do not over-interpret it.
        rows.append(f"{name} | productState={state} (raw vendor state; not independently verified)\n  Engine: {item.get('pathToSignedProductExe') or 'not reported'}")
    return "Registered antivirus products (registration does not prove protection is enabled):\n" + "\n".join(rows)


class DownloadMonitor:
    """Poll the user's Downloads folder and report newly-arrived risky file types."""
    def __init__(self):
        self.folder = Path.home() / "Downloads"
        self._seen: set[tuple[str, int, int]] = set()
        self._initialized = False

    def poll(self) -> list[str]:
        if platform.system() != "Windows" or not self.folder.is_dir():
            return []
        found = []
        current = set()
        try:
            for path in self.folder.iterdir():
                try:
                    if not path.is_file() or path.suffix.lower() not in RISKY_SUFFIXES:
                        continue
                    stat = path.stat()
                    key = (str(path.resolve()).lower(), stat.st_size, stat.st_mtime_ns)
                    current.add(key)
                    if self._initialized and key not in self._seen:
                        found.append(f"{path.name} ({stat.st_size:,} bytes)")
                except (OSError, PermissionError):
                    continue
        except OSError:
            return []
        self._seen = current
        self._initialized = True
        return found


def monitor_status() -> str:
    return (
        f"Watching: {Path.home() / 'Downloads'}\n"
        "New executable, script, shortcut, disk-image and installer files are flagged for review. "
        "This monitor does not block execution or replace antivirus real-time protection."
    )
