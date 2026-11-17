"""Bounded local coding workspace for JARVIS.

All file access is restricted to the user's JARVIS workspace. Project commands are
explicitly allow-listed and require confirmation because build/test scripts execute code.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

MAX_READ_BYTES = 160_000
MAX_WRITE_BYTES = 1_000_000
MAX_TREE_ENTRIES = 300
IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "target", "dist", "build", ".idea", ".vscode", ".jarvis-backups"}
BLOCKED_DIRS = {".git", ".ssh", ".gnupg", ".aws", ".azure", ".kube"}
BLOCKED_NAMES = {"id_rsa", "id_ed25519", "known_hosts", "credentials", "secrets.json", ".npmrc", ".pypirc"}

def workspace_root() -> Path:
    configured = os.environ.get("JARVIS_WORKSPACE")
    root = Path(configured).expanduser() if configured else Path.home() / "Documents" / "JARVIS-Workspace"
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root

def _project_path(project: str = ".") -> Path:
    root = workspace_root()
    candidate = (root / project).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("That project path is outside the JARVIS workspace.")
    if not candidate.exists() or not candidate.is_dir():
        raise ValueError("Project folder does not exist inside the JARVIS workspace.")
    return candidate

def _file_path(project: str, relative_path: str) -> Path:
    base = _project_path(project)
    candidate = (base / relative_path).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError("That file path escapes the selected project.")
    relative_parts = Path(relative_path).parts
    if any(part.casefold() in BLOCKED_DIRS for part in relative_parts):
        raise ValueError("JARVIS will not access credential stores or version-control internals.")
    name = candidate.name.casefold()
    if name in BLOCKED_NAMES or (name.startswith(".env") and name not in {".env.example", ".env.sample", ".env.template"}):
        raise ValueError("JARVIS will not read or overwrite secret environment or credential files.")
    if candidate.suffix.casefold() in {".pem", ".key", ".p12", ".pfx"}:
        raise ValueError("JARVIS will not access private-key or certificate files.")
    return candidate

def list_projects() -> str:
    root = workspace_root()
    projects = sorted(p.name for p in root.iterdir() if p.is_dir() and not p.is_symlink())
    return f"JARVIS coding workspace: {root}\nProjects:\n" + ("\n".join(projects[:100]) if projects else "(empty)")

def inspect_project(project: str = ".") -> str:
    base = _project_path(project)
    rows = [f"Project: {base}", "Files (bounded listing):"]
    count = 0
    for current, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and not (Path(current) / d).is_symlink())
        rel_dir = Path(current).relative_to(base)
        for name in sorted(files):
            path = Path(current) / name
            if path.is_symlink():
                continue
            rel = (rel_dir / name).as_posix()
            try:
                size = path.stat().st_size
            except OSError:
                continue
            rows.append(f"{rel} ({size} bytes)")
            count += 1
            if count >= MAX_TREE_ENTRIES:
                rows.append("... listing truncated")
                break
        if count >= MAX_TREE_ENTRIES:
            break
    for manifest in ("README.md", "pyproject.toml", "Cargo.toml", "package.json", "pom.xml", "build.gradle", "*.sln"):
        matches = list(base.glob(manifest)) if "*" in manifest else ([base / manifest] if (base / manifest).is_file() else [])
        for path in matches[:2]:
            try:
                snippet = path.read_text(encoding="utf-8", errors="replace")[:5000]
                rows.append(f"\n--- {path.name} ---\n{snippet}")
            except OSError:
                pass
    return "\n".join(rows)[:22000]

def read_file(project: str, relative_path: str) -> str:
    path = _file_path(project, relative_path)
    if not path.is_file():
        raise ValueError("That project file does not exist.")
    if path.stat().st_size > MAX_READ_BYTES:
        raise ValueError(f"File is larger than the {MAX_READ_BYTES}-byte reading limit.")
    try:
        return f"--- {relative_path} ---\n" + path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("That file is not UTF-8 text; binary files are not readable through this tool.") from exc

def write_file(project: str, relative_path: str, content: str) -> str:
    if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        raise ValueError(f"File content exceeds the {MAX_WRITE_BYTES}-byte limit.")
    path = _file_path(project, relative_path)
    if path.exists() and not path.is_file():
        raise ValueError("The destination exists and is not a regular file.")
    existed_before = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_note = ""
    if existed_before:
        backup_root = _project_path(project) / ".jarvis-backups"
        backup_name = "__".join(Path(relative_path).parts)
        backup_path = backup_root / (backup_name + "." + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".bak")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
        backup_note = " A timestamped backup was saved in .jarvis-backups."
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=".jarvis-", suffix=".tmp",
                                         delete=False) as handle:
            temp_name = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            try:
                os.unlink(temp_name)
            except OSError:
                pass
    return f"Wrote {relative_path} ({path.stat().st_size} bytes).{backup_note} Re-read the file to verify it."

COMMANDS = {
    "python_tests": ([sys.executable, "-m", "pytest", "-q"], "Run Python test suite"),
    "python_compile": ([sys.executable, "-m", "compileall", "-q", "."], "Compile-check Python files"),
    "cargo_check": (["cargo", "check"], "Run cargo check"),
    "cargo_test": (["cargo", "test"], "Run cargo tests"),
    "cargo_build": (["cargo", "build", "--release"], "Build Rust release"),
    "npm_test": (["npm", "test"], "Run npm tests"),
    "npm_build": (["npm", "run", "build"], "Run npm build"),
    "dotnet_test": (["dotnet", "test"], "Run .NET tests"),
    "dotnet_build": (["dotnet", "build"], "Build .NET project"),
}

def run_check(project: str, check: str) -> str:
    base = _project_path(project)
    if check not in COMMANDS:
        raise ValueError("Unsupported project check.")
    command, label = COMMANDS[check]
    try:
        result = subprocess.run(command, cwd=base, capture_output=True, text=True,
                                timeout=900, shell=False)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required build tool is not installed: {command[0]}") from exc
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{label} exceeded the 15-minute time limit.")
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    status = "PASSED" if result.returncode == 0 else f"FAILED (exit {result.returncode})"
    return f"{label}: {status}\n{output[-12000:]}".strip()

def create_project(name: str) -> str:
    clean = " ".join(str(name).strip().split())
    if not clean or len(clean) > 80 or clean in {".", ".."} or any(ch in clean for ch in '<>:"/\\\\|?*'):
        raise ValueError("Choose a simple project name (letters, numbers, spaces, dots, dashes or underscores).")
    root = workspace_root()
    target = (root / clean).resolve()
    if root not in target.parents:
        raise ValueError("Invalid project folder.")
    target.mkdir(parents=True, exist_ok=False)
    return f"Created project folder: {target}"
