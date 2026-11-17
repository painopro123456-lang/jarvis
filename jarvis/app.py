from __future__ import annotations
import sys, webbrowser
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QProgressBar, QTextEdit, QVBoxLayout,
    QWidget, QInputDialog, QTabWidget, QFileDialog, QComboBox
)
from jarvis.assistant import respond
from jarvis.system_monitor import snapshot, recommendations
from jarvis.voice import Voice
from jarvis import actions, ai, security, memory, automation, vision

class Metric(QFrame):
    def __init__(self,title):
        super().__init__()
        self.setObjectName("metric")
        layout=QVBoxLayout(self)
        self.name=QLabel(title.upper()); self.name.setObjectName("muted")
        self.value=QLabel("--"); self.value.setObjectName("metricValue")
        self.bar=QProgressBar(); self.bar.setRange(0,100); self.bar.setTextVisible(False)
        layout.addWidget(self.name); layout.addWidget(self.value); layout.addWidget(self.bar)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS | Personal System Intelligence")
        self.resize(1280,850)
        self.voice=Voice()
        root=QWidget(); root.setObjectName("root"); self.setCentralWidget(root)
        outer=QVBoxLayout(root)
        header=QHBoxLayout()
        brand=QLabel("JARVIS"); brand.setObjectName("brand")
        subtitle=QLabel("PERSONAL SYSTEM INTELLIGENCE"); subtitle.setObjectName("muted")
        self.online=QLabel("● SYSTEM ONLINE"); self.online.setObjectName("online")
        header.addWidget(brand); header.addWidget(subtitle); header.addStretch(); header.addWidget(self.online)
        outer.addLayout(header)
        self.tabs=QTabWidget(); outer.addWidget(self.tabs,1)
        self._build_dashboard()
        self._build_security()
        self._build_automation()
        self._build_memory()
        self._build_settings()
        self.setStyleSheet("""
            QWidget#root { background:#07111f; color:#e6f4ff; font-family:'Segoe UI'; }
            QLabel#brand { color:#69d9ff; font-size:28px; font-weight:800; letter-spacing:5px; }
            QLabel#muted { color:#829ab4; font-size:10px; letter-spacing:2px; }
            QLabel#online { color:#64e8b5; font-size:11px; font-weight:700; }
            QLabel#hero { font-size:22px; font-weight:500; padding:12px 2px; }
            QLabel#metricValue { color:#70dcff; font-size:25px; font-weight:700; }
            QLabel#section { color:#70dcff; font-size:12px; font-weight:700; letter-spacing:2px; }
            QFrame#metric, QFrame#panel { background:#0d1d30; border:1px solid #193650; border-radius:12px; }
            QProgressBar { background:#172c43; border:0; border-radius:4px; height:7px; }
            QProgressBar::chunk { background:#32bde9; border-radius:4px; }
            QTextEdit, QLineEdit, QComboBox { background:#0b1a2b; border:1px solid #1c3c59; border-radius:9px; padding:10px; color:#e6f4ff; }
            QPushButton { background:#123e5b; border:1px solid #246487; border-radius:8px; padding:10px 14px; color:#dff7ff; font-weight:700; }
            QPushButton:hover { background:#176087; }
            QTabWidget::pane { border:1px solid #193650; border-radius:10px; }
            QTabBar::tab { background:#0d1d30; color:#91abc5; padding:12px 20px; margin-right:4px; border-top-left-radius:8px; border-top-right-radius:8px; }
            QTabBar::tab:selected { background:#123e5b; color:#ffffff; }
        """)
        self.timer=QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.timeout.connect(self.update_ai_status); self.timer.start(3000)
        self.refresh(); self.update_ai_status()

    def button(self,label,callback):
        b=QPushButton(label); b.clicked.connect(callback); return b

    def _build_dashboard(self):
        page=QWidget(); layout=QVBoxLayout(page)
        hero=QLabel("Good day. Your system is under observation."); hero.setObjectName("hero"); layout.addWidget(hero)
        metrics=QGridLayout()
        self.cpu=Metric("Processor"); self.ram=Metric("Memory"); self.disk=Metric("System drive"); self.battery=Metric("Battery")
        for i,w in enumerate((self.cpu,self.ram,self.disk,self.battery)): metrics.addWidget(w,0,i)
        layout.addLayout(metrics)
        split=QHBoxLayout()
        self.chat=QTextEdit(); self.chat.setReadOnly(True)
        self.chat.append("JARVIS / Online. Local AI, memory, PC tools, security inspection and optional screen vision are available. No API key is required.")
        split.addWidget(self.chat,3)
        panel=QFrame(); panel.setObjectName("panel"); p=QVBoxLayout(panel)
        title=QLabel("LIVE SYSTEM"); title.setObjectName("section"); p.addWidget(title)
        self.host=QLabel("Detecting device…"); self.host.setWordWrap(True); p.addWidget(self.host)
        p.addWidget(QLabel("TOP MEMORY PROCESSES"))
        self.processes=QLabel("Loading…"); self.processes.setWordWrap(True); p.addWidget(self.processes)
        p.addWidget(QLabel("JARVIS RECOMMENDATIONS"))
        self.tips=QLabel("Checking…"); self.tips.setWordWrap(True); p.addWidget(self.tips)
        p.addStretch(); split.addWidget(panel,2); layout.addLayout(split,1)
        controls=QHBoxLayout()
        self.entry=QLineEdit(); self.entry.setPlaceholderText("Ask JARVIS… e.g. optimize my PC, explain this error, remember my preferences")
        self.entry.returnPressed.connect(self.send)
        controls.addWidget(self.entry,1); controls.addWidget(self.button("SEND",self.send))
        controls.addWidget(self.button("TALK",self.listen)); controls.addWidget(self.button("STOP SPEAKING",self.voice.stop_speaking))
        self.ai_setup=self.button("SET UP LOCAL AI",self.configure_ai); controls.addWidget(self.ai_setup)
        self.admin=self.button("ADMIN MODE",self.enable_admin); controls.addWidget(self.admin)
        layout.addLayout(controls)
        self.tabs.addTab(page,"OVERVIEW")

    def _build_security(self):
        page=QWidget(); layout=QVBoxLayout(page)
        intro=QLabel("SECURITY CENTER  /  Read-only inspection and Microsoft Defender actions"); intro.setObjectName("hero"); layout.addWidget(intro)
        row=QHBoxLayout()
        for label,fn in [
            ("DEFENDER STATUS",actions.defender_status),
            ("FIREWALL STATUS",security.firewall_status),
            ("NETWORK CONNECTIONS",security.network_connections),
            ("REVIEW PROCESS INDICATORS",security.inspect_processes),
            ("START DEFENDER QUICK SCAN",actions.start_defender_quick_scan),
        ]:
            row.addWidget(self.button(label,lambda checked=False,f=fn,l=label:self.run_report(l,f)))
        layout.addLayout(row)
        row2=QHBoxLayout()
        row2.addWidget(self.button("SCAN A FILE",self.scan_file))
        row2.addWidget(self.button("CREATE RESTORE POINT",self.restore_point))
        row2.addWidget(self.button("STARTUP APPS",lambda:self.run_report("Startup apps",actions.startup_report)))
        layout.addLayout(row2)
        self.security_log=QTextEdit(); self.security_log.setReadOnly(True)
        self.security_log.setPlaceholderText("Security inspection results appear here. Review indicators carefully; they are not automatic malware verdicts.")
        layout.addWidget(self.security_log,1)
        note=QLabel("JARVIS never disables Defender or Firewall. Scans are performed by Microsoft Defender. Network/process indicators are leads, not proof of compromise.")
        note.setObjectName("muted"); note.setWordWrap(True); layout.addWidget(note)
        self.tabs.addTab(page,"SECURITY")

    def _build_automation(self):
        page=QWidget(); layout=QVBoxLayout(page)
        intro=QLabel("AUTOMATION  /  Build repeatable routines with explicit review"); intro.setObjectName("hero"); layout.addWidget(intro)
        row=QHBoxLayout()
        row.addWidget(self.button("CREATE ROUTINE",self.create_routine))
        row.addWidget(self.button("REFRESH ROUTINES",self.refresh_routines))
        row.addWidget(self.button("OPEN TASK SCHEDULER",lambda:self.run_report("Task Scheduler",lambda:actions.open_target("taskschd.msc"))))
        layout.addLayout(row)
        self.routines=QTextEdit(); self.routines.setReadOnly(True); layout.addWidget(self.routines,1)
        warning=QLabel("Saved routines are disabled by default. JARVIS will not silently schedule or run actions in the background.")
        warning.setObjectName("muted"); layout.addWidget(warning)
        self.refresh_routines(); self.tabs.addTab(page,"AUTOMATION")

    def _build_memory(self):
        page=QWidget(); layout=QVBoxLayout(page)
        intro=QLabel("PRIVATE MEMORY  /  Stored locally on this Windows PC"); intro.setObjectName("hero"); layout.addWidget(intro)
        row=QHBoxLayout()
        row.addWidget(self.button("REMEMBER A NOTE",self.add_memory))
        row.addWidget(self.button("REFRESH MEMORY",self.refresh_memory))
        row.addWidget(self.button("CLEAR ALL MEMORY",self.clear_memory))
        layout.addLayout(row)
        self.memories=QTextEdit(); self.memories.setReadOnly(True); layout.addWidget(self.memories,1)
        note=QLabel("Memory is saved in your Windows AppData folder. It is not uploaded to a JARVIS cloud service.")
        note.setObjectName("muted"); layout.addWidget(note)
        self.refresh_memory(); self.tabs.addTab(page,"MEMORY")

    def _build_settings(self):
        page=QWidget(); layout=QVBoxLayout(page)
        intro=QLabel("VOICE, VISION & PREFERENCES"); intro.setObjectName("hero"); layout.addWidget(intro)
        row=QHBoxLayout()
        self.voice_style=QComboBox(); self.voice_style.addItems(["calm","standard","energetic"])
        row.addWidget(QLabel("Voice style")); row.addWidget(self.voice_style)
        row.addWidget(self.button("ENABLE WAKE WORD",self.enable_wake_word))
        row.addWidget(self.button("DISABLE WAKE WORD",self.disable_wake_word))
        layout.addLayout(row)
        vision_row=QHBoxLayout()
        vision_row.addWidget(self.button("ENABLE SCREEN VISION",self.enable_vision))
        vision_row.addWidget(self.button("CAPTURE & ANALYZE SCREEN",self.analyze_screen))
        layout.addLayout(vision_row)
        layout.addWidget(QLabel("Wake-word recognition uses Google's online speech recognition service when enabled. Screen vision uses a separate optional local model download; screenshots stay on this PC."))
        self.settings_log=QTextEdit(); self.settings_log.setReadOnly(True); layout.addWidget(self.settings_log,1)
        self.tabs.addTab(page,"SETTINGS")

    def log(self,area,title,result):
        area.append(f"{title}\n{result}\n")
    def confirm(self,prompt):
        return QMessageBox.question(self,"JARVIS confirmation",prompt,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes
    def run_report(self,title,fn):
        try: result=fn()
        except Exception as exc: result=f"Could not complete: {exc}"
        self.log(self.security_log,title,result)
    def update_ai_status(self):
        if hasattr(self,"ai_setup"): self.ai_setup.setText("LOCAL AI READY" if ai.is_ready() else "SET UP LOCAL AI")
    def configure_ai(self):
        if not ai.ollama_installed():
            QMessageBox.information(self,"Install local AI","JARVIS needs the free Ollama runtime. No API key is required.")
            webbrowser.open("https://ollama.com/download/windows"); return
        try: QMessageBox.information(self,"JARVIS local AI",ai.start_model_download())
        except Exception as exc: QMessageBox.warning(self,"Local AI setup",str(exc))
    def enable_admin(self):
        if actions.is_admin(): QMessageBox.information(self,"Administrator mode","JARVIS already has administrator permissions."); return
        if self.confirm("Windows will display a User Account Control prompt. Continue?"):
            try: self.chat.append("JARVIS / "+actions.relaunch_as_admin()); QApplication.quit()
            except Exception as exc: QMessageBox.warning(self,"Administrator mode",str(exc))
    def refresh(self):
        try:
            d=snapshot()
            for widget,key in ((self.cpu,"cpu"),(self.ram,"memory_percent"),(self.disk,"disk_percent")):
                widget.value.setText(f"{d[key]:.0f}%"); widget.bar.setValue(round(d[key]))
            if d["battery"] is None: self.battery.value.setText("N/A"); self.battery.bar.setValue(0)
            else: self.battery.value.setText(f"{d['battery']:.0f}%"); self.battery.bar.setValue(round(d["battery"]))
            self.host.setText(f"{d['host']}\n{d['os']}\nRAM: {d['memory_used_gb']:.1f}/{d['memory_total_gb']:.1f} GB\nFree drive: {d['disk_free_gb']:.1f} GB")
            self.processes.setText("\n".join(f"{p['name']} · {p['memory_mb']:.0f} MB" for p in d["processes"]))
            self.tips.setText("\n".join("• "+x for x in recommendations(d)))
            self.admin.setText("ADMIN ACTIVE" if actions.is_admin() else "ADMIN MODE")
        except Exception as exc: self.online.setText("● MONITOR LIMITED"); self.host.setText(str(exc))
    def send(self):
        message=self.entry.text().strip()
        if not message: return
        self.entry.clear(); self.chat.append(f"YOU / {message}")
        try: answer=respond(message,confirm=self.confirm)
        except Exception as exc: answer=f"I couldn't complete that action: {exc}"
        self.chat.append(f"JARVIS / {answer}\n"); self.voice.speak(answer,self.voice_style.currentText())
    def listen(self):
        self.chat.append("JARVIS / Listening…"); QApplication.processEvents()
        try: self.entry.setText(self.voice.listen_once()); self.send()
        except Exception as exc: QMessageBox.information(self,"Voice input",str(exc))
    def scan_file(self):
        path,_=QFileDialog.getOpenFileName(self,"Choose a file to scan")
        if path and self.confirm(f"Ask Microsoft Defender to scan this file?\n{path}"):
            self.run_report("Defender custom scan",lambda:security.scan_file(path))
    def restore_point(self):
        if self.confirm("Create a Windows restore point? This requires administrator mode and may take a minute."):
            self.run_report("Restore point",security.create_restore_point)
    def create_routine(self):
        name,ok=QInputDialog.getText(self,"New routine","Routine name:")
        if not ok or not name.strip(): return
        instruction,ok=QInputDialog.getMultiLineText(self,"Routine steps","Describe what the routine should do:")
        if ok and instruction.strip():
            self.log(self.routines,"Saved",automation.add_routine(name,instruction)); self.refresh_routines()
    def refresh_routines(self): self.routines.setPlainText(automation.report())
    def add_memory(self):
        note,ok=QInputDialog.getMultiLineText(self,"Remember a note","What should JARVIS remember on this PC?")
        if ok and note.strip(): self.log(self.memories,"Memory",memory.remember(note)); self.refresh_memory()
    def refresh_memory(self): self.memories.setPlainText(memory.summary())
    def clear_memory(self):
        if self.confirm("Clear every saved JARVIS note and preference on this PC?"):
            self.memories.setPlainText(memory.clear())
    def enable_wake_word(self):
        try:
            result=self.voice.start_wake_word(lambda phrase:self._wake_command(phrase))
            self.settings_log.append(result)
        except Exception as exc: QMessageBox.warning(self,"Wake word",str(exc))
    def _wake_command(self,phrase):
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0,lambda:(self.entry.setText(phrase),self.send()))
    def disable_wake_word(self): self.settings_log.append(self.voice.stop_wake_word())
    def enable_vision(self):
        if not ai.ollama_installed():
            QMessageBox.information(self,"Ollama required","Install Ollama first from https://ollama.com/download/windows."); webbrowser.open("https://ollama.com/download/windows"); return
        if self.confirm("Download the optional screen-vision model? It is a separate, potentially large download."):
            self.settings_log.append(ai.start_vision_download())
    def analyze_screen(self):
        try:
            path=vision.capture_screen()
            if not ai.vision_model_installed():
                self.settings_log.append(f"Screenshot saved locally: {path}\nEnable the optional screen-vision model to analyze it.")
                return
            if self.confirm("Capture the current screen and send it to the local vision model for analysis?"):
                result=ai.analyze_image(str(path))
                self.settings_log.append(f"Screen analysis ({path.name}):\n{result}")
        except Exception as exc: QMessageBox.warning(self,"Screen vision",str(exc))
    def closeEvent(self,event):
        self.voice.stop_wake_word(); self.voice.stop_speaking(); super().closeEvent(event)

def main():
    app=QApplication(sys.argv); app.setFont(QFont("Segoe UI",10))
    window=MainWindow(); window.show(); sys.exit(app.exec())

if __name__=="__main__": main()
