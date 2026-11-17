"""Natural-language AI router with a safe offline/basic-command fallback."""
from __future__ import annotations

from pathlib import Path

from jarvis import actions, system_monitor, ai, security, memory, automation


def respond(message: str, confirm=None) -> str:
    # When configured, the AI brain handles both conversation and multi-step
    # tool selection. Without a key, retain the original local command router.
    if ai.is_ready():
        return ai.respond(message, confirm=confirm)

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
        if not confirm or not confirm("Start a Microsoft Defender quick scan?"):
            return "Scan cancelled."
        return actions.start_defender_quick_scan()
    if "startup" in lower and any(w in lower for w in ("list", "show", "what", "apps", "programs")):
        return actions.startup_report()
    if any(w in lower for w in ("processes", "running apps", "task list", "ram usage")):
        return actions.process_report()
    if "firewall" in lower:
        return security.firewall_status()
    if "network connections" in lower or "active connections" in lower:
        return security.network_connections()
    if "suspicious process" in lower or "process security" in lower:
        return security.inspect_processes()
    if lower.startswith("scan file "):
        path = text[10:].strip()
        if not confirm or not confirm(f"Ask Microsoft Defender to scan {path}?"):
            return "File scan cancelled."
        return security.scan_file(path)
    if "restore point" in lower:
        if not confirm or not confirm("Create a Windows restore point? Administrator mode is required."):
            return "Restore point cancelled."
        return security.create_restore_point()
    if lower.startswith("remember "):
        return memory.remember(text[9:].strip())
    if "what do you remember" in lower or lower == "show memory":
        return memory.summary()
    if "clear memory" in lower:
        if not confirm or not confirm("Clear all locally saved JARVIS memories?"):
            return "Memory clear cancelled."
        return memory.clear()
    if lower.startswith("create routine "):
        return automation.add_routine("Custom routine", text[15:].strip())
    if "list routines" in lower or "show routines" in lower:
        return automation.report()
    if lower.startswith(("close process ", "end process ", "kill process ")):
        pid = text.rsplit(" ", 1)[-1]
        if not confirm or not confirm(f"Terminate process PID {pid}? Unsaved work in that app may be lost."):
            return "Process termination cancelled."
        return actions.terminate_process(pid)
    for phrase, plan in (("ultimate performance", "ultimate performance"),
                         ("high performance", "high performance"),
                         ("balanced power", "balanced")):
        if phrase in lower:
            if not confirm or not confirm(f"Change Windows power plan to {plan}?"):
                return "Power plan change cancelled."
            return actions.set_power_plan(plan)
    if "cancel shutdown" in lower or "abort restart" in lower:
        return actions.cancel_power_action()
    if "restart" in lower or "shut down" in lower or "shutdown" in lower:
        kind = "restart" if "restart" in lower else "shutdown"
        if not confirm or not confirm(f"Schedule Windows {kind} in 60 seconds?"):
            return f"{kind.title()} cancelled."
        return actions.schedule_power_action(kind)
    if "lock pc" in lower or "lock computer" in lower or lower == "lock windows":
        if not confirm or not confirm("Lock this Windows PC now?"):
            return "Lock cancelled."
        return actions.lock_pc()
    if lower.startswith("open "):
        return actions.open_target(text[5:], confirm=confirm)
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
        return ("Try: PC status; open Notepad; open C:\\\\path\\\\to\\\\file; list processes; "
                "show startup apps; Defender status; firewall status; active network connections; scan file C:\\\\path\\\\file.exe; remember I prefer dark mode; show memory; list routines; high performance; "
                "close process 1234; restart PC; lock PC; find file report.pdf. "
                "Install Ollama and select SET UP LOCAL AI to enable natural conversation and tool planning.")
    return ("Local AI is not ready yet. Select SET UP LOCAL AI to install or download the local model. "
            "Basic commands still work while setup completes.")
