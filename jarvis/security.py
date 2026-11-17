"""Read-only security inspection plus Microsoft Defender-backed file scans."""
from __future__ import annotations
import os, platform, subprocess
from pathlib import Path
import psutil
from jarvis import actions

def firewall_status() -> str:
    if platform.system() != "Windows":
        return "Windows Firewall inspection is only available on Windows."
    cmd = "Get-NetFirewallProfile | Select-Object Name,Enabled,DefaultInboundAction,DefaultOutboundAction | Format-Table -AutoSize | Out-String"
    r = subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",cmd],capture_output=True,text=True,timeout=20)
    if r.returncode: raise RuntimeError(r.stderr.strip() or "Could not inspect firewall.")
    return r.stdout.strip() or "No firewall profile data returned."

def network_connections() -> str:
    rows=[]
    for c in psutil.net_connections(kind="inet"):
        if not c.raddr: continue
        try:
            name=psutil.Process(c.pid).name() if c.pid else "Unknown"
        except Exception: name="Unknown"
        rows.append(f"{name} · PID {c.pid or '?'} · {c.laddr.ip}:{c.laddr.port} → {c.raddr.ip}:{c.raddr.port} · {c.status}")
    return "Active network connections (not a verdict of malicious activity):\n" + ("\n".join(rows[:35]) or "No remote connections visible; administrator permissions may be required.")

def inspect_processes() -> str:
    rows=[]
    for p in psutil.process_iter(["pid","name","exe","username"]):
        try:
            info=p.info
            name=info.get("name") or "Unknown"
            path=info.get("exe") or ""
            flags=[]
            if path and ("\\temp\\" in path.lower() or "\\downloads\\" in path.lower()): flags.append("running from user-writable folder")
            if not path: flags.append("executable path unavailable")
            if flags: rows.append(f"{name} · PID {info['pid']} · {', '.join(flags)} · {path}")
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    return "Review candidates only — these indicators do not prove malware:\n" + ("\n".join(rows[:30]) or "No obvious review candidates found.")

def scan_file(path_text: str) -> str:
    path=Path(os.path.expandvars(os.path.expanduser(path_text.strip().strip('"')))).resolve()
    if not path.is_file(): raise ValueError("Choose an existing file.")
    # Ask Defender to scan this exact file; do not execute or upload it.
    candidates=[Path(os.environ.get("ProgramFiles",r"C:\\Program Files"))/"Windows Defender"/"MpCmdRun.exe"]
    platform_dir=Path(os.environ.get("ProgramData",r"C:\\ProgramData"))/"Microsoft/Windows Defender/Platform"
    if platform_dir.is_dir(): candidates += sorted(platform_dir.glob("*/MpCmdRun.exe"), reverse=True)
    exe=next((p for p in candidates if p.is_file()),None)
    if not exe: raise RuntimeError("Microsoft Defender command-line scanner was not found.")
    subprocess.Popen([str(exe),"-Scan","-ScanType","3","-File",str(path)],creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    return f"Microsoft Defender started a custom scan of {path.name}. Check Windows Security for the result."

def create_restore_point() -> str:
    if not actions.is_admin(): return "Restore point creation requires JARVIS to be relaunched with ADMIN MODE."
    cmd="Checkpoint-Computer -Description 'JARVIS safety checkpoint' -RestorePointType 'MODIFY_SETTINGS'"
    r=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",cmd],capture_output=True,text=True,timeout=90)
    if r.returncode: raise RuntimeError(r.stderr.strip() or "Windows could not create a restore point.")
    return "Windows restore point created."
