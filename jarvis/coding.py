"""Bounded local coding workspace for JARVIS.

All file access is restricted to the user's JARVIS workspace. Project commands are
explicitly allow-listed and require confirmation because build/test scripts execute code.
"""
from __future__ import annotations

import difflib
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
BLOCKED_DIRS = {".git", ".ssh", ".gnupg", ".aws", ".azure", ".kube", ".jarvis-backups"}
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
    relative = Path(relative_path)
    if relative.is_absolute() or not relative_path or chr(0) in relative_path:
        raise ValueError("Use a non-empty relative project file path.")
    if any(part.casefold() in BLOCKED_DIRS for part in relative.parts):
        raise ValueError("JARVIS will not access credential stores, backups or version-control internals.")
    lexical = base / relative
    cursor = base
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symbolic-link paths are not allowed in the coding workspace.")
    candidate = lexical.resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError("That file path escapes the selected project.")
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


def preview_file_change(project: str, relative_path: str, content: str) -> str:
    """Return a bounded unified diff without changing the project."""
    if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        raise ValueError(f"Proposed content exceeds the {MAX_WRITE_BYTES}-byte limit.")
    path = _file_path(project, relative_path)
    if path.exists() and not path.is_file():
        raise ValueError("The destination exists and is not a regular file.")
    if path.exists():
        if path.stat().st_size > MAX_READ_BYTES:
            raise ValueError(f"Existing file is larger than the {MAX_READ_BYTES}-byte preview limit.")
        before = path.read_text(encoding="utf-8").splitlines(keepends=True)
    else:
        before = []
    after = content.splitlines(keepends=True)
    diff = "".join(difflib.unified_diff(
        before, after, fromfile=f"a/{relative_path}" if before else "/dev/null",
        tofile=f"b/{relative_path}", n=3
    ))
    if not diff:
        return f"No changes proposed for {relative_path}."
    return f"Proposed change for {relative_path} (preview only; nothing written):\n{diff[:18000]}"

def search_project(project: str, query: str) -> str:
    """Search bounded UTF-8 project text for a symbol or phrase without executing code."""
    needle = str(query).strip()
    if not needle or len(needle) > 120:
        raise ValueError("Enter a search phrase between 1 and 120 characters.")
    base = _project_path(project)
    matches = []
    scanned = 0
    skipped_large = 0
    for current, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and d.casefold() not in BLOCKED_DIRS and not (Path(current) / d).is_symlink())
        for name in sorted(files):
            candidate = Path(current) / name
            if candidate.is_symlink():
                continue
            relative = candidate.relative_to(base).as_posix()
            try:
                safe_path = _file_path(project, relative)
                if not safe_path.is_file():
                    continue
                if safe_path.stat().st_size > MAX_READ_BYTES:
                    skipped_large += 1
                    continue
                content = safe_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError, ValueError):
                continue
            scanned += 1
            for line_no, line in enumerate(content.splitlines(), 1):
                if needle.casefold() in line.casefold():
                    matches.append(f"{relative}:{line_no}: {line.strip()[:240]}")
                    if len(matches) >= 80:
                        return f"Project search for {needle!r} (first 80 matches; results capped):\n" + "\n".join(matches)
    summary = f"Project search for {needle!r}: scanned {scanned} text files"
    if skipped_large:
        summary += f"; skipped {skipped_large} files over {MAX_READ_BYTES} bytes"
    return summary + ".\n" + ("\n".join(matches) if matches else "No matches found.")


