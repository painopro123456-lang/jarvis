"""Windows controls exposed through explicit, allow-listed operations."""
from __future__ import annotations

import ctypes
import difflib
import os
import platform
import subprocess
import sys
import shutil
import webbrowser
from pathlib import Path

import psutil

APP_ALIASES = {
    "notepad": "notepad.exe", "calculator": "calc.exe", "paint": "mspaint.exe",
    "task manager": "taskmgr.exe", "file explorer": "explorer.exe",
    "settings": "ms-settings:", "task scheduler": "taskschd.msc", "resource monitor": "resmon.exe", "services": "services.msc", "windows security": "ms-settings:windowsdefender",
}
APPROVED_WINGET_APPS = {
    "7zip": "7zip.7zip", "vlc": "VideoLAN.VLC", "notepad++": "Notepad++.Notepad++",
    "firefox": "Mozilla.Firefox", "google chrome": "Google.Chrome", "obs": "OBSProject.OBSStudio",
    "discord": "Discord.Discord", "steam": "Valve.Steam",
}

EXECUTABLE_SUFFIXES = {
    ".exe", ".com", ".scr", ".bat", ".cmd", ".ps1", ".psm1", ".vbs",
    ".vbe", ".js", ".jse", ".wsf", ".wsh", ".hta", ".jar", ".msi",
    ".msp", ".lnk", ".reg",
}
PROTECTED_PROCESS_NAMES = {
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe",
    "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe",
}

POWER_PLANS = {
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


def _start_menu_shortcuts():
    """Return installed-app shortcuts from the current user's and common Start Menus."""
    roots = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
    ]
    found = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for shortcut in root.rglob("*.lnk"):
                if shortcut.is_file():
                    found.append(shortcut)
                    if len(found) >= 2500:
                        return found
        except (OSError, PermissionError):
            continue
    return found


def _find_start_menu_app(query: str):
    wanted = " ".join(query.casefold().split())
    matches = []
    for shortcut in _start_menu_shortcuts():
        label = shortcut.stem
        normal = " ".join(label.casefold().replace("&", " ").split())
        if wanted == normal or wanted.replace(" ", "") == normal.replace(" ", ""):
            return [shortcut]
        ratio = difflib.SequenceMatcher(None, wanted, normal).ratio()
        if wanted in normal or ratio >= 0.78:
            matches.append((ratio, shortcut))
    matches.sort(key=lambda item: item[0], reverse=True)
    if not matches:
        return []
    best = matches[0][0]
    # Do not guess between similarly named apps.
    return [path for score, path in matches[:5] if score >= max(0.78, best - 0.08)]


def open_target(target: str, confirm=None) -> str:
    key = target.strip().lower()
    if key in APP_ALIASES:
        value = APP_ALIASES[key]
        if value.startswith("ms-"):
            os.startfile(value)
        elif value.casefold().endswith(".msc"):
            # .msc files are MMC snap-ins, not standalone executables.
            subprocess.Popen(["mmc.exe", value], shell=False)
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
        resolved = path.resolve()
        if resolved.is_file() and resolved.suffix.casefold() in EXECUTABLE_SUFFIXES:
            if not confirm or not confirm(
                f"Run this executable or script?\n{resolved}\nOnly continue if you trust its source."
            ):
                return "Opening executable cancelled."
        os.startfile(str(resolved))
        return f"Opening {resolved}."
    executable = shutil.which(target.strip())
    if executable:
        executable_path = Path(executable)
        if executable_path.suffix.casefold() in EXECUTABLE_SUFFIXES:
            if not confirm or not confirm(
                f"Run this executable?\n{executable_path}\nOnly continue if you trust its source."
            ):
                return "Opening executable cancelled."
        subprocess.Popen([executable], shell=False)
        return f"Launching {target}."
    if platform.system() == "Windows":
        matches = _find_start_menu_app(target)
        if len(matches) == 1:
            os.startfile(str(matches[0]))
            return f"Opening {matches[0].stem}."
        if len(matches) > 1:
            names = ", ".join(path.stem for path in matches)
            raise ValueError(f"I found several similar Start Menu apps: {names}. Tell me the exact app name.")
    raise ValueError("I couldn't find that app or path. Try its Start Menu name or a full file/folder path.")


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
    if pid in (0, 1, 4, os.getpid()):
        raise ValueError("That process is protected or is JARVIS itself.")
    proc = psutil.Process(pid)
    name = proc.name()
    if name.casefold() in PROTECTED_PROCESS_NAMES:
        raise ValueError(f"JARVIS will not terminate critical Windows process '{name}'.")
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



def search_software(query: str) -> str:
    """Search winget catalogue without installing or changing anything."""
    search = " ".join(str(query).strip().split())
    if not search or len(search) > 100:
        raise ValueError("Enter a search phrase between 1 and 100 characters.")
    if any(ch in search for ch in ("\r", "\n", "\0")):
        raise ValueError("That search phrase contains invalid characters.")
    if platform.system() != "Windows":
        raise RuntimeError("Software discovery is available only on Windows.")
    winget = shutil.which("winget")
    if not winget:
        raise RuntimeError("Windows Package Manager (winget) was not found. Install or update App Installer from Microsoft Store.")
    args = [winget, "search", "--query", search, "--source", "winget",
            "--accept-source-agreements", "--disable-interactivity"]
    result = subprocess.run(args, capture_output=True, text=True, timeout=90, shell=False)
    output = (result.stdout or "").strip()
    if result.returncode:
        details = (result.stderr or output).strip()[-1200:]
        raise RuntimeError(details or "The Windows Package Manager catalogue search failed.")
    if not output:
        return f"No catalogue matches found for: {search}"
    return ("Read-only Windows Package Manager search results for "
            + repr(search) + ". These are candidates, not endorsements; compare publisher and app purpose before choosing.\n"
            + output[-4500:])


def manage_software(name: str, upgrade: bool = False) -> str:
    """Install/update a specifically named app via winget, without a hard-coded app allow-list."""
    app_name = " ".join(str(name).strip().split())
    if not app_name or len(app_name) > 120:
        raise ValueError("Enter a software name between 1 and 120 characters.")
    if any(ch in app_name for ch in ("\r", "\n", "\0")):
        raise ValueError("That software name contains invalid characters.")
    if platform.system() != "Windows":
        raise RuntimeError("Software management is available only on Windows.")
    winget = shutil.which("winget")
    if not winget:
        raise RuntimeError("Windows Package Manager (winget) was not found. Install or update App Installer from Microsoft Store.")
    verb = "upgrade" if upgrade else "install"
    args = [
        winget, verb, "--name", app_name, "--exact",
        "--source", "winget", "--silent",
        "--accept-package-agreements", "--accept-source-agreements",
        "--disable-interactivity",
    ]
    result = subprocess.run(args, capture_output=True, text=True, timeout=1200, shell=False)
    if result.returncode:
        details = (result.stderr or result.stdout).strip()[-1800:]
        if not details:
            details = "winget could not find one exact package match or the operation failed."
        raise RuntimeError(details)
    return f"{'Updated' if upgrade else 'Installed'} {app_name} through Windows Package Manager.\n\nVerification output:\n{(result.stdout or 'winget completed successfully.').strip()[-1200:]}"
