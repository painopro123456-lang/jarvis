# JARVIS for Windows

A local-first Windows desktop assistant with an AI personality, voice output, PC telemetry, safe system actions and Microsoft Defender integration.

## Local AI — no API key, no cloud account

JARVIS uses [Ollama](https://ollama.com) to run an open-weight language model on the user's own PC. No OpenAI key, cloud subscription or per-message fee is required.

### First-time setup
1. Download and install the free Windows runtime from [ollama.com/download/windows](https://ollama.com/download/windows).
2. Open JARVIS and click **SET UP LOCAL AI**.
3. JARVIS selects a model based on available system RAM and downloads it once. Default choices: Qwen 3.5 0.8B (under 8 GB RAM), 2B (8–15 GB), or 4B (16 GB+).
4. Once downloaded, JARVIS chats with the model through Ollama on `127.0.0.1`. Conversations and inference stay on the PC.

The first model download requires internet and storage (model sizes vary). After the model is downloaded, ordinary conversations work offline. Local speed and reasoning quality depend on the PC's CPU, RAM and GPU. A small model on an older laptop will be less capable and slower than a large cloud model; JARVIS does not pretend otherwise.

## Personality and reasoning
JARVIS is instructed not to agree automatically. It should respectfully challenge incorrect claims, explain its reasoning, distinguish facts from estimates, admit mistakes when corrected, and use a composed, concise conversational style.

## Current Windows capabilities
- Live CPU, RAM, drive and battery telemetry plus top memory-consuming processes.
- Read-only process listing and startup-app inspection.
- Open allow-listed Windows apps, common folders and existing paths.
- Change between Balanced, High performance and Ultimate performance power plans after confirmation.
- Close a process by PID only after confirmation; protected/system processes are blocked.
- Read Microsoft Defender protection status and start a quick scan after confirmation. JARVIS never disables Defender.
- Lock, restart or shut down Windows only after confirmation; restart/shutdown have a 60-second cancellation window.
- Search Desktop, Documents and Downloads for a filename.
- AI tool calling is restricted to the approved local tool list. Unknown model output is never passed to CMD or PowerShell.

## Voice
JARVIS currently speaks using the installed Windows speech engine. Optional microphone input is provided through SpeechRecognition and Google recognition, which requires internet. See `requirements-voice.txt` for optional dependencies. Fully offline speech recognition is a planned improvement.

## Run from source
1. Install Python 3.11 on Windows.
2. `py -m venv .venv`
3. `.venv\\Scripts\\activate`
4. `pip install -r requirements.txt`
5. `py -m jarvis`

## Build
Run `build.bat`, or use the **Build Windows EXE** workflow in GitHub Actions. The artifact is a portable `JARVIS.exe` (not an installer yet).

## Safety
JARVIS starts without administrator privileges. Operations requiring elevation should use Windows UAC and explicit user approval. Do not grant it unrestricted unattended administrator access. Defender is never disabled and user files are not silently deleted.