def audit_python_project(project: str) -> str:
    """Run bounded, read-only AST and heuristic security checks on Python source."""
    import ast
    import re

    base = _project_path(project)
    findings: list[tuple[str, str, str, str]] = []
    scanned = 0
    considered = 0
    skipped_large = 0
    truncated = False
    syntax_errors = 0
    secret_pattern = re.compile(
        r"""(?i)\b(?:[A-Za-z_][A-Za-z0-9_]*_)?"""
        r"""(?:api[_-]?(?:key|token)|client[_-]?secret|secret|password|token)"""
        r"""(?:_[A-Za-z0-9_]+)?\b\s*[:=]\s*['"][^'"]{8,}['"]"""
    )
    dangerous_calls = {
        "eval": ("HIGH", "Dynamic eval() executes data as Python code."),
        "exec": ("HIGH", "exec() executes dynamically supplied code."),
        "os.system": ("MEDIUM", "os.system() invokes a system shell; prefer argument-list subprocess calls."),
        "pickle.load": ("HIGH", "Untrusted pickle data can execute code during deserialization."),
        "pickle.loads": ("HIGH", "Untrusted pickle data can execute code during deserialization."),
    }
    for current, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and d.casefold() not in BLOCKED_DIRS
                         and not (Path(current) / d).is_symlink())
        for name in sorted(files):
            candidate = Path(current) / name
            if candidate.suffix.casefold() != ".py" or candidate.is_symlink():
                continue
            considered += 1
            if considered > 2000:
                truncated = True
                break
            relative = candidate.relative_to(base).as_posix()
            try:
                safe_path = _file_path(project, relative)
                if not safe_path.is_file():
                    continue
                if safe_path.stat().st_size > MAX_READ_BYTES:
                    skipped_large += 1
                    continue
                source = safe_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError, ValueError):
                continue
            scanned += 1
            try:
                tree = ast.parse(source, filename=relative)
            except SyntaxError as exc:
                syntax_errors += 1
                findings.append(("ERROR", relative, str(exc.lineno or 1), "Python syntax error; source was not executed."))
                continue

            for line_no, line in enumerate(source.splitlines(), 1):
                if secret_pattern.search(line):
                    findings.append(("HIGH", relative, str(line_no),
                                     "Possible hard-coded credential; value deliberately not displayed."))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                parts = []
                current_node = node.func
                while isinstance(current_node, ast.Attribute):
                    parts.append(current_node.attr)
                    current_node = current_node.value
                if isinstance(current_node, ast.Name):
                    parts.append(current_node.id)
                call_name = ".".join(reversed(parts))
                if call_name in dangerous_calls:
                    severity, message = dangerous_calls[call_name]
                    findings.append((severity, relative, str(getattr(node, "lineno", 1)), message))
                if call_name in {"subprocess.run", "subprocess.Popen", "subprocess.call"}:
                    if any(keyword.arg == "shell" and isinstance(keyword.value, ast.Constant)
                           and keyword.value.value is True for keyword in node.keywords):
                        findings.append(("HIGH", relative, str(getattr(node, "lineno", 1)),
                                         "subprocess is invoked with shell=True; review for command injection."))
                if call_name == "yaml.load":
                    loader = next((keyword.value for keyword in node.keywords if keyword.arg == "Loader"), None)
                    safe_loader = (
                        isinstance(loader, ast.Name) and loader.id in {"SafeLoader", "CSafeLoader"}
                    ) or (
                        isinstance(loader, ast.Attribute) and loader.attr in {"SafeLoader", "CSafeLoader"}
                    )
                    if not safe_loader:
                        findings.append(("HIGH", relative, str(getattr(node, "lineno", 1)),
                                         "yaml.load() does not use a recognized safe Loader; use yaml.safe_load()."))
            if len(findings) >= 120:
                break
        if truncated or len(findings) >= 120:
            break

    scope_note = f" Skipped {skipped_large} files larger than {MAX_READ_BYTES} bytes." if skipped_large else ""
    if truncated:
        scope_note += " Stopped after 2,000 Python files; the remaining project was not audited."
    if not findings:
        return (f"Python static audit complete: scanned {scanned} files; no configured checks triggered."
                f"{scope_note} This is not proof the project is secure; no code was executed.")
    order = {"ERROR": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda item: (order.get(item[0], 9), item[1], int(item[2]) if item[2].isdigit() else 0))
    lines = [f"Python static audit: scanned {scanned} files; {syntax_errors} syntax errors; "
             f"{len(findings)} findings (capped at 120).{scope_note}"]
    lines.extend(f"[{severity}] {path}:{line} — {message}"
                 for severity, path, line, message in findings[:120])
    lines.append("Read-only heuristic audit: findings need human review; absence of findings is not a security guarantee.")
    return "\n".join(lines)


COMMANDS = {
    "python_tests": ([sys.executable, "-m", "pytest", "-q"], "Run Python test suite"),
    "python_compile": ([sys.executable, "-m", "compileall", "-q", "-x", r"(^|[\\/])(\.git|\.venv|venv|node_modules|target|dist|build|\.jarvis-backups)([\\/]|$)", "."], "Compile-check Python files"),
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
