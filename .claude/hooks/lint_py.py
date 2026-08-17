"""PostToolUse hook: run Ruff on a Python file Claude just wrote or edited.

Reads the hook payload from stdin, formats and auto-fixes the edited file, then
reports anything Ruff could not fix back to Claude via stderr and exit code 2.

Stdlib only: `jq` is not available on this machine and hook commands default to
Git Bash on Windows, so the usual shell recipe does not work here.

mypy is deliberately not run here. Single-file mypy re-analyses imports and
reports misleading errors mid-edit; type checking belongs in stop_gate.py, where
the tree is whole.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TIMEOUT_SECONDS = 60


def find_ruff(project_dir: Path) -> Path | None:
    """Locate the project's Ruff executable.

    Args:
        project_dir: Repository root.

    Returns:
        Path to Ruff inside the project venv, or None if it is not installed.
    """
    candidates = [
        project_dir / ".venv" / "Scripts" / "ruff.exe",  # Windows
        project_dir / ".venv" / "bin" / "ruff",  # POSIX
    ]
    return next((c for c in candidates if c.exists()), None)


def run(ruff: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run Ruff with the given arguments.

    Args:
        ruff: Path to the Ruff executable.
        args: Arguments to pass to Ruff.

    Returns:
        The completed process, with output captured as text.
    """
    return subprocess.run(
        [str(ruff), *args],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )


def target_file(payload: dict[str, object], project_dir: Path) -> Path | None:
    """Extract the edited Python file from the hook payload.

    Args:
        payload: Decoded hook JSON from stdin.
        project_dir: Repository root.

    Returns:
        The file to lint, or None if this edit is not a Python file inside the
        project.
    """
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    raw = tool_input.get("file_path")
    if not isinstance(raw, str) or not raw.endswith(".py"):
        return None

    path = Path(raw)
    if not path.is_absolute():
        path = project_dir / path
    if not path.exists():
        return None

    try:
        path.resolve().relative_to(project_dir.resolve())
    except ValueError:
        return None  # outside the project
    return path


def main() -> None:
    """Format and lint the edited file, reporting what could not be fixed."""
    # lstrip the BOM: some shells prepend one when piping to a native command.
    raw = sys.stdin.read().lstrip("﻿").strip()
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        print(f"lint_py.py could not parse its payload: {exc}", file=sys.stderr)
        sys.exit(0)  # surface it, but never block on a bad payload

    project_dir = Path(payload.get("cwd") or Path.cwd())
    path = target_file(payload, project_dir)
    if path is None:
        sys.exit(0)

    ruff = find_ruff(project_dir)
    if ruff is None:
        sys.exit(0)  # no venv yet; the stop gate will say so

    try:
        # Fix first, then format: fixes (e.g. removing an unused import) leave
        # whitespace behind that only a subsequent format pass tidies up.
        run(ruff, ["check", "--fix", str(path)])
        run(ruff, ["format", str(path)])
        remaining = run(ruff, ["check", str(path)])
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"ruff could not be run on {path.name}: {exc}", file=sys.stderr)
        sys.exit(2)

    if remaining.returncode != 0:
        print(
            f"Ruff issues remain in {path.name} after --fix:\n"
            f"{remaining.stdout}{remaining.stderr}",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
