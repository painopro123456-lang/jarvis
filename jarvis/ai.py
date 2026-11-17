"""Local-first JARVIS agent powered by Ollama; no cloud account or API key."""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Callable

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
def _choose_model() -> str:
    """Choose a modest local model based on installed physical RAM."""
    try:
        import psutil
        ram = psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        ram = 8
    # Small enough for older laptops; users with more RAM get a stronger model.
    return "qwen3.5:4b" if ram >= 16 else ("qwen3.5:2b" if ram >= 8 else "qwen3.5:0.8b")


MODEL = os.getenv("JARVIS_LOCAL_MODEL") or _choose_model()
_HISTORY: list[dict] = []
_SERVER_PROCESS = None
_PULL_PROCESS = None


def ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def _request(path: str, payload: dict | None = None, timeout: int = 8):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL + path, data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def server_running() -> bool:
    try:
        _request("/api/version", timeout=2)
        return True
    except Exception:
        return False


def start_server() -> bool:
    global _SERVER_PROCESS
    if server_running():
        return True
    executable = shutil.which("ollama")
    if not executable:
        return False
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        _SERVER_PROCESS = subprocess.Popen(
            [executable, "serve"], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    except Exception:
        return False
    for _ in range(20):
        time.sleep(0.25)
        if server_running():
            return True
    return server_running()


def installed_models() -> set[str]:
    try:
        result = _request("/api/tags", timeout=5)
        return {str(m.get("name", "")) for m in result.get("models", [])}
    except Exception:
        return set()


def model_installed() -> bool:
    models = installed_models()
    return MODEL in models or MODEL + ":latest" in models


def is_ready() -> bool:
    return server_running() and model_installed()


def setup_status() -> str:
    if not ollama_installed():
        return "Ollama is not installed. Install the free local runtime first."
    if not server_running():
        return "Starting local AI runtime…"
    if not model_installed():
        return f"Local model not downloaded yet: {MODEL}"
    return f"LOCAL AI READY · {MODEL}"


def start_model_download():
    """Start model download in background; returns a human-readable status."""
    global _PULL_PROCESS
    if not ollama_installed():
        return "Install Ollama first using the official download page."
    if not start_server():
        return "Ollama could not start. Restart Ollama and try again."
    if model_installed():
        return f"{MODEL} is already installed and ready."
    if _PULL_PROCESS is not None and _PULL_PROCESS.poll() is None:
        return f"Downloading {MODEL} already."
    executable = shutil.which("ollama")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        _PULL_PROCESS = subprocess.Popen(
            [executable, "pull", MODEL], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        return (f"Downloading {MODEL} in the background. This is a one-time model "
                "download; after it finishes, JARVIS runs locally without an API key.")
    except Exception as exc:
        return f"Could not start model download: {exc}"


def _tool(name: str, description: str, properties: dict | None = None,
          required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object", "properties": properties or {},
                "required": required or [], "additionalProperties": False,
            },
        },
    }


TOOLS = [
    _tool("get_system_status", "Read current CPU, RAM, disk and battery telemetry."),
    _tool("list_processes", "List the top running processes by memory use."),
    _tool("inspect_startup_apps", "Read Windows startup app entries without changing them."),
    _tool("get_defender_status", "Read Microsoft Defender protection status."),
    _tool("start_defender_quick_scan", "Start a Microsoft Defender quick malware scan."),
    _tool("open_app_or_path", "Open an installed Windows app, known folder, or existing path.",
          {"target": {"type": "string"}}, ["target"]),
    _tool("set_power_plan", "Change Windows power plan.",
          {"plan": {"type": "string", "enum": ["balanced", "high performance", "ultimate performance"]}},
          ["plan"]),
    _tool("terminate_process", "Terminate a process by PID. This can lose unsaved work.",
          {"pid": {"type": "integer"}}, ["pid"]),
    _tool("lock_pc", "Lock the current Windows session."),
    _tool("schedule_power_action", "Schedule Windows restart or shutdown after 60 seconds.",
          {"action": {"type": "string", "enum": ["restart", "shutdown"]}}, ["action"]),
    _tool("cancel_power_action", "Cancel a pending Windows shutdown or restart."),
    _tool("get_firewall_status", "Read Windows Firewall profile status."),
    _tool("inspect_network_connections", "List visible active remote network connections for review."),
    _tool("inspect_suspicious_processes", "List process indicators that deserve review; never label them malware without evidence."),
    _tool("scan_file_with_defender", "Ask Microsoft Defender to scan one existing file.", {"path": {"type": "string"}}, ["path"]),
    _tool("create_restore_point", "Create a Windows restore point before a major settings change."),
    _tool("remember_preference", "Save a user preference locally on this PC.", {"key": {"type": "string"}, "value": {"type": "string"}}, ["key", "value"]),
    _tool("remember_note", "Save a note to private local JARVIS memory.", {"note": {"type": "string"}}, ["note"]),
    _tool("read_memory", "Read saved local JARVIS memories."),
    _tool("clear_memory", "Clear all local JARVIS memory. Requires confirmation."),
    _tool("save_automation_routine", "Save a disabled automation routine for the user to review.", {"name": {"type": "string"}, "instruction": {"type": "string"}}, ["name", "instruction"]),
    _tool("list_automation_routines", "List saved automation routines."),
    _tool("install_approved_app", "Install an app from JARVIS's small allow-list using Windows Package Manager.", {"app": {"type": "string", "enum": ["7zip","vlc","notepad++","firefox","google chrome","obs","discord","steam"]}}, ["app"]),
    _tool("upgrade_approved_app", "Update an app from JARVIS's small allow-list using Windows Package Manager.", {"app": {"type": "string", "enum": ["7zip","vlc","notepad++","firefox","google chrome","obs","discord","steam"]}}, ["app"]),
    _tool("run_pc_diagnostics", "Collect read-only system, disk and recent Windows error diagnostics."),
    _tool("find_duplicate_files", "Find duplicate files in Desktop, Documents and Downloads without deleting anything."),
]


