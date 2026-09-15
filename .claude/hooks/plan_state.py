"""Read the workflow state that lives in the active plan file.

The nine-step pipeline keeps its state in `docs/plans/<slug>.md`, not in the
conversation. Each plan file carries one machine-readable marker:

    <!-- claude-plan step=3 status=active -->

`stop_gate.py` reads it to decide how strict to be, and `session_brief.py`
reads it to tell a fresh session where the work left off. This module is the
single parser both import, so the format is defined in exactly one place.

Stdlib only, and importable: Python puts a script's own directory on
`sys.path`, so a sibling hook can `import plan_state` with no setup.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

PLAN_DIR = Path("docs") / "plans"

GIT_TIMEOUT_SECONDS = 30

#: Steps from here on run against real code, so the stop gate blocks on failure.
GATE_FROM_STEP = 4

STEP_NAMES: dict[int, str] = {
    1: "Conceptualize",
    2: "Plan",
    3: "Implement",
    4: "Verify",
    5: "Test",
    6: "Concept check",
    7: "Ship",
    8: "Recommend",
    9: "Pull request",
}

MARKER = re.compile(
    r"<!--\s*claude-plan\s+step=(\d+)\s+status=([a-z]+)\s*-->",
    re.IGNORECASE,
)
BRANCH_ROW = re.compile(r"^\|\s*Branch\s*\|\s*([^|\s][^|]*?)\s*\|", re.MULTILINE)
TITLE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class Plan:
    """One plan file and the workflow state it declares.

    Attributes:
        path: Path to the plan file, relative to the repository root.
        step: The step the pipeline is on, 1 through 9.
        status: `active`, `done` or `parked`.
        title: The plan's first-level heading.
        branch: The branch the plan names, or an empty string if it names none.
    """

    path: Path
    step: int
    status: str
    title: str
    branch: str

    @property
    def step_name(self) -> str:
        """Name of the current step, or `unknown` if the number is out of range."""
        return STEP_NAMES.get(self.step, "unknown")

    @property
    def gated(self) -> bool:
        """Whether this step must leave ruff, mypy and pytest green."""
        return self.step >= GATE_FROM_STEP


def parse(path: Path) -> Plan | None:
    """Parse one plan file.

    Args:
        path: Path to a candidate plan file.

    Returns:
        The plan it declares, or None if the file has no valid marker.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    marker = MARKER.search(text)
    if marker is None:
        return None

    step = int(marker.group(1))
    if not 1 <= step <= 9:
        return None

    branch = BRANCH_ROW.search(text)
    title = TITLE.search(text)
    return Plan(
        path=path,
        step=step,
        status=marker.group(2).lower(),
        title=title.group(1).strip() if title else path.stem,
        branch=branch.group(1).strip().strip("`") if branch else "",
    )


def all_plans(project_dir: Path) -> list[Plan]:
    """Parse every plan file in the repo.

    Args:
        project_dir: Repository root.

    Returns:
        Every parseable plan, most recently modified first.
    """
    plan_dir = project_dir / PLAN_DIR
    if not plan_dir.is_dir():
        return []

    plans: list[Plan] = []
    for path in sorted(plan_dir.glob("*.md")):
        plan = parse(path)
        if plan is None:
            continue
        try:
            relative = path.relative_to(project_dir)
        except ValueError:
            relative = path  # project_dir is itself relative; the path is usable as-is
        plans.append(replace(plan, path=relative))
    plans.sort(key=lambda plan: (project_dir / plan.path).stat().st_mtime, reverse=True)
    return plans


def active_plan(project_dir: Path) -> Plan | None:
    """Find the plan the pipeline is currently working through.

    More than one active plan is a mistake rather than an error, so the most
    recently touched one wins instead of the caller having to handle a clash.

    Args:
        project_dir: Repository root.

    Returns:
        The active plan, or None if no plan is active.
    """
    return next(
        (plan for plan in all_plans(project_dir) if plan.status == "active"), None
    )


def git_lines(project_dir: Path, args: list[str]) -> list[str]:
    """Run a git command and return its non-empty output lines.

    Args:
        project_dir: Repository root.
        args: Git arguments, without the leading "git".

    Returns:
        Output lines, or an empty list if git failed or was unavailable.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def current_branch(project_dir: Path) -> str:
    """Name the branch currently checked out.

    A detached HEAD and a failed git call both report as an empty string, since
    neither gives a branch a caller could act on.

    Args:
        project_dir: Repository root.

    Returns:
        The branch name, or an empty string if git could not say.
    """
    lines = git_lines(project_dir, ["branch", "--show-current"])
    return lines[0].strip() if lines else ""


def main() -> None:
    """Showcase this module's functionality."""
    project_dir = Path.cwd()
    print(f"plans found: {[str(plan.path) for plan in all_plans(project_dir)]}")
    print(f"active: {active_plan(project_dir)}")
    print(f"branch: {current_branch(project_dir)!r}")
    print(f"step 4 is gated: {GATE_FROM_STEP <= 4}")


if __name__ == "__main__":
    main()
