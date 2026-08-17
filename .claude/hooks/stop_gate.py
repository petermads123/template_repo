"""Stop hook: refuse to end the turn on a broken tree.

Runs only when Python files actually changed, so conversational turns stay
instant. When they did change, it runs the full verification set and
cross-checks STRUCTURE.md against the modules on disk, then blocks with a
specific reason if anything fails.

Stdlib only: `jq` is not available on this machine and hook commands default to
Git Bash on Windows.

Escape hatch: create `.claude/.skip-gate` to bypass this deliberately.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

TOOL_TIMEOUT_SECONDS = 300
GIT_TIMEOUT_SECONDS = 30

# Paths mentioned in STRUCTURE.md that look like this are prose, not real files.
PLACEHOLDER = re.compile(r"[<>*]")
PATH_IN_TEXT = re.compile(r"[\w./-]+\.py")


def venv_tool(project_dir: Path, name: str) -> Path | None:
    """Locate an executable inside the project's virtual environment.

    Args:
        project_dir: Repository root.
        name: Tool name without extension, e.g. "ruff".

    Returns:
        Path to the executable, or None if the venv does not provide it.
    """
    candidates = [
        project_dir / ".venv" / "Scripts" / f"{name}.exe",  # Windows
        project_dir / ".venv" / "bin" / name,  # POSIX
    ]
    return next((c for c in candidates if c.exists()), None)


def capture(
    cmd: list[str], cwd: Path, timeout: int
) -> subprocess.CompletedProcess[str]:
    """Run a command and capture its output.

    Args:
        cmd: Command and arguments.
        cwd: Working directory.
        timeout: Seconds before giving up.

    Returns:
        The completed process, with output captured as text.
    """
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def git_lines(project_dir: Path, args: list[str]) -> list[str]:
    """Run a git command and return its non-empty output lines.

    Args:
        project_dir: Repository root.
        args: Git arguments, without the leading "git".

    Returns:
        Output lines, or an empty list if git failed.
    """
    try:
        result = capture(["git", *args], project_dir, GIT_TIMEOUT_SECONDS)
    except (subprocess.TimeoutExpired, OSError):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def changed_python_files(project_dir: Path) -> set[str]:
    """Find Python files changed in the working tree or committed on this branch.

    Checking committed changes too means the gate still fires when work was
    committed earlier in the turn and the working tree is now clean.

    Args:
        project_dir: Repository root.

    Returns:
        Repo-relative paths of changed Python files.
    """
    changed: set[str] = set()

    for line in git_lines(project_dir, ["status", "--porcelain"]):
        path = line[3:] if len(line) > 3 else ""
        if " -> " in path:  # rename: "old -> new"
            path = path.split(" -> ", 1)[1]
        path = path.strip().strip('"')
        if path.endswith(".py"):
            changed.add(path)

    branch = git_lines(project_dir, ["branch", "--show-current"])
    if branch and branch[0] != "main":
        diff = git_lines(project_dir, ["diff", "--name-only", "main...HEAD"])
        changed.update(p for p in diff if p.endswith(".py"))

    return changed


def tracked_python_files(project_dir: Path) -> set[str]:
    """List every Python file in the repo, honouring .gitignore.

    Args:
        project_dir: Repository root.

    Returns:
        Repo-relative paths of all non-ignored Python files.
    """
    lines = git_lines(
        project_dir,
        ["ls-files", "--cached", "--others", "--exclude-standard", "--", "*.py"],
    )
    return {line.strip().strip('"') for line in lines}


def structure_problems(project_dir: Path) -> list[str]:
    """Cross-check STRUCTURE.md against the Python files on disk.

    This is a file-level check only. Signature drift is invisible to it; use the
    structure-auditor subagent for that.

    Args:
        project_dir: Repository root.

    Returns:
        Human-readable problem descriptions, empty if the two agree.
    """
    structure = project_dir / "STRUCTURE.md"
    if not structure.exists():
        return ["STRUCTURE.md is missing from the repo root."]

    text = structure.read_text(encoding="utf-8")
    on_disk = tracked_python_files(project_dir)

    problems = [
        f"STRUCTURE.md does not mention `{path}`, which exists on disk."
        for path in sorted(on_disk)
        if path not in text
    ]

    mentioned = {
        match
        for match in PATH_IN_TEXT.findall(text)
        if "/" in match and not PLACEHOLDER.search(match)
    }
    problems.extend(
        f"STRUCTURE.md mentions `{path}`, which no longer exists."
        for path in sorted(mentioned)
        if not (project_dir / path).exists()
    )
    return problems


def gate_failures(project_dir: Path) -> list[str]:
    """Run ruff, mypy and pytest, collecting failures.

    Args:
        project_dir: Repository root.

    Returns:
        One entry per failed command, including its output.
    """
    checks = [
        ("ruff", ["check", "."]),
        ("ruff", ["format", "--check", "."]),
        ("mypy", []),
        ("pytest", ["-q"]),
    ]

    failures: list[str] = []
    for name, args in checks:
        tool = venv_tool(project_dir, name)
        if tool is None:
            failures.append(f'`{name}` is not installed. Run: pip install -e ".[dev]"')
            continue
        try:
            result = capture([str(tool), *args], project_dir, TOOL_TIMEOUT_SECONDS)
        except (subprocess.TimeoutExpired, OSError) as exc:
            failures.append(f"`{name}` could not be run: {exc}")
            continue
        if result.returncode != 0:
            command = " ".join([name, *args])
            output = (result.stdout + result.stderr).strip()
            failures.append(f"`{command}` failed:\n{output}")
    return failures


def block(reason: str) -> None:
    """Tell Claude Code to keep going instead of stopping.

    Args:
        reason: Why the turn may not end yet.
    """
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def main() -> None:
    """Gate the end of the turn on a clean, documented tree."""
    # lstrip the BOM: some shells prepend one when piping to a native command.
    raw = sys.stdin.read().lstrip("﻿").strip()
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        print(f"stop_gate.py could not parse its payload: {exc}", file=sys.stderr)
        sys.exit(0)  # surface it, but never block on a payload we cannot read

    if payload.get("stop_hook_active"):
        sys.exit(0)  # already blocked once this turn; do not loop

    project_dir = Path(payload.get("cwd") or Path.cwd())

    if (project_dir / ".claude" / ".skip-gate").exists():
        sys.exit(0)

    if not changed_python_files(project_dir):
        sys.exit(0)  # nothing to check; keep conversational turns instant

    problems = gate_failures(project_dir) + structure_problems(project_dir)
    if problems:
        block(
            "The tree is not ready to hand back. Fix these, then stop again:\n\n"
            + "\n\n".join(f"- {p}" for p in problems)
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
