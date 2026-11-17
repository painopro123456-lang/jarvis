"""Bridge to the Rust native core bundled beside the JARVIS application."""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

def _binary() -> Path:
    candidates=[]
    if getattr(sys,"frozen",False):
        candidates.append(Path(getattr(sys,"_MEIPASS",Path(sys.executable).parent))/"jarvis-core.exe")
        candidates.append(Path(sys.executable).parent/"jarvis-core.exe")
    root=Path(__file__).resolve().parent.parent
    candidates.append(root/"native"/"target"/"release"/"jarvis-core.exe")
    for path in candidates:
        if path.is_file(): return path
    raise FileNotFoundError("The Rust JARVIS core was not found. Reinstall the latest JARVIS build.")

def driver_audit() -> str:
    exe=_binary()
    flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
    result=subprocess.run([str(exe),"drivers"],capture_output=True,text=True,timeout=240,
                          stdin=subprocess.DEVNULL,creationflags=flags,shell=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Windows driver inspection failed.")
    try: report=json.loads(result.stdout)
    except json.JSONDecodeError as exc: raise RuntimeError(f"Rust driver report was invalid: {exc}") from exc
    installed=report.get("installed_drivers") or []
    updates=report.get("available_driver_updates") or []
    lines=[f"RUST DRIVER AUDIT · {report.get('scanned_at','time unavailable')}",
           f"Installed signed-driver records: {len(installed)}",
           f"Driver updates offered by Windows Update: {len(updates)}",
           "",
           "AVAILABLE DRIVER UPDATES (not installed):"]
    if updates:
        for item in updates[:40]:
            lines.append("• "+str(item.get("Title","Unnamed driver update")))
            if item.get("Description"): lines.append("  "+str(item["Description"]).replace("\n"," ")[:350])
    else:
        lines.append("Windows Update did not offer any driver updates in this scan.")
    if report.get("update_scan_error"):
        lines += ["","Windows Update scan note: "+str(report["update_scan_error"])]
    lines += ["","INSTALLED DRIVER SAMPLE:"]
    for item in installed[:30]:
        lines.append("• {0} — {1} — version {2}".format(
            item.get("DeviceName","Unknown device"),
            item.get("Manufacturer","Unknown manufacturer"),
            item.get("DriverVersion","unknown")))
    lines += ["","Important: Windows Update's offered-driver list is not a complete comparison against every vendor release. No drivers were downloaded or changed. Review the hardware vendor's official support page before approving an update."]
    return "\n".join(lines)
