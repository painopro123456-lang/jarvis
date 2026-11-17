# JARVIS capability roadmap

This roadmap separates working foundations from features that still need implementation and testing. A roadmap entry is not a claim that the feature is already available in the Windows app.

## 1. Reasoning and task execution

**Foundation present**
- Local Ollama model with tool calling.
- Bounded tool-call loop.
- System instructions now require a stepwise plan for complex tasks, inspection of each tool result, and evidence-based success claims.
- Software discovery can search by task description; results must be shown and the user must choose before installation.

**Next**
- Add visible task plans with per-step status (planned, waiting for approval, running, verified, failed).
- Persist resumable plans and detect duplicate/repeated actions.
- Add targeted retry rules and stop conditions rather than repeating failed actions.

## 2. PC awareness and optimization

**Foundation present**
- CPU, memory, disk, battery and process telemetry.
- Startup, driver inventory, diagnostics and optional local screen understanding.

**Next**
- Build a hardware/software inventory with source and timestamp for each fact.
- Add measured before/after optimization recommendations.
- Compare driver versions against official OEM/vendor release sources; Windows Update discovery alone is not a complete latest-driver comparison.
- Never apply an optimization without preview and approval.

## 3. Security

**Foundation present**
- Microsoft Defender and Firewall status, network/process review indicators, file scans and Defender quick scan.
- Indicators are explicitly not treated as proof of malware.

**Next**
- Add signed-file metadata and reputation lookups with source attribution.
- Add alert history and a review queue.
- Do not build a replacement antivirus engine or silently quarantine/delete files. Use Windows Security/Defender for remediation.

## 4. Browser companion

**Not yet implemented**
- Build a Chrome/Edge extension with narrow permissions and a visible connected-tab state.
- Prefer active-tab scoped access; do not read passwords, cookies, session tokens or unrelated tabs.
- Ask before form submission, messaging, purchases, uploads or downloads.
- Show the exact page and action to be performed, then verify the resulting page state.

## 5. Voice and personality

**Foundation present**
- Text-to-speech, microphone input and optional wake-word recognition.
- Local conversation history within the current AI session.

**Next**
- Add voice activity detection, interruption/barge-in, partial transcription and clearer microphone state.
- Add durable user-controlled preferences separately from conversational history.
- Keep wake-word processing local where possible; clearly label any online speech recognition.

## 6. Approval, audit and recovery

**Foundation present**
- Consequential AI tool actions require a confirmation callback; if no approval UI is available, those actions fail closed.
- A minimal local activity log stores timestamp, action name and outcome only.
- Saved automation routines remain disabled by default.

**Next**
- Add previews and typed approval scopes for each action.
- Verify settings after changes and implement rollback only where Windows exposes a reliable inverse operation.
- Keep an audit entry for manual GUI actions as well as AI tool calls.
- Never promise rollback for destructive or inherently irreversible operations.

## 7. Software researcher

**Foundation present**
- Read-only search of the Windows Package Manager catalogue using app names or feature descriptions.
- Separate install/update action with confirmation.

**Next**
- Parse catalogue results into structured candidates with publisher, package ID, version and source.
- Rank alternatives using feature fit, publisher trust, compatibility and licensing/pricing evidence.
- Require the user to choose a specific candidate before install; never infer a package ID from fuzzy text alone.
- Verify installation by querying the package manager after completion.

## Architecture

- **Rust core:** narrow, typed Windows operations, system inventory and permission enforcement.
- **Python/PySide6 shell (current):** GUI, local AI orchestration, voice and current integrations.
- **Local model:** understands requests and proposes plans; it does not receive arbitrary shell access.
- **Browser extension (future):** isolated, user-visible browser actions with minimal permissions.

The goal is a capable assistant with observable, reversible where possible, user-approved actions—not unrestricted access or a claim that mistakes are impossible.
