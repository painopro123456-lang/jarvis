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
    """Report new risky files only after their size is stable across polls.

    This is notification-only; it is not an execution blocker or antivirus engine.
    """
    def __init__(self):
        self.folder = Path.home() / "Downloads"
        self._known: set[str] = set()
        self._pending: dict[str, tuple[int, int]] = {}
        self._reported: set[str] = set()
        self._initialized = False

    def poll(self) -> list[str]:
        if platform.system() != "Windows" or not self.folder.is_dir():
            return []
        found: list[str] = []
        present: set[str] = set()
        try:
            entries = list(self.folder.iterdir())
        except OSError:
            return []
        for path in entries:
            try:
                if not path.is_file() or path.suffix.lower() not in RISKY_SUFFIXES:
                    continue
                stat = path.stat()
                key = str(path.resolve()).casefold()
                present.add(key)
                if not self._initialized or key in self._known or key in self._reported:
                    continue
                previous = self._pending.get(key)
                if previous is None or previous[0] != stat.st_size:
                    self._pending[key] = (stat.st_size, 0)
                    continue
                stable_polls = previous[1] + 1
                self._pending[key] = (stat.st_size, stable_polls)
                # Timer runs every five seconds. Two unchanged polls means the
                # file has been stable for roughly ten seconds.
                if stable_polls >= 2:
                    found.append(f"{path.name} ({stat.st_size:,} bytes)")
                    self._reported.add(key)
                    self._pending.pop(key, None)
            except (OSError, PermissionError):
                continue
        if not self._initialized:
            self._known = present
            self._initialized = True
            return []
        self._known.update(present)
        for key in list(self._pending):
            if key not in present:
                self._pending.pop(key, None)
        return found


def monitor_status() -> str:
    return (
        f"Watching: {Path.home() / 'Downloads'}\n"
        "New executable, script, shortcut, disk-image and installer files are flagged for review. "
        "This monitor does not block execution or replace antivirus real-time protection."
    )
