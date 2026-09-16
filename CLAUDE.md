# Working in this repo

@STRUCTURE.md

`STRUCTURE.md` above is the map of what lives where. Read it before searching the repo, and
update it in the same change whenever a module or public signature changes.

## The implementation pipeline

Anything that is not cosmetic goes through ten steps. State lives in
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
| 10 | Review | `/watch-pr` | Hourly check until the PR merges or closes |

`/feature <what to build>` starts the pipeline and creates the plan folder and its first
round. In a session that is already mid-pipeline it reports the step instead.

Exactly one plan file across the repo carries `status=active`. When step 8 opens the next
round, the round before it becomes `done` and the new file takes over.

### Each step picks its own model

Every skill pins a model and effort in its frontmatter, so a step runs on what it needs
rather than on whatever the session happens to be set to. The override lasts the turn and
reverts on the next prompt.

| Step | Model | Effort | Why |
|---|---|---|---|
| 1 Conceptualize | `opus` | `xhigh` | Shaping the concept is the most expensive thing to get wrong |
| 2 Plan | `opus` | `high` | The design fork, and signatures step 4 checks literally |
| 3 Implement | `sonnet` | `max` | Transcribing a plan that has already done the thinking |
| 4 Verify | `sonnet` | `max` | Mechanical checks plus classifying each mismatch |
| 5 Test | `sonnet` | `max` | Edge cases and the bugs they expose |
| 6 Concept check | `sonnet` | `max` | A different model from the one that wrote the code |
| 7 Ship | `sonnet` | `max` | Commit and push; procedural |
| 8 Recommend | `opus` | `xhigh` | Judging what is worth building next |
| 9 Pull request | `sonnet` | `max` | Verification and writing, both well-specified |
| 10 Review | `opus` | `medium` | Most check-ins find nothing; the judgment is fix-or-new-round |

`/feature` carries step 1's settings because it opens step 1 in the same turn, and a model
override applies for the rest of the turn it is set in. `/small-change` runs `opus` at
`high`: bypassing the pipeline is a judgment call made without any of its safety nets, so
the step that decides whether a change really is small gets the clever model.

`max` is the top effort level; every Sonnet step uses it. Aliases rather than pinned IDs, so
a newer Opus or Sonnet is picked up without editing twelve files. `ultracode` is a
session-level effort setting and not valid in frontmatter, where the levels are `low`,
`medium`, `high`, `xhigh` and `max`.

### Review and merge

| Fact | Value |
|---|---|
| Approver | `petermads123` |
| Merge method | the repository's configured default |

Step 9 requests a review from the approver when it opens the pull request. Step 10 may
**complete the merge**, but only when all five hold: an approval from the approver, that
approval not stale (nothing pushed since), CI green where there is CI, no merge conflict,
and no review thread waiting on Claude.

Never approve anything yourself, and never merge without the approval. An approval says the
change is wanted, not that a failing gate may be bypassed.

**GitHub will not let anyone request a review from, or approve, their own pull request.** In
a solo repo every pull request Claude opens is authored by the person who would approve it,
so the review route is unavailable and waiting for an approval that cannot exist would wedge
the pipeline. There the merge signal is an unambiguous instruction from the approver in a
pull request comment — "merge it", "approved, go ahead". Read it narrowly: "looks good" on
one thread is feedback, not authorisation to merge. When unsure, ask.

### Step 10 runs until the pull request closes

Opening the pull request is not finishing the work. Step 10 re-checks it about once an hour,
acts on review comments and CI, and ends only when the pull request merges or closes — so
the plan file stays `active` through it.

It is the one place a step starts the next one unasked: `/create-pr` invokes `/watch-pr`,
because the alternative is a published pull request nobody is watching. It is also the one
step that mostly does nothing, and a quiet check-in re-arms silently rather than reporting.

Its judgment call is whether a review comment is a fix or a new round. The same small-or-
large test decides, and the same rule applies: **when it is close, route up.** An
over-routed comment costs a conversation; an under-routed one puts unplanned, untested
behaviour into a pull request a reviewer has already read.

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

### Routing is Claude's job, not the user's

**The user never has to type a slash command.** When they describe work in prose — "I want
to add X", "can you change Y", "this should really do Z" — classify it against the test
above *before touching anything*, and act on the classification:

- **Clearly small** — say so in one line with the reason, then make the change under
  `/small-change`.
- **Clearly not small** — say so in one line with the reason, then start `/feature`.
- **Genuinely ambiguous** — ask, with `AskUserQuestion`, offering the two routes and what
  each would mean for this particular request. Do not resolve a coin flip by guessing.

Announce the routing either way. A one-line "small: local rename, no signature or behaviour
change" lets the user correct a wrong call before it costs anything.

**When it is close but not a coin flip, route up.** `/feature` step 1 is a conversation, so
an over-routed change costs a single sentence to correct — "this is tiny, just do it" — but
an under-routed one skips the concept, the tests and the concept check, and nobody finds out
until much later. The two mistakes are not equally expensive.

Three things this rule does *not* cover:

- **An explicit slash command wins.** If the user types `/small-change`, that is the route,
  even if you would have chosen otherwise. Say so if you disagree, then do as asked.
- **A question is not a work request.** "How does the stop gate decide?" or "where does X
  live?" gets an answer, not a pipeline.
- **A plan already in flight takes precedence.** If a plan file is `active`, a new request
  is usually part of *that* work: the current step, a step to go back to, or a step 8
  recommendation. Check the active plan before starting a second pipeline — two active
  plans is a state the hooks will complain about, and rightly.

Never start editing code because a request sounded simple. Skipping the classification is
the failure this section exists to prevent.

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
