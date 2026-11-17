"""OpenAI-powered JARVIS brain with a small, explicit Windows tool allow-list.

The model can plan and request tools, but it cannot execute shell commands, write
arbitrary code, or access files outside the operations implemented below.
"""
from __future__ import annotations

import json
import os
from typing import Callable

SERVICE_NAME = "JARVIS.OpenAI"
ACCOUNT_NAME = "default"
MODEL = os.getenv("JARVIS_MODEL", "gpt-5.5")
_HISTORY: list[dict] = []


def get_api_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    try:
        import keyring
        return keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
    except Exception:
        return None


def save_api_key(key: str) -> None:
    key = key.strip()
    if not key.startswith("sk-") or len(key) < 20:
        raise ValueError("That doesn't look like an OpenAI API key.")
    try:
        import keyring
        keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, key)
    except Exception as exc:
        raise RuntimeError(
            "Windows Credential Manager could not save the key. "
            "Set OPENAI_API_KEY in Windows environment variables instead."
        ) from exc


def remove_api_key() -> None:
    try:
        import keyring
        keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
    except Exception:
        pass


def has_api_key() -> bool:
    return bool(get_api_key())


def _tool(name: str, description: str, properties: dict | None = None,
          required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


TOOLS = [
    _tool("get_system_status", "Read current CPU, RAM, disk and battery telemetry."),
    _tool("list_processes", "List the top running processes by memory use."),
    _tool("inspect_startup_apps", "Read the Windows startup app entries. Does not change them."),
    _tool("get_defender_status", "Read Microsoft Defender protection status."),
    _tool("start_defender_quick_scan", "Start a Microsoft Defender quick malware scan."),
    _tool("open_app_or_path", "Open an installed allow-listed Windows app, known folder, or existing path.",
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
]


def _execute(name: str, args: dict, confirm: Callable[[str], bool] | None) -> str:
    from jarvis import actions, system_monitor

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
        target = str(args["target"])[:500]
        return actions.open_target(target)
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
        if confirm and not confirm(
            f"Terminate process PID {pid}? This may close an app and lose unsaved work."
        ):
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
    return "Tool not available."


def respond(message: str, confirm: Callable[[str], bool] | None = None) -> str:
    """Ask the model to respond and optionally call approved local tools."""
    key = get_api_key()
    if not key:
        raise RuntimeError(
            "OpenAI isn't connected yet. Click AI SETUP and add your OpenAI API key. "
            "You can still use the built-in basic commands."
        )
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, timeout=45.0, max_retries=1)
        if not _HISTORY:
            _HISTORY.append({
                "role": "system",
                "content": (
                    "You are JARVIS, a capable Windows PC assistant. Speak naturally and "
                    "concisely. Understand the user's intent, ask a short clarification when "
                    "needed, and use the provided tools for PC facts/actions. Never claim an "
                    "action succeeded unless its tool returned success. Explain what you are "
                    "about to change. Tool calls are limited to the listed allow-list. Never "
                    "invent tool results, never request arbitrary terminal execution, never "
                    "disable antivirus/firewall/security, never exfiltrate secrets, and never "
                    "delete user files. Ask the user before risky actions; the app enforces "
                    "confirmation for supported risky tools. If a requested capability is not "
                    "available, say so honestly and suggest a safe next step."
                ),
            })
        _HISTORY.append({"role": "user", "content": message[:4000]})
        # Keep a bounded conversation while preserving the system instructions.
        del _HISTORY[1:max(1, len(_HISTORY) - 18)]
        for _ in range(5):
            completion = client.chat.completions.create(
                model=MODEL,
                messages=_HISTORY,
                tools=TOOLS,
                tool_choice="auto",
                parallel_tool_calls=False,
            )
            msg = completion.choices[0].message
            if not msg.tool_calls:
                answer = (msg.content or "I'm here. What should I do?").strip()
                _HISTORY.append({"role": "assistant", "content": answer})
                return answer
            _HISTORY.append(msg.model_dump(exclude_none=True))
            for call in msg.tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                    result = _execute(call.function.name, args, confirm)
                except Exception as exc:
                    result = f"Action failed: {exc}"
                _HISTORY.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(result)[:6000],
                })
        return "I completed the available tool steps, but reached my action limit. What would you like me to check next?"
    except Exception as exc:
        # Do not silently switch to a weaker mode after an API failure.
        raise RuntimeError(f"JARVIS AI request failed: {exc}") from exc
