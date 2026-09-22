"""SessionStart hook: tell a fresh session where the pipeline left off.

The ten-step workflow stops for the user after steps 1, 2 and 8, and the build
block in between can halt to ask, so a session often starts in the middle of
something. Rather than relying on the user to remember the state — or on Claude
to guess it — this hook reads the active plan file and injects a short brief as
session context.

Silent when nothing is in flight: a repo with no active plan starts clean.

Stdlib only: `jq` is not available on this machine and hook commands default to
Git Bash on Windows, so the usual shell recipe does not work here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from plan_state import STEP_NAMES, Plan, all_plans, current_branch, feature_rounds

# Which skill resumes each step, keyed by the step it produces.
STEP_SKILLS: dict[int, str] = {
    1: "/conceptualize",
    2: "/plan",
    3: "/build",
    4: "/build",
    5: "/build",
    6: "/build",
    7: "/build",
    8: "/recommend",
    9: "/create-pr",
    10: "/watch-pr",
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
        f"It is on **step {plan.step} of {max(STEP_SKILLS)} — {plan.step_name}**, "
        f"resumed with `{STEP_SKILLS[plan.step]}`.",
    ]

    if plan.step < max(STEP_SKILLS):
        following = plan.step + 1
        lines.append(
            f"The step after it is {following} ({STEP_NAMES[following]}), "
            f"`{STEP_SKILLS[following]}`."
        )

    earlier = [
        other
        for other in feature_rounds(project_dir, plan.feature)
        if other.round_number < plan.round_number
    ]
    if earlier:
        shipped = ", ".join(f"`{other.path.name}` ({other.title})" for other in earlier)
        lines.append(
            f"\nThis is round {plan.round_number} of `{plan.feature}`. Earlier rounds "
            f"are already on the branch: {shipped}. Read them before changing anything — "
            "their acceptance criteria still have to hold."
        )

    checked_out = current_branch(project_dir)
    if plan.branch and checked_out and plan.branch != checked_out:
        lines.append(
            f"\n**Branch mismatch.** The plan names `{plan.branch}` but "
            f"`{checked_out}` is checked out. Resolve this before writing code."
        )

    lines.append(
        "\nRead the plan file before doing anything to it. Steps 1, 2 and 8 wait "
        "for the user; steps 3 to 7 run as one block under `/build`, which "
        "resumes from the step above and halts only to ask."
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
