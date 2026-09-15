"""SessionStart hook: tell a fresh session where the pipeline left off.

The nine-step workflow deliberately stops after every step, so a session almost
always starts in the middle of something. Rather than relying on the user to
remember the state — or on Claude to guess it — this hook reads the active plan
file and injects a short brief as session context.

Silent when nothing is in flight: a repo with no active plan starts clean.

Stdlib only: `jq` is not available on this machine and hook commands default to
Git Bash on Windows, so the usual shell recipe does not work here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from plan_state import STEP_NAMES, Plan, all_plans, current_branch

# Which skill resumes each step, keyed by the step it produces.
STEP_SKILLS: dict[int, str] = {
    1: "/conceptualize",
    2: "/plan",
    3: "/implement",
    4: "/verify",
    5: "/test",
    6: "/concept-check",
    7: "/ship",
    8: "/recommend",
    9: "/create-pr",
}


def brief(project_dir: Path, plan: Plan) -> str:
    """Describe the state of one active plan.

    Args:
        project_dir: Repository root.
        plan: The plan to describe.

    Returns:
        A few lines of context for the start of the session.
    """
    lines = [
        "## Workflow state",
        "",
        f"An implementation pipeline is in flight: `{plan.path}` — {plan.title}",
        f"It is on **step {plan.step} of 9 — {plan.step_name}**, "
        f"resumed with `{STEP_SKILLS[plan.step]}`.",
    ]

    if plan.step < 9:
        following = plan.step + 1
        lines.append(
            f"The step after it is {following} ({STEP_NAMES[following]}), "
            f"`{STEP_SKILLS[following]}`."
        )

    checked_out = current_branch(project_dir)
    if plan.branch and checked_out and plan.branch != checked_out:
        lines.append(
            f"\n**Branch mismatch.** The plan names `{plan.branch}` but "
            f"`{checked_out}` is checked out. Resolve this before writing code."
        )

    lines.append(
        "\nRead the plan file before doing anything to it. The pipeline never "
        "advances on its own — finish the current step, then stop and wait."
    )
    return "\n".join(lines)


def main() -> None:
    """Inject the active plan's state into the new session's context."""
    # lstrip the BOM: some shells prepend one when piping to a native command.
    raw = sys.stdin.read().lstrip("﻿").strip()
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        sys.exit(0)  # a session should never fail to start over this

    project_dir = Path(payload.get("cwd") or Path.cwd())
    active = [plan for plan in all_plans(project_dir) if plan.status == "active"]
    if not active:
        sys.exit(0)

    context = brief(project_dir, active[0])
    if len(active) > 1:
        others = ", ".join(f"`{plan.path}`" for plan in active[1:])
        context += (
            f"\n\n**More than one plan is marked active.** The most recently "
            f"touched one is described above; also active: {others}. "
            "Park the ones that are not being worked on."
        )

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                }
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
