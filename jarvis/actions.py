"""Windows controls exposed through explicit, allow-listed operations."""
from __future__ import annotations

import ctypes
import os
import platform
import subprocess
import sys
import webbrowser
from pathlib import Path

import psutil

APP_ALIASES = {
    "notepad": "notepad.exe", "calculator": "calc.exe", "paint": "mspaint.exe",
    "task manager": "taskmgr.exe", "file explorer": "explorer.exe",
    "settings": "ms-settings:", "task scheduler": "taskschd.msc", "resource monitor": "resmon.exe", "services": "services.msc", "windows security": "ms-settings:windowsdefender",
}
APPROVED_WINGET_APPS = {\n    "7zip": "7zip.7zip", "vlc": "VideoLAN.VLC", "notepad++": "Notepad++.Notepad++",\n    "firefox": "Mozilla.Firefox", "google chrome": "Google.Chrome", "obs": "OBSProject.OBSStudio",\n    "discord": "Discord.Discord", "steam": "Valve.Steam",\n}\n\nPOWER_PLANS = {
    "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
    "high performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "ultimate performance": "e9a42b02-d5df-448d-aa00-03f14749eb61",
}


def is_admin() -> bool:
    if platform.system() != "Windows":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> str:
    if is_admin():
        return "JARVIS is already running as administrator."
    if platform.system() != "Windows":
        return "Administrator mode is only available on Windows."
    if getattr(sys, "frozen", False):
        executable, params = sys.executable, ""
    else:
        executable, params = sys.executable, '-m jarvis'
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
    if result <= 32:
        raise RuntimeError("Windows did not start the administrator session.")
    return "Windows UAC approval requested. JARVIS will reopen with administrator privileges."


def open_target(target: str) -> str:
    key = target.strip().lower()
    if key in APP_ALIASES:
        value = APP_ALIASES[key]
        if value.startswith("ms-"):
            os.startfile(value)
        else:
            subprocess.Popen([value], shell=False)
        return f"Opening {target}."
    folders = {"downloads": Path.home() / "Downloads",
               "documents": Path.home() / "Documents",
               "desktop": Path.home() / "Desktop"}
    if key in folders:
        os.startfile(str(folders[key]))
        return f"Opening your {target} folder."
    if key in {"browser", "web browser"}:
        webbrowser.open("https://www.google.com")
        return "Opening your default browser."
    path = Path(os.path.expandvars(os.path.expanduser(target.strip().strip('"'))))
    if path.exists():
        os.startfile(str(path.resolve()))
        return f"Opening {path}."
    raise ValueError("I couldn't find that app or path. Try an app name or a full file/folder path.")


def process_report() -> str:
    rows = []
    for p in psutil.process_iter(["pid", "name", "memory_info", "username"]):
        try:
            info = p.info
            mem = info["memory_info"].rss / (1024 ** 2) if info.get("memory_info") else 0
            rows.append((mem, info["pid"], info.get("name") or "Unknown"))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    rows.sort(reverse=True)
    return "Top processes by RAM:\n" + "\n".join(
        f"PID {pid}  |  {name}  |  {mem:.0f} MB" for mem, pid, name in rows[:15]
    )


def terminate_process(pid_text: str) -> str:
    if not pid_text.isdigit():
        raise ValueError("Use a numeric process ID (PID), for example: close process 1234.")
    pid = int(pid_text)
    if pid in (0, 4, os.getpid()):
        raise ValueError("That process is protected or is JARVIS itself.")
    proc = psutil.Process(pid)
    name = proc.name()
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except psutil.TimeoutExpired:
        proc.kill()
    return f"Closed {name} (PID {pid})."


