# JARVIS for Windows

A local-first Windows desktop assistant with a conversational local AI, voice controls, PC telemetry, memory, security inspection, troubleshooting and guarded automation.

## No API key required

JARVIS uses [Ollama](https://ollama.com) to run its language model locally. There is no OpenAI API key, cloud subscription or per-message fee. Install Ollama from [ollama.com/download/windows](https://ollama.com/download/windows), open JARVIS and choose **SET UP LOCAL AI**. The model is a one-time download; after setup, ordinary AI conversations run on the PC. Model speed and reasoning quality depend on available CPU, RAM and GPU.

## Features

### Intelligence
- Independent-minded assistant personality: can challenge assumptions, explain reasoning, admit mistakes and revise its view when given better evidence.
- Multi-step planning and allow-listed local PC tool calling.
- Private local memory for notes and preferences, with view and clear controls.
- Proactive system recommendations and a one-click daily PC briefing.

### PC operator
- Live CPU, RAM, disk, battery and top-process monitoring.
- Process and startup-app inspection.
- Open common Windows apps, folders and existing paths.
- Change supported power plans after confirmation.
- Find files and detect duplicates in Desktop, Documents and Downloads. Duplicate detection is read-only; it never deletes files.
- Install/update only a small approved list of applications through Windows Package Manager (winget), after confirmation.
- Read-only diagnostics including recent critical/error System events.
- Create a Windows restore point before a major change (requires administrator mode and confirmation).

### Security center
- Read Microsoft Defender and Windows Firewall status.
- Inspect visible network connections, process indicators and startup entries.
- Ask Microsoft Defender to scan a selected file or run a quick scan.
- JARVIS does not disable Defender or Windows Firewall. Process and network indicators are review leads, not proof of malware. Defender handles its own quarantine workflow.

### Voice and vision
- Windows text-to-speech with calm, standard and energetic rate presets; stop-speaking control.
- Optional microphone input and wake word. Wake-word recognition uses Google's online speech-recognition service when enabled; it is not an always-on offline recognizer.
- Optional screen capture and local vision analysis using a separate Ollama vision model. The vision model is a separate, potentially large download and is never downloaded without confirmation. A screenshot is analyzed only after the user requests it and confirms.

### Automation
- Save named routines for later review. New routines are disabled by default.
- No silent background task execution or unrestricted shell access. Windows Task Scheduler can be opened by the user for advanced scheduling.

## Safety boundaries
JARVIS starts without administrator privileges. Risky actions require a confirmation dialog. Its AI can call only explicitly allow-listed functions; model output is never passed directly to arbitrary CMD or PowerShell. User files are not silently deleted. JARVIS is a companion to Windows Security, not a replacement for antivirus software.

## Run from source
1. Install Python 3.11 on Windows.
2. `py -m venv .venv`
3. `.venv\\Scripts\\activate`
4. `pip install -r requirements.txt`
5. `py -m jarvis`

Optional microphone dependencies: `pip install -r requirements-voice.txt`.

## Download the Windows app
The GitHub Actions workflow builds a **single standalone `JARVIS.exe`** and publishes it as a direct GitHub Release asset. No ZIP download is required:

[Download JARVIS.exe](https://github.com/painopro123456-lang/jarvis/releases/latest/download/JARVIS.exe)

This is a portable executable, not an installer. Windows may show SmartScreen because the build is not code-signed.