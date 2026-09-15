# Working in this repo

@STRUCTURE.md

`STRUCTURE.md` above is the map of what lives where. Read it before searching the repo, and
update it in the same change whenever a module or public signature changes.

## The implementation pipeline

Anything that is not cosmetic goes through nine steps. State lives in
`docs/plans/<feature-slug>/NN-<round-slug>.md`, not in the conversation, so work survives a
context reset or a new session. One folder per feature, one numbered file per round; a
recommendation accepted at step 8 opens the next round on the same branch.

| # | Step | Skill | Produces |
|---|---|---|---|
| 1 | Conceptualize | `/conceptualize` | Agreed concept and acceptance criteria |
| 2 | Plan | `/plan` | Modules, signatures, implementation guide, test intents |
| 3 | Implement | `/implement` | Branch and working code |
| 4 | Verify | `/verify` | ruff, mypy, plan completeness, STRUCTURE.md |
| 5 | Test | `/test` | Edge-case suite, pytest green |
| 6 | Concept check | `/concept-check` | Audit against step 1, not step 2 |
| 7 | Ship | `/ship` | Commit and push |
| 8 | Recommend | `/recommend` | Ranked follow-ups, decided with the user |
| 9 | Pull request | `/create-pr` | Whole-branch re-verification, then a PR to `main`, ready for review |

`/feature <what to build>` starts the pipeline and creates the plan folder and its first
round. In a session that is already mid-pipeline it reports the step instead.

Exactly one plan file across the repo carries `status=active`. When step 8 opens the next
round, the round before it becomes `done` and the new file takes over.

### The gate between steps is the point

**Finish one step, then stop and wait.** Never begin the next step because it looks
obvious, because the user seems to want speed, or because the two steps are related. The
user opens each step by invoking its skill or saying so.

This is what makes the pipeline worth its overhead: each stop is a place to change course
while it is still cheap. A step that runs into the next one has skipped that decision on
the user's behalf.

Going *backwards* needs no permission. A failing test that reveals an unsettled concept
belongs back at step 1, and saying so is always right.

## What to invoke

| Situation | Use |
|---|---|
| New module, new public function, behavior change, anything needing a design decision | `/feature` |
| Rename, docstring wording, plot styling, message text, formatting | `/small-change` |
| Resuming work already in flight | The step's own skill, or `/feature` to check state |
| Need edge cases for a function | `test-designer` subagent |
| STRUCTURE.md looks out of sync with the code | `structure-auditor` subagent |
| Broad "where is X" search across the repo | built-in `Explore` subagent |

### Small or large?

It is **not** a small change if it does any of these:

- adds or removes a file
- changes a public signature
- changes behavior
- needs a new test

Any one of them routes to `/feature`. Everything else is `/small-change`.

## Conventions

`.claude/rules/python.md` loads automatically whenever a `.py` file is read or edited, so
the conventions are already in context — you do not need to invoke anything to get them.

## Branches

Never commit to `main`; it is protected on the remote and `.claude/hooks/guard_git.py`
refuses the command. Branch names are `type/kebab-case`:

| Prefix | Use for |
|---|---|
| `feat/` | new behavior |
| `fix/` | corrected behavior |
| `refactor/` | changed structure, identical behavior |
| `docs/` | prose only |
| `test/` | test-only additions |
| `chore/` | tooling, dependencies, config |

Examples: `feat/csv-export`, `fix/greet-unicode-crash`, `refactor/split-solver-module`,
`chore/bump-ruff`. The branch is created in step 3 and recorded in the plan file.

## Commands

Run from the repo root with `.venv` active. All four must pass before a PR:

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

## Automation already in place

- **At session start**, `.claude/hooks/session_brief.py` reports the active plan and the
  step it is on. Silent when nothing is in flight.
- **Before every `Bash` call**, `.claude/hooks/guard_git.py` refuses a commit or push that
  would land on `main`, including inside a compound command.
- **After every `Write`/`Edit` of a `.py` file**, `.claude/hooks/lint_py.py` runs
  `ruff format` and `ruff check --fix` on that file. Formatting is handled for you; only
  unfixable errors come back.
- **Before a turn ends**, `.claude/hooks/stop_gate.py` decides how strict to be from the
  active plan's step. Steps 1 to 3 are advisory. From step 4, and whenever no plan is
  active, it blocks if ruff, mypy or pytest fail or `STRUCTURE.md` does not mention a
  module that exists on disk. Create `.claude/.skip-gate` to bypass it deliberately.

Hooks are read at session start. If you change anything under `.claude/hooks/` or
`.claude/settings.json`, Claude Code must be restarted before it takes effect. Skills and
rules hot-reload without a restart.

## Growth

Keep this file a routing map. When guidance grows past routing, move it into a skill — a
skill's body loads only when used, while everything here is in context every session. Facts
and routing stay; procedures become skills.
