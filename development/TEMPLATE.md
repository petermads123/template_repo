# <Feature title>

<!-- claude-plan step=1 status=template -->

> Copy this file to `development/<branch>/NN-<round-slug>.md`, change `status=template`
> to `status=active`, and fill it in as the pipeline runs. Delete these quoted
> instructions from your copy.
>
> One folder per branch, one numbered file per round. Round 1 is `01-<topic>.md`; a
> recommendation taken up in step 8, or a review comment at step 10, becomes
> `02-<its-own-slug>.md` in the same folder, and so on. Every round of a feature shares
> one branch and one pull request.
>
> The marker line above is the workflow's state, read by `.claude/hooks/plan_state.py`:
> `step` is the step currently in progress, `status` is `active`, `done`, `parked` or
> `template`. Keep exactly one file `active` across the whole repo — when a new round
> opens, the round before it becomes `done`, and step 9 marks the newest round `done` in
> the commit that opens the pull request. The stop gate is advisory through step 7, where
> the build carries its own gates and must be able to halt on a red tree, and blocking
> from step 8.
>
> Every step commits and pushes this file with what it produced, so the branch is always
> the state and any session can resume from it.

| Field | Value |
|---|---|
| Feature | `<branch>` (the folder) |
| Round | `<N>` |
| Branch | `<type>/<kebab-case-topic>` |
| Started | `<YYYY-MM-DD>` |

## Progress

| # | Step | Skill | Runs | Status |
|---|---|---|---|---|
| 1 | Conceptualize | `/conceptualize` | with the user | pending |
| 2 | Plan | `/plan` | with the user | pending |
| 3 | Implement | `/implement` | in `/build` | pending |
| 4 | Verify | `/verify` | in `/build` | pending |
| 5 | Test | `/test` | in `/build` | pending |
| 6 | Concept check | `/concept-check` | in `/build` | pending |
| 7 | Ship | `/ship` | in `/build` | pending |
| 8 | Recommend | `/recommend` | with the user | pending |
| 9 | Pull request | `/create-pr` | with the user | pending |
| 10 | Review | `/watch-pr` | on the pull request | pending |

Statuses: `pending`, `in progress`, `done`.

## Builds on

> Round 1 writes "Nothing — this is the first round." and moves on. A later round fills
> this in before step 1 starts, because its concept is a change to something that already
> exists and is already on the branch.

| Round | File | What it delivered |
|---|---|---|

This round came from recommendation `<R#>` of round `<N>`, which read:

> <the recommendation, quoted from that round's section 8>

What is already on the branch that this round must not break:

---

## 1. Concept

> Written in step 1, agreed with the user before step 2 starts. Prose, not code. Steps 3
> to 7 run without the user, and the one thing that stops them is a finding that would
> change this section — so what is not decided here is decided by a halt.

### What this is

### Why it is worth building

### Inputs and outputs

### How it connects to the rest of the repo

Which existing modules it calls, which call it, what it does not touch.

### Explicitly out of scope

### Acceptance criteria

> Numbered, observable, and phrased so that step 6 can mark each one met or not met.
> These are the contract. Step 2 plans against them, step 5 tests them, step 6 audits
> against them. If a criterion cannot be observed from outside the code, rewrite it.

| # | The finished feature... |
|---|---|
| A1 | |
| A2 | |

### Open questions

> Must be empty before step 2 begins. An unanswered question here is a decision being
> made by accident later — and nobody is watching when it happens.

---

## 2. Plan

> Written in step 2, accepted by the user before step 3 starts. Concrete enough that
> step 3 is transcription, not invention.

### Approach

One paragraph on the chosen approach, and one on what was rejected and why.

### Modules

| Path | New or changed | Purpose |
|---|---|---|

### Public API

> Every public class and function, with its full signature as it will be written.
> `Covers` links back to the acceptance criteria above.

| Signature | Module | Purpose | Covers |
|---|---|---|---|

### Implementation guide

Ordered. Each entry small enough to finish and check.

1.
2.

### Test intents

> High-level: what a test must prove, not how it is written. Step 5 turns each of these
> into concrete cases, including the edge cases.

| # | Must prove | Covers |
|---|---|---|
| T1 | | |

### Risks

What could make this harder than it looks, and what the build should do if it does —
including whether it should halt.

---

## 3. Implementation notes

> Written in step 3. Only deviations from the plan above, each with its reason. "Built as
> planned" is a complete and good entry.

---

## 4. Verification log

> Written in step 4: the static half. Command output, not a summary of it.

| Check | Result |
|---|---|
| `ruff check .` | |
| `ruff format --check .` | |
| `mypy` | |
| Plan completeness | every signature in the Public API table exists as written |
| `STRUCTURE.md` | in sync |
| `python -m <package>.<module>` | |

---

## 5. Test log

> Written in step 5: the dynamic half.

| Intent | Test names | Result |
|---|---|---|

Edge cases considered and deliberately skipped, with reasons:

---

## 6. Concept check

> Written in step 6, against section 1 — not against section 2. The question is whether
> the thing built is the thing agreed, not whether it matches the plan.

| # | Criterion | Met | Evidence |
|---|---|---|---|
| A1 | | | |

Drift found, and what was done about it:

### Earlier rounds still hold

> Later rounds only. Re-check every acceptance criterion from every earlier round in this
> folder: this round changed code they depend on, and their tests passing is necessary but
> not sufficient — a criterion can be satisfied by tests that no longer describe what the
> feature does.

| Round | # | Criterion | Still met | Evidence |
|---|---|---|---|---|

---

## 7. Ship log

| Field | Value |
|---|---|
| Commits | |
| Pushed to | |

---

## 8. Recommendations

> Written in step 8. Follow-up work this change makes possible or desirable. Not bugs —
> a bug found here goes back through `/build` before the pull request.

| # | Recommendation | Why it helps | Effort | Decision |
|---|---|---|---|---|
| R1 | | | | |

Decisions: `deferred`, `rejected`, or `next round` — a new numbered file in this folder,
taken back through steps 1 to 7 on the same branch.

---

## 9. Pull request

> Written in step 9, in the commit that opens the pull request — so the URL is not known
> yet and the pull request is found from the branch. The review itself is recorded on the
> pull request thread, not here: this file is `done` from step 9 on.

| Field | Value |
|---|---|
| URL | opened by step 9 — see the branch's pull request |
| Opened as | ready for review |

---

## Halted

> Only if the build stopped. Written by `/build`: the step, the reason verbatim from the
> step that halted, the question for the user — and, once answered, the answer and what
> changed because of it. Never deleted; it is the record of where the plan was thinner
> than the code needed.
