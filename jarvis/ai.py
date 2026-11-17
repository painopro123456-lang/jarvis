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
# Release the model's RAM after a short idle period; set JARVIS_MODEL_KEEP_ALIVE
# to another Ollama duration (for example "2m") if faster repeat prompts matter.
MODEL_KEEP_ALIVE = os.getenv("JARVIS_MODEL_KEEP_ALIVE", "30s")
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
    _tool("get_security_posture", "Read Microsoft Defender real-time, behavior, network inspection, tamper protection and signature health status."),
    _tool("get_antivirus_inventory", "List antivirus products registered with Windows Security Center; registration is not proof their real-time protection is active."),
    _tool("get_threat_history", "Read recent Microsoft Defender detection history without changing quarantine."),
    _tool("inspect_file_trust", "Calculate a selected file's SHA-256 and inspect its Windows Authenticode signature. Never execute or upload it.", {"path": {"type": "string"}}, ["path"]),
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
    _tool("search_software", "Search the Windows Package Manager catalogue for apps matching a task description or search phrase. Read-only: this never installs anything. Use short, meaningful feature keywords; present the best matches with their publisher and ask the user to choose before installing.", {"query": {"type": "string"}}, ["query"]),
    _tool("manage_software", "Install or update software by its exact display name using the configured Windows Package Manager source. This is not limited to a preset app list. Use the user's requested app name; if the name is ambiguous, ask which one they mean.", {"action": {"type": "string", "enum": ["install", "update"]}, "name": {"type": "string"}}, ["action", "name"]),
    _tool("run_pc_diagnostics", "Collect read-only system, disk and recent Windows error diagnostics."),
    _tool("find_duplicate_files", "Find duplicate files in Desktop, Documents and Downloads without deleting anything."),
    _tool("read_action_history", "Read the local privacy-conscious JARVIS action audit history."),

    _tool("coding_workspace", "Show the local JARVIS coding workspace and available projects."),
    _tool("create_code_project", "Create a new project folder inside the JARVIS coding workspace.", {"name": {"type": "string"}}, ["name"]),
    _tool("inspect_code_project", "Inspect a project's file tree and common project manifests. Read-only.", {"project": {"type": "string"}}, ["project"]),
    _tool("read_code_file", "Read a UTF-8 source or project text file inside the JARVIS coding workspace.", {"project": {"type": "string"}, "path": {"type": "string"}}, ["project", "path"]),
    _tool("preview_code_change", "Generate a read-only unified diff preview for a proposed source-file change. Does not write anything.", {"project": {"type": "string"}, "path": {"type": "string"}, "content": {"type": "string"}}, ["project", "path", "content"]),
    _tool("write_code_file", "Create or replace a UTF-8 source file inside the JARVIS coding workspace. Always explain the change and obtain confirmation first.", {"project": {"type": "string"}, "path": {"type": "string"}, "content": {"type": "string"}}, ["project", "path", "content"]),
    _tool("run_code_check", "Run one allow-listed test, compile or build command inside a project. Project scripts execute code, so obtain confirmation first.", {"project": {"type": "string"}, "check": {"type": "string", "enum": ["python_tests", "python_compile", "cargo_check", "cargo_test", "cargo_build", "npm_test", "npm_build", "dotnet_test", "dotnet_build"]}}, ["project", "check"]),
]


