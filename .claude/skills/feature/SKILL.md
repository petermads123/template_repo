---
name: feature
description: Start or resume the nine-step implementation pipeline for a feature, module, behavior change or anything needing a design decision. Creates the plan file that carries the work from concept to pull request, or reports which step an in-flight plan is on. Use for any change that is not purely cosmetic.
argument-hint: [what to build]
---

# Feature pipeline

Nine steps, one plan file, a hard stop after every step. This skill is the entry point:
it either resumes what is in flight or starts something new. It does not do the work.

## The pipeline

| # | Step | Skill | Produces |
|---|---|---|---|
| 1 | Conceptualize | `/conceptualize` | Agreed concept and acceptance criteria |
| 2 | Plan | `/plan` | Modules, signatures, implementation guide, test intents |
| 3 | Implement | `/implement` | Branch and working code |
| 4 | Verify | `/verify` | ruff, mypy, plan completeness, STRUCTURE.md |
| 5 | Test | `/test` | Edge-case suite, pytest green |
| 6 | Concept check | `/concept-check` | Audit against step 1, not step 2 |
| 7 | Ship | `/ship` | Commit and push |
| 8 | Recommend | `/recommend` | Ranked follow-ups |
| 9 | Pull request | `/create-pr` | Draft PR to `main` |

## 1. Look before starting

```bash
ls docs/plans/
```

Parse each plan's marker — `<!-- claude-plan step=N status=... -->`.

**If a plan is already `active`**: report its slug, title, step and next step, then stop and
ask whether to resume it or park it. Two active plans make the hooks guess which state the
repo is in, so never create a second one. Park with `status=parked`.

**If the request is cosmetic** — a rename, a docstring reword, formatting, plot styling —
do not start a pipeline. Say so and switch to `/small-change`. The test is in `CLAUDE.md`:
adding or removing a file, changing a public signature, changing behavior or needing a new
test all mean the pipeline; nothing else does.

## 2. Create the plan file

Pick a slug: kebab-case, a few words, what the feature *is* rather than what it does to the
repo — `csv-export`, not `add-csv-module`.

```bash
cp docs/plans/TEMPLATE.md docs/plans/<slug>.md
```

In the copy: set the title, fill the Slug and Started rows, delete the quoted instructions,
and set the marker to

```
<!-- claude-plan step=1 status=active -->
```

Leave the Branch row as a placeholder. Step 3 creates the branch and fills it in — naming
it now would guess at a scope that step 1 has not settled yet.

## 3. Hand off to step 1

Invoke `/conceptualize` and let it run. It is a conversation, and it is where the shape of
the feature actually gets decided — do not shortcut it by writing a concept unilaterally
and asking for a yes.

## Resuming

`/feature` with no argument, or in a fresh session, reports the state and stops. Any step
can also be re-entered directly by its own skill: `/verify` after a fix, `/test` to add a
case, `/concept-check` after a round of changes. Re-running a step is normal and cheap.
Skipping one is neither.