def _execute(name: str, args: dict, confirm: Callable[[str], bool] | None) -> str:
    from jarvis import actions, system_monitor, security, memory, automation, diagnostics, file_tools
    if name == "get_system_status":
        d = system_monitor.snapshot()
        return json.dumps({k: d[k] for k in (
            "host", "os", "cpu", "memory_percent", "memory_used_gb",
            "memory_total_gb", "disk_percent", "disk_free_gb", "battery"
        )})
    if name == "list_processes":
        return actions.process_report()
    if name == "inspect_startup_apps":
        return actions.startup_report()
    if name == "get_defender_status":
        return actions.defender_status()
    if name == "open_app_or_path":
        return actions.open_target(str(args["target"])[:500])
    if name == "start_defender_quick_scan":
        if confirm and not confirm("Start a Microsoft Defender quick scan?"):
            return "User cancelled the scan."
        return actions.start_defender_quick_scan()
    if name == "set_power_plan":
        plan = args["plan"]
        if confirm and not confirm(f"Change Windows power plan to {plan}?"):
            return "User cancelled the power plan change."
        return actions.set_power_plan(plan)
    if name == "terminate_process":
        pid = int(args["pid"])
        if confirm and not confirm(f"Terminate process PID {pid}? This may close an app and lose unsaved work."):
            return "User cancelled process termination."
        return actions.terminate_process(str(pid))
    if name == "lock_pc":
        if confirm and not confirm("Lock this Windows PC now?"):
            return "User cancelled locking the PC."
        return actions.lock_pc()
    if name == "schedule_power_action":
        action = args["action"]
        if confirm and not confirm(f"Schedule Windows {action} in 60 seconds?"):
            return "User cancelled the power action."
        return actions.schedule_power_action(action)
    if name == "cancel_power_action":
        return actions.cancel_power_action()
    if name == "get_firewall_status":
        return security.firewall_status()
    if name == "inspect_network_connections":
        return security.network_connections()
    if name == "inspect_suspicious_processes":
        return security.inspect_processes()
    if name == "scan_file_with_defender":
        path = str(args["path"])[:1000]
        if confirm and not confirm(f"Ask Microsoft Defender to scan this file?\\n{path}"):
            return "File scan cancelled."
        return security.scan_file(path)
    if name == "create_restore_point":
        if confirm and not confirm("Create a Windows restore point? This may take a minute and requires administrator mode."):
            return "Restore point creation cancelled."
        return security.create_restore_point()
    if name == "remember_preference":
        return memory.set_preference(str(args["key"]), str(args["value"]))
    if name == "remember_note":
        return memory.remember(str(args["note"]))
    if name == "read_memory":
        return memory.summary()
    if name == "clear_memory":
        if confirm and not confirm("Permanently clear JARVIS's locally saved notes and preferences?"):
            return "Memory clear cancelled."
        return memory.clear()
    if name == "save_automation_routine":
        return automation.add_routine(str(args["name"]), str(args["instruction"]))
    if name == "list_automation_routines":
        return automation.report()
    if name == "install_approved_app":
        app=str(args["app"]).lower()
        if confirm and not confirm(f"Install {app} using Windows Package Manager?"):
            return "Installation cancelled."
        return actions.install_approved_app(app, upgrade=False)
    if name == "upgrade_approved_app":
        app=str(args["app"]).lower()
        if confirm and not confirm(f"Update {app} using Windows Package Manager?"):
            return "Update cancelled."
        return actions.install_approved_app(app, upgrade=True)
    if name == "run_pc_diagnostics":
    if name == "find_duplicate_files":
        return file_tools.find_duplicates()
        return diagnostics.report()
    return "Tool not available."


