"""Small intent router. Unknown requests are never executed as commands."""
from __future__ import annotations

from jarvis import actions, system_monitor


def respond(message: str) -> str:
    text = message.strip()
    lower = text.lower()
    if not text:
        return "Tell me what you need."
    if any(word in lower for word in ("status", "health", "how is my pc", "pc report", "system info")):
        data = system_monitor.snapshot()
        battery = "not available" if data["battery"] is None else f"{data['battery']:.0f}%"
        tips = " ".join(system_monitor.recommendations(data))
        return (f"Your PC is {data['os']}. CPU is at {data['cpu']:.0f} percent, "
                f"memory at {data['memory_percent']:.0f} percent, and drive usage at "
                f"{data['disk_percent']:.0f} percent. Battery: {battery}. {tips}")
    if "defender" in lower or "virus scan" in lower or "malware scan" in lower or "security scan" in lower:
        return actions.start_defender_quick_scan()
    for prefix in ("open ", "launch ", "start "):
        if lower.startswith(prefix):
            return actions.open_target(text[len(prefix):])
    if lower in {"help", "what can you do", "commands"}:
        return ("I can report PC health, start a Microsoft Defender quick scan, and open "
                "Notepad, Calculator, Paint, Task Manager, File Explorer, Settings, "
                "your Downloads/Documents/Desktop folders, or your browser.")
    return ("I don't have a safe action for that yet. Try 'PC status', 'open Notepad', "
            "or 'start Defender scan'. I won't run arbitrary terminal commands.")
