# JARVIS for Windows

A local-first Windows desktop assistant being migrated toward a lightweight Rust system core, with conversational local AI, voice controls, PC telemetry, memory, security inspection, troubleshooting and guarded automation.

## No API key required

JARVIS uses [Ollama](https://ollama.com) to run its language model locally. There is no OpenAI API key, cloud subscription or per-message fee. Install Ollama from [ollama.com/download/windows](https://ollama.com/download/windows), open JARVIS and choose **SET UP LOCAL AI**. The model is a one-time download; after setup, ordinary AI conversations run on the PC. Model speed and reasoning quality depend on available CPU, RAM and GPU.

## Features

### Intelligence
- Independent-minded assistant personality: can challenge assumptions, explain reasoning, admit mistakes and revise its view when given better evidence.
- Multi-step tool use with step-by-step result inspection, bounded retries and explicit success/failure reporting.
- A local action history view in the Security Center; only minimal action metadata is recorded.
- A bounded coding workspace: create projects, inspect project structure and manifests, search source files for symbols/errors/TODOs, read/write source files, run a read-only Python static security audit, and run allow-listed Python, Rust, Node.js and .NET checks/builds. Search and audit are read-only and bounded; file edits and project commands require confirmation; results must be inspected and verified.
- Private local memory for notes and preferences, with view and clear controls.
- Proactive system recommendations and a one-click daily PC briefing.

### PC operator
- Rust native-core foundation, compiled as a small Windows sidecar and bundled into the JARVIS executable. The current desktop interface is still Python/PySide6 during the staged migration; it is not yet a fully Rust application.
- Read-only driver audit: lists installed Plug-and-Play driver records and asks Windows Update which driver updates it currently offers. It never installs drivers. This is not a complete comparison against every manufacturer's newest release.
- Live CPU, RAM, disk, battery and top-process monitoring.
- Process and startup-app inspection.
- Open common Windows apps, folders and existing paths.
- Change supported power plans after confirmation.
- Find files and detect duplicates in Desktop, Documents and Downloads. Duplicate detection is read-only; it never deletes files.
- Discover software from a plain-language description by searching the Windows Package Manager catalogue; JARVIS presents candidates for the user to compare and choose before any installation.
- Install/update a specifically chosen application through Windows Package Manager (winget), after confirmation.
- Read-only diagnostics including recent critical/error System events.
- Create a Windows restore point before a major change (requires administrator mode and confirmation).

### Security center
- Read Microsoft Defender and Windows Firewall status.
- Inspect visible network connections, process indicators and startup entries.
- Read Defender's real-time protection, behavior monitoring, network inspection, tamper-protection and signature freshness status where Windows exposes them.
- Read recent Microsoft Defender detection history without changing quarantine.
- Ask Microsoft Defender to scan a selected file or run a quick scan.
- Inspect a selected file's SHA-256 and Authenticode signer/status locally; files are not executed or uploaded by this check.
- JARVIS does not disable Defender or Windows Firewall and does not claim to replace antivirus. Process/network indicators and signature results are evidence to review, not proof that a file or PC is clean. Defender handles its own quarantine workflow. These checks are defensive visibility features, not a guarantee against advanced malware.

### Coding workspace
- Default workspace: `Documents/JARVIS-Workspace` (override with `JARVIS_WORKSPACE`).
- JARVIS can create project folders, inspect project files/manifests, read UTF-8 source files, and create or replace source files inside that workspace only.
- It can run a fixed set of Python, Cargo, npm and .NET test/build commands from the selected project directory. Running project commands requires confirmation because build scripts execute code.
- It does not yet edit arbitrary folders, directly operate a GitHub repository, or run unrestricted terminal commands. Copy a project into the workspace before asking JARVIS to work on it.

### Browser access roadmap
- Browser automation is planned as a permissioned feature. The current build can open the default browser, but does not yet have full tab/page interaction. Future browser actions will use a visible, user-controlled browser session and ask before submitting forms, downloading files, sending messages or purchasing anything.

### Voice and vision
- Windows text-to-speech with calm, standard and energetic rate presets; stop-speaking control.
- Optional microphone input and wake word. Wake-word recognition uses Google's online speech-recognition service when enabled; it is not an always-on offline recognizer.
- Optional screen capture and local vision analysis using a separate Ollama vision model. The vision model is a separate, potentially large download and is never downloaded without confirmation. A screenshot is analyzed only after the user requests it and confirms.

### Automation
- Save named routines for later review. New routines are disabled by default.
- No silent background task execution or unrestricted shell access. Windows Task Scheduler can be opened by the user for advanced scheduling.

## Development roadmap

The current repository is a staged build, not yet a finished unrestricted PC agent. Implemented foundations include local conversational AI, allow-listed PC tools, local screen analysis (optional model), read-only security inspection, driver inventory/Windows Update discovery, description-based software catalogue search, explicit confirmation for consequential AI tool actions, and a privacy-minimal local action history. Remaining planned work includes a permissioned browser companion/extension for real page interaction, deeper hardware/vendor driver comparison, a verified optimization planner with before/after measurements, more robust rollback for supported settings, richer speech turn-taking, and an end-to-end integration test suite. The Rust core is currently a small sidecar; the GUI and most orchestration remain Python/PySide6.

## Safety boundaries
JARVIS starts without administrator privileges. Risky actions require a confirmation dialog. No software can guarantee that an AI will never make a mistake; JARVIS is being designed around narrow permissions, previews, explicit approvals, verification and recovery rather than blind trust. Its AI can call only explicitly allow-listed functions; model output is never passed directly to arbitrary CMD or PowerShell. User files are not silently deleted. JARVIS is a companion to Windows Security, not a replacement for antivirus software.

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

### Third-party antivirus and Download Guard

The Security Center can list antivirus products registered with Windows Security Center and watches the current user's Downloads folder for newly arriving executable, installer, script, shortcut, disk-image and Java archive file types. New arrivals trigger an on-screen warning. This is an alerting companion only: it does not intercept browser traffic, block process execution, scan or quarantine files, and it cannot prove an antivirus engine is active. Real-time prevention and quarantine must be provided by a reputable installed third-party endpoint product with its own tamper protection enabled. JARVIS never claims that a file is safe merely because it is signed or that no alert means the system is clean.
