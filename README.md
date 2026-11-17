# JARVIS for Windows

A local-first Windows desktop assistant foundation with a voice-ready interface, live PC telemetry, safe system actions, and Microsoft Defender integration.

## What is in this first build
- Windows desktop dashboard with CPU, memory, disk, battery and process information.
- Text commands for opening applications and folders, reading system status, and starting Microsoft Defender scans.
- Text-to-speech responses (Windows voice through `pyttsx3`).
- Optional microphone input through SpeechRecognition + PyAudio (install the optional audio dependency separately if your PC supports it).
- Safety gates: destructive/system-wide changes are not executed silently. Defender is never disabled.
- PyInstaller packaging and GitHub Actions Windows EXE build.

## Run from source
1. Install Python 3.11 on Windows.
2. `py -m venv .venv`
3. `.venv\\Scripts\\activate`
4. `pip install -r requirements.txt`
5. `py -m jarvis`

Optional microphone support: `pip install -r requirements-voice.txt`. Speech recognition currently uses the configured SpeechRecognition engine and therefore needs an internet connection for Google recognition. The app remains fully usable by typing if voice input is unavailable.

## Build
Run `build.bat`, or use the **Build Windows EXE** workflow in GitHub Actions. The artifact is a portable `JARVIS.exe` (not an installer yet).

## Safety
JARVIS starts without administrator privileges. Operations requiring elevation should use Windows UAC and explicit user approval. Do not grant it unrestricted unattended administrator access. Review any command before confirming it.


## Expanded Windows PC controls
- **ADMIN MODE** button requests elevation through the standard Windows UAC prompt. JARVIS does not silently self-elevate.
- Live CPU, RAM, drive and battery telemetry plus top memory-consuming processes.
- Read-only process listing and startup-app inspection.
- Open allow-listed Windows apps, common folders, and an existing path supplied by the user.
- Change between Balanced, High performance, and Ultimate performance power plans after confirmation.
- Close a process by PID only after confirmation; protected/system processes are blocked.
- Read Microsoft Defender protection status and start a quick scan after confirmation. JARVIS never disables Defender.
- Lock, restart, or shut down Windows only after confirmation; restart/shutdown are scheduled with a 60-second cancellation window.
- Search Desktop, Documents, and Downloads for a filename.
- Unknown text is never passed to PowerShell, CMD, or an arbitrary shell.

### Example commands
- `PC status`
- `list processes`
- `show startup apps`
- `Defender status`
- `start Defender scan`
- `set high performance` / `set balanced power`
- `close process 1234`
- `open C:\\Users\\YourName\\Documents`
- `find file report.pdf`
- `lock PC`, `restart PC`, `cancel shutdown`

Administrator access is not a magic bypass for Windows security boundaries. UAC, user permissions, Defender, and file ownership continue to apply.