def startup_report() -> str:
    if platform.system() != "Windows":
        return "Startup-app inspection is available on Windows."
    import winreg
    found = []
    locations = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ]
    for hive, key in locations:
        try:
            with winreg.OpenKey(hive, key) as reg:
                for i in range(winreg.QueryInfoKey(reg)[1]):
                    name, value, _ = winreg.EnumValue(reg, i)
                    found.append(f"{name}: {value}")
        except OSError:
            pass
    for folder in (Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup",
                   Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup"):
        if folder.is_dir():
            found.extend(f"Startup shortcut: {p.name}" for p in folder.iterdir())
    return "Startup entries (read-only):\n" + ("\n".join(found[:40]) if found else "No entries found or access unavailable.")


def set_power_plan(name: str) -> str:
    key = name.lower().strip()
    if key not in POWER_PLANS:
        raise ValueError("Choose balanced, high performance, or ultimate performance.")
    result = subprocess.run(["powercfg", "/setactive", POWER_PLANS[key]],
                            capture_output=True, text=True, shell=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"Windows could not activate {key}.")
    return f"Power plan changed to {key}. You can change it back by asking for balanced."


def defender_status() -> str:
    command = "(Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureLastUpdated | Format-List | Out-String)"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                            capture_output=True, text=True, timeout=20, shell=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Could not read Microsoft Defender status.")
    return "Microsoft Defender status:\n" + result.stdout.strip()


def start_defender_quick_scan() -> str:
    if platform.system() != "Windows":
        raise RuntimeError("Microsoft Defender scanning is available on Windows.")
    roots = [Path(os.environ.get("ProgramFiles", r"C:\\Program Files")) / "Windows Defender",
             Path(os.environ.get("ProgramData", r"C:\\ProgramData")) / "Microsoft/Windows Defender/Platform"]
    exe = next((p / "MpCmdRun.exe" for p in roots if (p / "MpCmdRun.exe").is_file()), None)
    if exe is None and roots[1].is_dir():
        versions = sorted(roots[1].glob("*/MpCmdRun.exe"), reverse=True)
        exe = versions[0] if versions else None
    if exe is None:
        raise RuntimeError("Microsoft Defender scanner was not found. Check Windows Security.")
    subprocess.Popen([str(exe), "-Scan", "-ScanType", "1"],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return "Microsoft Defender quick scan started. Real-time protection settings were not changed."


def schedule_power_action(kind: str) -> str:
    if kind == "restart":
        args = ["shutdown.exe", "/r", "/t", "60", "/c", "Restart scheduled by JARVIS"]
    elif kind == "shutdown":
        args = ["shutdown.exe", "/s", "/t", "60", "/c", "Shutdown scheduled by JARVIS"]
    else:
        raise ValueError("Unknown power action.")
    subprocess.Popen(args, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return f"Windows {kind} scheduled in 60 seconds. Say 'cancel shutdown' to cancel it."


def cancel_power_action() -> str:
    subprocess.run(["shutdown.exe", "/a"], capture_output=True, shell=False)
    return "Windows shutdown or restart request cancelled, if one was pending."


def lock_pc() -> str:
    if platform.system() != "Windows":
        raise RuntimeError("PC lock is available on Windows.")
    ctypes.windll.user32.LockWorkStation()
    return "Locking Windows."


def install_approved_app(name: str, upgrade: bool=False) -> str:
    key=name.strip().lower()
    if key not in APPROVED_WINGET_APPS:
        raise ValueError("That app is not on JARVIS's approved install list. Available: "+", ".join(APPROVED_WINGET_APPS))
    if platform.system() != "Windows":
        raise RuntimeError("App installation is available only on Windows.")
    winget=shutil.which("winget")
    if not winget: raise RuntimeError("Windows Package Manager (winget) was not found.")
    package=APPROVED_WINGET_APPS[key]
    args=[winget,"upgrade" if upgrade else "install","--id",package,"--exact","--silent","--accept-package-agreements","--accept-source-agreements"]
    result=subprocess.run(args,capture_output=True,text=True,timeout=900,shell=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[-1500:] or "winget could not complete the request.")
    return f"{'Updated' if upgrade else 'Installed'} {key} using Windows Package Manager."
