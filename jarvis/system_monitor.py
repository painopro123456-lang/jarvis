"""Read-only Windows system telemetry."""
from __future__ import annotations

import platform
import shutil
import socket
import psutil


def snapshot() -> dict:
    vm = psutil.virtual_memory()
    disk = shutil.disk_usage("C:\\") if platform.system() == "Windows" else shutil.disk_usage("/")
    battery = psutil.sensors_battery()
    try:
        host = socket.gethostname()
    except OSError:
        host = "Windows PC"
    return {
        "host": host,
        "os": f"{platform.system()} {platform.release()}",
        "cpu": psutil.cpu_percent(interval=0.25),
        "memory_percent": vm.percent,
        "memory_used_gb": vm.used / (1024 ** 3),
        "memory_total_gb": vm.total / (1024 ** 3),
        "disk_percent": disk.used / disk.total * 100,
        "disk_free_gb": disk.free / (1024 ** 3),
        "battery": None if battery is None else battery.percent,
        "processes": sorted(
            ({"name": p.info.get("name") or "Unknown",
              "pid": p.info["pid"],
              "memory_mb": (p.info.get("memory_info").rss / (1024 ** 2))
                  if p.info.get("memory_info") else 0}
             for p in psutil.process_iter(["name", "memory_info"])),
            key=lambda p: p["memory_mb"], reverse=True
        )[:8],
    }


def recommendations(data: dict) -> list[str]:
    tips = []
    if data["cpu"] >= 85:
        tips.append("CPU load is high. Check the top processes before closing anything.")
    if data["memory_percent"] >= 85:
        tips.append("Memory pressure is high. Save your work and review memory-heavy apps.")
    if data["disk_percent"] >= 90:
        tips.append("The system drive is nearly full. Review temporary files manually.")
    if not tips:
        tips.append("No critical resource pressure detected in this snapshot.")
    return tips
