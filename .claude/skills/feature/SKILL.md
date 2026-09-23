---
name: feature
description: Start or resume the ten-step implementation pipeline for a feature, module, behavior change or anything needing a design decision. Creates the plan file that carries the work from concept to pull request, or reports which step an in-flight plan is on. Use for any change that is not purely cosmetic, whether the user names the skill or just describes the work in prose.
argument-hint: [what to build]
model: opus
effort: xhigh
---

# Feature pipeline

Ten steps, one plan folder per branch, three places where the user decides. This skill is
the entry point for a feature: it either resumes what is in flight or starts something new.
It does not do the work. A defect enters the same pipeline through `/fix`, which diagnoses
it first.

## The pipeline

| # | Step | Skill | Produces | Waits for |
|---|---|---|---|---|
| 1 | Conceptualize | `/conceptualize` | Agreed concept, acceptance criteria, branch | the user |
| 2 | Plan | `/plan` | Modules, signatures, implementation guide, test intents | the user |
| 3 | Implement | `/build` → `/implement` | Working code | — |
| 4 | Verify | `/build` → `/verify` | ruff, mypy, plan completeness, STRUCTURE.md | — |
| 5 | Test | `/build` → `/test` | Edge-case suite, pytest green | — |
| 6 | Concept check | `/build` → `/concept-check` | Audit against step 1, not step 2 | — |
| 7 | Ship | `/build` → `/ship` | Round complete on the branch | — |
| 8 | Recommend | `/recommend` | Ranked follow-ups | the user |
| 9 | Pull request | `/create-pr` | PR to `main`, ready for review | the user, before publishing |
| 10 | Review | `/watch-pr` | Hourly check until the PR merges or closes | — |

Steps 3 to 7 are one block: `/build` runs them unattended, each in a subagent on its own
model, and halts only for something that would change the concept or a gate that fails
twice the same way. Every step commits and pushes, so the branch and its plan folder are
always the state, and any session can resume from them.

## 1. Look before starting

```bash
ls development/*/*/
```

One folder per branch, one numbered file per round inside it. Parse each file's marker —
`<!-- claude-plan step=N status=... -->`.

**If a plan is already `active`**: report its folder, title, step and what happens next,
then stop and ask whether to resume it or park it. Two active plans make the hooks guess
which state the repo is in, so never create a second one. Park with `status=parked`.

**If no plan is active**, also say what the most recent `done` round was and whether its
section 9 names a pull request — a pull request the user has not merged yet is worth a
`/watch-pr`, and nothing else will mention it.

**If the request is cosmetic** — a rename, a docstring reword, formatting, plot styling —
do not start a pipeline. Say so and switch to `/small-change`. The test is in `CLAUDE.md`:
adding or removing a file, changing a public signature, changing behavior or needing a new
test all mean the pipeline; nothing else does.

**If the request is a defect** — something that exists behaves wrongly — do not start here
either. Say so and switch to `/fix`: it reproduces the symptom and finds the cause before
step 1 opens, and it comes back here on its own if the diagnosis says it is not a bug.

## 2. Hand off to step 1

Invoke `/conceptualize` with the request. It has the conversation, and at its close it
names the branch, creates the plan folder and the first round file, and commits. Nothing is
created here, because the folder is named for the branch and the branch is not chosen
until the scope is — naming it now would guess at a scope step 1 has not settled yet.

Do not shortcut step 1 by writing a concept unilaterally and asking for a yes. It is where
the shape of the feature actually gets decided.

## Resuming

`/feature` with no argument, or in a fresh session, reports the state and stops — including
which round of which branch is in flight, what the earlier rounds delivered, and whether a
build halted and on what. The step's own skill re-enters it: `/plan` to revise a plan,
`/build` to resume a halted build, `/recommend` to decide the list, `/watch-pr` to resume a
watch. Re-running a step is normal and cheap. Skipping one is neither.
