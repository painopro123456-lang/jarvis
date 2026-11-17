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