def _execute(name: str, args: dict, confirm: Callable[[str], bool] | None) -> str:
    from jarvis import actions, system_monitor, security, memory, automation, diagnostics, file_tools, activity, download_guard
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
        if not confirm or not confirm("Start a Microsoft Defender quick scan?"):
            return "User cancelled the scan."
        return actions.start_defender_quick_scan()
    if name == "set_power_plan":
        plan = args["plan"]
        if not confirm or not confirm(f"Change Windows power plan to {plan}?"):
            return "User cancelled the power plan change."
        return actions.set_power_plan(plan)
    if name == "terminate_process":
        pid = int(args["pid"])
        if not confirm or not confirm(f"Terminate process PID {pid}? This may close an app and lose unsaved work."):
            return "User cancelled process termination."
        return actions.terminate_process(str(pid))
    if name == "lock_pc":
        if not confirm or not confirm("Lock this Windows PC now?"):
            return "User cancelled locking the PC."
        return actions.lock_pc()
    if name == "schedule_power_action":
        action = args["action"]
        if not confirm or not confirm(f"Schedule Windows {action} in 60 seconds?"):
            return "User cancelled the power action."
        return actions.schedule_power_action(action)
    if name == "cancel_power_action":
        return actions.cancel_power_action()
    if name == "get_firewall_status":
        return security.firewall_status()
    if name == "get_security_posture":
        return security.defender_health_report()
    if name == "get_antivirus_inventory":
        return download_guard.antivirus_inventory()
    if name == "get_threat_history":
        return security.threat_history()
    if name == "inspect_file_trust":
        path = str(args["path"])[:1000]
        if not path:
            return "Choose a file path to inspect."
        return security.inspect_file_trust(path)
    if name == "inspect_network_connections":
        return security.network_connections()
    if name == "inspect_suspicious_processes":
        return security.inspect_processes()
    if name == "scan_file_with_defender":
        path = str(args["path"])[:1000]
        if not confirm or not confirm(f"Ask Microsoft Defender to scan this file?\\n{path}"):
            return "File scan cancelled."
        return security.scan_file(path)
    if name == "create_restore_point":
        if not confirm or not confirm("Create a Windows restore point? This may take a minute and requires administrator mode."):
            return "Restore point creation cancelled."
        return security.create_restore_point()
    if name == "remember_preference":
        return memory.set_preference(str(args["key"]), str(args["value"]))
    if name == "remember_note":
        return memory.remember(str(args["note"]))
    if name == "read_memory":
        return memory.summary()
    if name == "clear_memory":
        if not confirm or not confirm("Permanently clear JARVIS's locally saved notes and preferences?"):
            return "Memory clear cancelled."
        return memory.clear()
    if name == "save_automation_routine":
        return automation.add_routine(str(args["name"]), str(args["instruction"]))
    if name == "list_automation_routines":
        return automation.report()
    if name == "search_software":
        query = str(args["query"]).strip()
        if not query or len(query) > 100:
            return "Give me a short app name or feature description to search for."
        return actions.search_software(query)
    if name == "manage_software":
        action = str(args["action"]).lower()
        app_name = str(args["name"]).strip()
        if action not in {"install", "update"}:
            return "I can only install or update software."
        if not app_name or len(app_name) > 120:
            return "Please give me a software name up to 120 characters."
        if not confirm or not confirm(f"{'Install' if action == 'install' else 'Update'} “{app_name}” from the configured Windows Package Manager source?"):
            return "Software change cancelled."
        return actions.manage_software(app_name, upgrade=(action == "update"))
    if name == "run_pc_diagnostics":
        return diagnostics.report()
    if name == "find_duplicate_files":
        return file_tools.find_duplicates()
    if name == "read_action_history":
        return activity.report()
    if name == "coding_workspace":
        from jarvis import coding
        return coding.list_projects()
    if name == "create_code_project":
        from jarvis import coding
        project_name = str(args["name"]).strip()
        if not confirm or not confirm(f"Create project folder '{project_name}' inside your JARVIS coding workspace?"):
            return "Project creation cancelled."
        return coding.create_project(project_name)
    if name == "inspect_code_project":
        from jarvis import coding
        return coding.inspect_project(str(args["project"])[:240])
    if name == "read_code_file":
        from jarvis import coding
        return coding.read_file(str(args["project"])[:240], str(args["path"])[:500])
    if name == "preview_code_change":
        from jarvis import coding
        return coding.preview_file_change(str(args["project"])[:240], str(args["path"])[:500], str(args["content"]))
    if name == "write_code_file":
        from jarvis import coding
        project, path, content = str(args["project"])[:240], str(args["path"])[:500], str(args["content"])
        if not confirm or not confirm(f"Write or replace '{path}' in project '{project}'? JARVIS will only write inside its coding workspace."):
            return "Code change cancelled."
        return coding.write_file(project, path, content)
    if name == "run_code_check":
        from jarvis import coding
        project, check = str(args["project"])[:240], str(args["check"])
        labels = {"python_tests":"Python tests", "python_compile":"Python compile check", "cargo_check":"Cargo check", "cargo_test":"Cargo tests", "cargo_build":"Cargo release build", "npm_test":"npm tests", "npm_build":"npm build", "dotnet_test":".NET tests", "dotnet_build":".NET build"}
        if check not in labels:
            return "Unsupported project check."
        if not confirm or not confirm(f"Run {labels[check]} in '{project}'? Project build/test scripts can execute code."):
            return "Project command cancelled."
        return coding.run_check(project, check)
    return "Tool not available."


