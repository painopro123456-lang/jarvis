"""Opt-in screenshot capture. Images remain local unless the user asks the local vision model to inspect them."""
from __future__ import annotations
import os
from pathlib import Path

def capture_screen() -> Path:
    try:
        from PySide6.QtWidgets import QApplication
        screen=QApplication.primaryScreen()
        if screen is None: raise RuntimeError("No screen is available.")
        root=Path(os.getenv("APPDATA",str(Path.home())))/"JARVIS"/"screenshots"
        root.mkdir(parents=True,exist_ok=True)
        path=root/"latest-screen.png"
        if not screen.grabWindow(0).save(str(path),"PNG"):
            raise RuntimeError("Windows could not save the screenshot.")
        return path
    except ImportError as exc:
        raise RuntimeError("Screen capture requires the JARVIS desktop interface.") from exc
