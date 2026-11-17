"""Local Windows diagnostics for common PC problems; no repair commands are run."""
from __future__ import annotations
import platform, subprocess, shutil
import psutil

def report() -> str:
    rows=[]
    rows.append(f"OS: {platform.platform()}")
    rows.append(f"CPU: {psutil.cpu_percent(interval=0.5):.0f}%")
    vm=psutil.virtual_memory()
    rows.append(f"RAM: {vm.percent:.0f}% used ({vm.available/(1024**3):.1f} GB available)")
    root="C:\\" if platform.system()=="Windows" else "/"
    disk=shutil.disk_usage(root)
    rows.append(f"Disk: {disk.free/(1024**3):.1f} GB free ({disk.used/disk.total*100:.0f}% used)")
    if platform.system()=="Windows":
        try:
            cmd="Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; StartTime=(Get-Date).AddDays(-2)} -MaxEvents 12 | Select-Object TimeCreated,Id,LevelDisplayName,ProviderName,Message | Format-List | Out-String"
            r=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",cmd],capture_output=True,text=True,timeout=35)
            if r.returncode==0 and r.stdout.strip(): rows.append("Recent critical/error System events (last 48h):\n"+r.stdout.strip()[:7000])
            elif r.stderr.strip(): rows.append("Event log access: "+r.stderr.strip()[:500])
        except Exception as exc: rows.append("Event log check unavailable: "+str(exc))
    rows.append("This is diagnostic evidence, not an automatic diagnosis. No settings or files were changed.")
    return "\n".join(rows)