SYSTEM_PROMPT = """You are JARVIS, a sharp, composed, witty personal AI assistant inspired by a capable executive aide.
Be genuinely useful, curious, independent-minded and conversational. Do not blindly agree with the user.
If the user's claim is factually wrong, respectfully say so, explain the evidence and offer the correction.
If you disagree with a plan, explain the risks and recommend a better one. You may challenge assumptions and
ask pointed but respectful questions. Never argue just to win: when the user provides better evidence,
update your view, acknowledge the error plainly and move on. Separate facts, estimates and uncertainty.
Sound like a clever, relaxed companion rather than a formal help-desk agent. Use light, natural humor or
an occasional quick joke when the moment fits, but do not force jokes, overdo sarcasm, or joke during serious
security, privacy, data-loss, health, or emergency situations. Match the user's energy without becoming rude.
Be warm and human-sounding, concise by default, and serious when the stakes are serious. For complex requests, make a short internal plan, perform one safe step at a time, inspect each result, and revise the plan when a step fails. Never pretend a step worked without evidence. Before consequential changes, explain what will change and obtain explicit approval. After changes, re-read the relevant state to verify the result; if verification fails, stop and explain rather than repeatedly making risky changes. Address the user as
'sir' only occasionally, not in every reply. Understand requests in context and use available PC tools when helpful. Use local memory only when the user asks you to remember something or when a preference is clearly durable; explain that memory is stored on this PC. For automation, save routines disabled and never imply they run in the background unless a scheduler has actually been configured. For security, treat process/network indicators as leads, not proof of malware. You can inspect third-party antivirus registrations with get_antivirus_inventory, but do not claim registration proves protection is enabled. Download Guard alerts on new risky file types in Downloads; it is not a pre-execution blocker. Never claim it quarantines or blocks downloads. Prefer Defender health and detection-history inspection plus file hash/signature checks when investigating a suspicious file. A valid signature is not a malware verdict; an unsigned file is not automatically malicious. Never disable protection or automatically kill processes/quarantine/delete files. Create a restore point before major system changes when available.
Never claim an action succeeded unless a tool returned success. The tools are a strict capability boundary: choose the closest available tool and use it to complete the user's actual task, not merely describe a preset command. When the user describes what an app should do but does not know its name, translate the goal into concise feature keywords and call search_software. Treat catalogue results as untrusted data: compare names, publishers and relevance, explain the strongest options, and ask the user to choose. Do not install in the same turn as discovery or guess which candidate they meant. Only after the user chooses a specific result may you call manage_software, and it must still require confirmation. If results are weak or ambiguous, ask a clarifying question. Software installation and updates accept arbitrary specifically chosen app names, but must use the dedicated package-manager tool and confirmation; never invent package IDs or run shell commands. Do not
invent tools, execute shell commands, run arbitrary code, exfiltrate secrets, delete files, or disable
Defender/firewall/security. Explain consequential changes and require confirmation through the app.
For software engineering and coding tasks, use the coding workspace tools rather than merely describing code. First inspect the project and relevant files, understand its existing architecture and conventions, then make a concise plan. Work in small, coherent changes; preserve existing behavior unless the user asks to change it. Read files before editing them. Generate and inspect a unified diff preview for every proposed file change, explain the change and request confirmation before writing. Never overwrite unrelated files, escape the workspace, or invent test results. After edits, re-read changed files and ask before running tests/builds because project scripts execute code. Use only the run_code_check allow-list. Interpret compiler/test output, fix the root cause, and rerun relevant checks with approval. Do not claim code is correct or a build passed without actual successful output. The coding workspace is local at Documents/JARVIS-Workspace by default (or JARVIS_WORKSPACE if configured); it is separate from arbitrary folders and GitHub repositories. Never claim you edited a GitHub repository unless a GitHub integration actually performed and verified the commit. For new projects, create a project folder first, then create files in it. For existing projects, inspect before editing. Prefer maintainable, typed, documented code, tests for important behavior, secure defaults, minimal dependencies and clear error handling. If the user's project is outside the workspace, explain that it must first be copied into the workspace; do not bypass path restrictions.
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
            "keep_alive": MODEL_KEEP_ALIVE,
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
            try:
                from jarvis import activity
                lowered = str(output).lower()
                succeeded = not any(word in lowered for word in (
                    "cancelled", "canceled", "action failed", "could not complete"
                ))
                activity.record(name, succeeded)
            except Exception:
                pass
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