SYSTEM_PROMPT = """You are JARVIS, a sharp, composed, witty personal AI assistant inspired by a capable executive aide.
Be genuinely useful, curious, independent-minded and conversational. Do not blindly agree with the user.
If the user's claim is factually wrong, respectfully say so, explain the evidence and offer the correction.
If you disagree with a plan, explain the risks and recommend a better one. You may challenge assumptions and
ask pointed but respectful questions. Never argue just to win: when the user provides better evidence,
update your view, acknowledge the error plainly and move on. Separate facts, estimates and uncertainty.
Use concise natural language, with occasional dry wit, not canned robotic phrases. Address the user as 'sir'
only occasionally, not in every reply. Understand requests in context and use available PC tools when helpful. Use local memory only when the user asks you to remember something or when a preference is clearly durable; explain that memory is stored on this PC. For automation, save routines disabled and never imply they run in the background unless a scheduler has actually been configured. For security, treat process/network indicators as leads, not proof of malware. Create a restore point before major system changes when available.
Never claim an action succeeded unless a tool returned success. The tools are a strict allow-list: do not
invent tools, execute shell commands, run arbitrary code, exfiltrate secrets, delete files, or disable
Defender/firewall/security. Explain consequential changes and require confirmation through the app.
If a requested capability is unavailable, say so honestly and suggest a safe next step."""


def respond(message: str, confirm: Callable[[str], bool] | None = None) -> str:
    if not message.strip():
        return "I'm listening."
    if not start_server():
        raise RuntimeError("Local AI is unavailable. Install Ollama from https://ollama.com/download/windows.")
    if not model_installed():
        raise RuntimeError(f"JARVIS's local model ({MODEL}) is still downloading. Please wait for setup to finish.")
    _HISTORY.append({"role": "user", "content": message[:4000]})
    del _HISTORY[:-24]
    for _ in range(5):
        payload = {
            "model": MODEL,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + _HISTORY,
            "tools": TOOLS,
            "stream": False,
            "options": {"temperature": 0.65, "num_ctx": 8192, "num_predict": 1200},
        }
        try:
            result = _request("/api/chat", payload, timeout=180)
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Could not reach local Ollama: {exc}") from exc
        msg = result.get("message") or {}
        calls = msg.get("tool_calls") or []
        if not calls:
            answer = (msg.get("content") or "I'm here. What would you like to tackle?").strip()
            _HISTORY.append({"role": "assistant", "content": answer})
            return answer
        _HISTORY.append(msg)
        for call in calls:
            fn = call.get("function") or {}
            name = fn.get("name", "")
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            try:
                output = _execute(name, args, confirm)
            except Exception as exc:
                output = f"Action failed: {exc}"
            _HISTORY.append({
                "role": "tool", "tool_name": name, "content": str(output)[:6000]
            })
    return "I've reached my safe action limit for this request. Tell me which part you'd like me to continue with."


VISION_MODEL = os.getenv("JARVIS_VISION_MODEL", "qwen2.5vl:3b")

def vision_model_installed() -> bool:
    return VISION_MODEL in installed_models() or VISION_MODEL + ":latest" in installed_models()

def start_vision_download() -> str:
    if not ollama_installed():
        return "Install Ollama first."
    if not start_server():
        return "Ollama could not start."
    if vision_model_installed():
        return f"{VISION_MODEL} is already installed."
    executable=shutil.which("ollama")
    flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
    subprocess.Popen([executable,"pull",VISION_MODEL],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
    return f"Downloading optional screen-vision model {VISION_MODEL}. This is a separate, potentially large download."

def analyze_image(image_path: str, question: str="Describe what is visible and help troubleshoot it.") -> str:
    if not vision_model_installed():
        return f"Screen vision is not installed. Use ENABLE SCREEN VISION to download {VISION_MODEL} (a separate large model)."
    with open(image_path,"rb") as image_file:
        encoded=base64.b64encode(image_file.read()).decode("ascii")
    result=_request("/api/chat",{
        "model":VISION_MODEL,
        "messages":[{"role":"user","content":question[:2000],"images":[encoded]}],
        "stream":False,
        "options":{"temperature":0.3,"num_predict":900}
    },timeout=180)
    return (result.get("message") or {}).get("content","The vision model returned no description.")
