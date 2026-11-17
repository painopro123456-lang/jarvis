from __future__ import annotations

import sys
import webbrowser
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QProgressBar, QTextEdit, QVBoxLayout, QWidget, QInputDialog
)
from jarvis.assistant import respond
from jarvis.system_monitor import snapshot
from jarvis.voice import Voice
from jarvis import actions, ai


class Metric(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("metric")
        layout = QVBoxLayout(self)
        self.name = QLabel(title.upper())
        self.name.setObjectName("muted")
        self.value = QLabel("--")
        self.value.setObjectName("metricValue")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        layout.addWidget(self.name)
        layout.addWidget(self.value)
        layout.addWidget(self.bar)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS | Windows Intelligence")
        self.resize(1120, 760)
        self.voice = Voice()
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        header = QHBoxLayout()
        brand = QLabel("JARVIS")
        brand.setObjectName("brand")
        subtitle = QLabel("PERSONAL SYSTEM INTELLIGENCE")
        subtitle.setObjectName("muted")
        header.addWidget(brand)
        header.addWidget(subtitle)
        header.addStretch()
        self.online = QLabel("● SYSTEM ONLINE")
        self.online.setObjectName("online")
        header.addWidget(self.online)
        outer.addLayout(header)

        hero = QLabel("Good day. Your system is under observation.")
        hero.setObjectName("hero")
        outer.addWidget(hero)

        metrics = QGridLayout()
        self.cpu = Metric("Processor")
        self.ram = Metric("Memory")
        self.disk = Metric("System drive")
        self.battery = Metric("Battery")
        for i, widget in enumerate((self.cpu, self.ram, self.disk, self.battery)):
            metrics.addWidget(widget, 0, i)
        outer.addLayout(metrics)

        mid = QHBoxLayout()
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setPlaceholderText("Your JARVIS conversation will appear here.")
        self.chat.append("JARVIS  /  Online. Set up LOCAL AI for natural conversation, independent reasoning and multi-step PC tasks. No API key or cloud account required.")
        self.chat.setMinimumHeight(300)
        mid.addWidget(self.chat, 3)
        side = QFrame()
        side.setObjectName("panel")
        side_layout = QVBoxLayout(side)
        title = QLabel("SYSTEM OVERVIEW")
        title.setObjectName("section")
        side_layout.addWidget(title)
        self.host = QLabel("Detecting device…")
        self.host.setWordWrap(True)
        side_layout.addWidget(self.host)
        side_layout.addWidget(QLabel("TOP MEMORY PROCESSES"))
        self.processes = QLabel("Loading…")
        self.processes.setWordWrap(True)
        side_layout.addWidget(self.processes)
        side_layout.addStretch()
        mid.addWidget(side, 2)
        outer.addLayout(mid)

        controls = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Ask JARVIS… e.g. 'PC status', 'list processes', 'open Calculator'")
        self.entry.returnPressed.connect(self.send)
        send = QPushButton("SEND")
        send.clicked.connect(self.send)
        mic = QPushButton("🎙  TALK")
        mic.clicked.connect(self.listen)
        self.admin = QPushButton("ADMIN MODE")
        self.admin.clicked.connect(self.enable_admin)
        self.ai_setup = QPushButton("AI SETUP")
        self.ai_setup.clicked.connect(self.configure_ai)
        controls.addWidget(self.entry, 1)
        controls.addWidget(mic)
        controls.addWidget(self.ai_setup)
        controls.addWidget(self.admin)
        controls.addWidget(send)
        outer.addLayout(controls)

        foot = QLabel("LOCAL AI  •  LOCAL PC CONTROL  •  UAC ELEVATION  •  CONFIRMATIONS FOR RISKY ACTIONS")
        foot.setObjectName("muted")
        outer.addWidget(foot)

        self.setStyleSheet("""
            QWidget#root { background:#07111f; color:#e6f4ff; font-family:'Segoe UI'; }
            QLabel#brand { color:#69d9ff; font-size:28px; font-weight:800; letter-spacing:5px; }
            QLabel#muted { color:#718ba7; font-size:10px; letter-spacing:2px; }
            QLabel#online { color:#64e8b5; font-size:11px; font-weight:700; }
            QLabel#hero { font-size:22px; font-weight:500; padding:18px 2px; }
            QFrame#metric, QFrame#panel { background:#0d1d30; border:1px solid #193650; border-radius:12px; }
            QLabel#metricValue { color:#70dcff; font-size:25px; font-weight:700; }
            QLabel#section { color:#70dcff; font-size:12px; font-weight:700; letter-spacing:2px; }
            QProgressBar { background:#172c43; border:0; border-radius:4px; height:7px; }
            QProgressBar::chunk { background:#32bde9; border-radius:4px; }
            QTextEdit, QLineEdit { background:#0b1a2b; border:1px solid #1c3c59; border-radius:9px; padding:12px; color:#e6f4ff; }
            QPushButton { background:#123e5b; border:1px solid #246487; border-radius:8px; padding:11px 18px; color:#dff7ff; font-weight:700; }
            QPushButton:hover { background:#176087; }
        """)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.timeout.connect(self.update_ai_status)
        self.timer.start(2500)
        self.refresh()
        self.update_admin_status()
        self.update_ai_status()

    def update_ai_status(self):
        self.ai_setup.setText("LOCAL AI READY" if ai.is_ready() else "SET UP LOCAL AI")

    def configure_ai(self):
        if not ai.ollama_installed():
            QMessageBox.information(
                self, "Install local AI",
                "JARVIS does not need an API key. First install the free Ollama local runtime. "
                "After installation, reopen JARVIS and click SET UP LOCAL AI to download its model."
            )
            webbrowser.open("https://ollama.com/download/windows")
            return
        try:
            status = ai.start_model_download()
            self.update_ai_status()
            QMessageBox.information(self, "JARVIS local AI", status)
        except Exception as exc:
            QMessageBox.warning(self, "Local AI setup", str(exc))

    def confirm(self, prompt: str) -> bool:
        return QMessageBox.question(self, "JARVIS confirmation", prompt,
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No) == QMessageBox.Yes

    def enable_admin(self):
        if actions.is_admin():
            QMessageBox.information(self, "Administrator mode", "JARVIS already has administrator permissions.")
            return
        if not self.confirm("Windows will display a User Account Control prompt. Continue?"):
            return
        try:
            message = actions.relaunch_as_admin()
            self.chat.append("JARVIS  /  " + message)
            QApplication.quit()
        except Exception as exc:
            QMessageBox.warning(self, "Administrator mode", str(exc))

    def update_admin_status(self):
        self.admin.setText("ADMIN ACTIVE" if actions.is_admin() else "ADMIN MODE")

    def refresh(self):
        try:
            data = snapshot()
            self.cpu.value.setText(f"{data['cpu']:.0f}%")
            self.cpu.bar.setValue(round(data["cpu"]))
            self.ram.value.setText(f"{data['memory_percent']:.0f}%")
            self.ram.bar.setValue(round(data["memory_percent"]))
            self.disk.value.setText(f"{data['disk_percent']:.0f}%")
            self.disk.bar.setValue(round(data["disk_percent"]))
            if data["battery"] is None:
                self.battery.value.setText("N/A")
                self.battery.bar.setValue(0)
            else:
                self.battery.value.setText(f"{data['battery']:.0f}%")
                self.battery.bar.setValue(round(data["battery"]))
            self.host.setText(f"{data['host']}\n{data['os']}\nFree on system drive: {data['disk_free_gb']:.1f} GB")
            self.processes.setText("\n".join(
                f"{p['name']}  ·  {p['memory_mb']:.0f} MB" for p in data["processes"]
            ) or "No process data")
            self.update_admin_status()
        except Exception as exc:
            self.online.setText("● MONITOR LIMITED")
            self.host.setText(str(exc))

    def send(self):
        message = self.entry.text().strip()
        if not message:
            return
        self.entry.clear()
        self.chat.append(f"YOU  /  {message}")
        try:
            answer = respond(message, confirm=self.confirm)
        except Exception as exc:
            answer = f"I couldn't complete that action: {exc}"
        self.chat.append(f"JARVIS  /  {answer}\n")
        self.voice.speak(answer)

    def listen(self):
        self.chat.append("JARVIS  /  Listening…")
        QApplication.processEvents()
        try:
            phrase = self.voice.listen_once()
            self.entry.setText(phrase)
            self.send()
        except Exception as exc:
            QMessageBox.information(self, "Voice input", str(exc))


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
