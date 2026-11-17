"""Intent router for JARVIS. Unknown text is never executed as a shell command."""
from __future__ import annotations


from jarvis import actions, system_monitor


def respond(message: str, confirm=None) -> str:
    text = message.strip()
    lower = text.lower()
    if not text:
        return "Tell me what you need."
    if any(w in lower for w in ("status", "health", "how is my pc", "pc report", "system info")):
        data = system_monitor.snapshot()
        battery = "not available" if data["battery"] is None else f"{data['battery']:.0f}%"
        return (f"Your PC is {data['os']}. CPU {data['cpu']:.0f}%, RAM "
                f"{data['memory_percent']:.0f}%, drive {data['disk_percent']:.0f}%. "
                f"Battery: {battery}. " + " ".join(system_monitor.recommendations(data)))
    if "administrator" in lower or "admin mode" in lower or "admin status" in lower:
        return "JARVIS is running as administrator." if actions.is_admin() else "JARVIS is running with normal user permissions. Use the ADMIN MODE button to request Windows UAC elevation."
    if any(w in lower for w in ("defender status", "antivirus status", "protection status")):
        return actions.defender_status()
    if "defender" in lower or "virus scan" in lower or "malware scan" in lower or "security scan" in lower:
        if confirm and not confirm("Start a Microsoft Defender quick scan?"):
            return "Scan cancelled."
        return actions.start_defender_quick_scan()
    if "startup" in lower and any(w in lower for w in ("list", "show", "what", "apps", "programs")):
        return actions.startup_report()
    if any(w in lower for w in ("processes", "running apps", "task list", "ram usage")):
        return actions.process_report()
    if lower.startswith(("close process ", "end process ", "kill process ")):
        pid = text.rsplit(" ", 1)[-1]
        if confirm and not confirm(f"Terminate process PID {pid}? Unsaved work in that app may be lost."):
            return "Process termination cancelled."
        return actions.terminate_process(pid)
    for phrase, plan in (("ultimate performance", "ultimate performance"),
                         ("high performance", "high performance"),
                         ("balanced power", "balanced")):
        if phrase in lower:
            if confirm and not confirm(f"Change Windows power plan to {plan}?"):
                return "Power plan change cancelled."
            return actions.set_power_plan(plan)
    if "cancel shutdown" in lower or "abort restart" in lower:
        return actions.cancel_power_action()
    if "restart" in lower or "shut down" in lower or "shutdown" in lower:
        kind = "restart" if "restart" in lower else "shutdown"
        if confirm and not confirm(f"Schedule Windows {kind} in 60 seconds?"):
            return f"{kind.title()} cancelled."
        return actions.schedule_power_action(kind)
    if "lock pc" in lower or "lock computer" in lower or lower == "lock windows":
        if confirm and not confirm("Lock this Windows PC now?"):
            return "Lock cancelled."
        return actions.lock_pc()
    if lower.startswith("open "):
        return actions.open_target(text[5:])
    if lower.startswith("find file "):
        term = text[10:].strip().lower()
        if not term:
            return "Tell me the file name to find."
        matches = []
        for root in (Path.home() / "Desktop", Path.home() / "Documents", Path.home() / "Downloads"):
            if root.exists():
                try:
                    for p in root.rglob("*"):
                        if term in p.name.lower():
                            matches.append(str(p))
                            if len(matches) >= 20:
                                break
                except (PermissionError, OSError):
                    pass
        return "Found files:\n" + "\n".join(matches) if matches else "No matching files found in Desktop, Documents, or Downloads."
    if lower in {"help", "what can you do", "commands"}:
        return ("Try: PC status; open Notepad; open C:\\path\\to\\file; list processes; "
                "show startup apps; Defender status; start Defender scan; high performance; "
                "close process 1234; restart PC; lock PC; find file report.pdf. "
                "Risky actions ask before proceeding.")
    return ("I don't have a mapped action for that request yet. I will not interpret arbitrary text "
            "as terminal commands. Type 'help' to see supported PC controls.")
from pathlib import Path
