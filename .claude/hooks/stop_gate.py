"""Stop hook: refuse to end the turn on a broken tree, once the step warrants it.

The ten-step pipeline runs steps 3 to 7 as one unattended block that carries
its own gates — ruff, mypy and pytest at steps 4, 5 and 7 — and halts to ask
the user when something needs a decision. A halt can leave the tree red on
purpose, and a gate that refused to end that turn would force the second fix
attempt the halting rule forbids. This hook therefore reads the active plan
file and scales its strictness:

- **No active plan** (a `/small-change`, or ad-hoc work): strict, as before.
  Any turn that touched Python must leave ruff, mypy, pytest and STRUCTURE.md
  in order, with every test file somewhere pytest will actually collect it.
- **Steps 1 to 7**: advisory. Nothing is run; the turn ends freely, with a note
  saying when the gate starts biting. Python changing during steps 1 or 2 is
  itself worth a note, since those steps are meant to produce a plan, not code.
- **Steps 8 to 10**: strict, same as no plan. Step 7 is where the block
  promises a green tree, and nothing after it is allowed to take that back.

Stdlib only: `jq` is not available on this machine and hook commands default to
Git Bash on Windows, so the usual shell recipe does not work here.

Escape hatch: create `.claude/.skip-gate` to bypass this deliberately.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from plan_state import GATE_FROM_STEP, Plan, active_plan, current_branch, git_lines

TOOL_TIMEOUT_SECONDS = 300

# Must match `testpaths` in pyproject.toml: pytest collects nothing outside it.
TEST_DIR = "tests"

# Must match `where` under [tool.setuptools.packages.find]: the installable root.
SRC_DIR = "src"

# Paths mentioned in STRUCTURE.md that look like this are prose, not real files.
PLACEHOLDER = re.compile(r"[<>*]")
# The placeholder characters are matched as part of the path so that
# `src/<package>/module.py` is captured whole and PLACEHOLDER can reject it.
# Leaving them out matched only the `/module.py` tail, which looks like a real
# path, and reported prose as a deleted file.
PATH_IN_TEXT = re.compile(r"[\w./<>*-]+\.py")


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

    if current_branch(project_dir) != "main":
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


def stray_test_files(project_dir: Path) -> list[str]:
    """Find test files pytest will never collect.

    `testpaths` in pyproject.toml scopes collection to one directory, so a test
    file written anywhere else is skipped in silence: `pytest` collects none of
    it and still exits zero. That is the worst failure mode a test can have, so
    it is reported as loudly as a failing one.

    Args:
        project_dir: Repository root.

    Returns:
        Human-readable problem descriptions, empty if every test is collectable.
    """
    prefix = f"{TEST_DIR}/"
    return [
        f"`{path}` looks like a test but is outside `{TEST_DIR}/`, so `pytest` "
        f"never collects it. Move it into `{TEST_DIR}/`."
        for path in sorted(tracked_python_files(project_dir))
        if (Path(path).name.startswith("test_") or Path(path).stem.endswith("_test"))
        and not path.startswith(prefix)
    ]


def missing_init_files(project_dir: Path) -> list[str]:
    """Find package directories under the source root with no `__init__.py`.

    A directory of modules without one is not a package: setuptools will not
    install it, and imports from it resolve only by accident of the working
    directory. Under a `src/` layout that accident stops happening, so the
    failure surfaces at install time rather than here unless it is checked.

    Args:
        project_dir: Repository root.

    Returns:
        Human-readable problem descriptions, empty if every package has one.
    """
    tracked = tracked_python_files(project_dir)
    prefix = f"{SRC_DIR}/"

    packages = {str(Path(path).parent) for path in tracked if path.startswith(prefix)}
    return [
        f"`{package}/` holds modules but no `__init__.py`, so it is not a package "
        "and will not install."
        for package in sorted(packages)
        if f"{package}/__init__.py" not in tracked
    ]


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


def advisory_notes(project_dir: Path, plan: Plan, changed: set[str]) -> list[str]:
    """Collect the non-blocking observations worth surfacing below the gate step.

    Args:
        project_dir: Repository root.
        plan: The active plan.
        changed: Python files changed in the tree or on this branch.

    Returns:
        Notes to show the user, empty if there is nothing to say.
    """
    notes = [
        f"Plan `{plan.path}` is on step {plan.step} ({plan.step_name}). "
        f"The verification gate starts at step {GATE_FROM_STEP}."
    ]

    if changed and plan.step <= 2:
        notes.append(
            f"{len(changed)} Python file(s) changed during a planning step. "
            "Steps 1 and 2 are meant to produce a concept and a plan, not code."
        )

    branch = current_branch(project_dir)
    if plan.branch and branch and branch != plan.branch:
        notes.append(
            f"The plan names branch `{plan.branch}` but `{branch}` is checked out."
        )

    return notes


def notice(message: str) -> None:
    """Show the user a message and let the turn end.

    This ends the hook: reaching it means the current step is not gated, so
    nothing further is checked.

    Args:
        message: What to surface.
    """
    print(json.dumps({"systemMessage": message}))
    sys.exit(0)


def block(reason: str) -> None:
    """Tell Claude Code to keep going instead of stopping.

    Args:
        reason: Why the turn may not end yet.
    """
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def enforce(project_dir: Path) -> None:
    """Run the full verification set and block if anything fails.

    Args:
        project_dir: Repository root.
    """
    problems = (
        gate_failures(project_dir)
        + structure_problems(project_dir)
        + stray_test_files(project_dir)
        + missing_init_files(project_dir)
    )
    if problems:
        block(
            "The tree is not ready to hand back. Fix these, then stop again:\n\n"
            + "\n\n".join(f"- {p}" for p in problems)
        )


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

    changed = changed_python_files(project_dir)
    plan = active_plan(project_dir)

    if plan is None:
        if changed:
            enforce(project_dir)  # no pipeline in flight: hold the old strict line
        sys.exit(0)

    if not plan.gated:
        notice("\n".join(advisory_notes(project_dir, plan, changed)))

    if changed:
        enforce(project_dir)

    sys.exit(0)


if __name__ == "__main__":
    main()
