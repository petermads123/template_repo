# <Feature title>

<!-- claude-plan step=1 status=template -->

> Copy this file to `docs/plans/<slug>.md`, change `status=template` to `status=active`,
> and fill it in as the pipeline runs. Delete these quoted instructions from your copy.
>
> The marker line above is the workflow's state, read by `.claude/hooks/plan_state.py`:
> `step` is the step currently in progress, `status` is `active`, `done`, `parked` or
> `template`. Keep exactly one plan `active`. The stop gate is advisory through step 3
> and blocking from step 4, so this marker decides how strict the repo is being.

| Field | Value |
|---|---|
| Slug | `<slug>` |
| Branch | `<type>/<kebab-case-topic>` |
| Started | `<YYYY-MM-DD>` |

## Progress

| # | Step | Skill | Status |
|---|---|---|---|
| 1 | Conceptualize | `/conceptualize` | pending |
| 2 | Plan | `/plan` | pending |
| 3 | Implement | `/implement` | pending |
| 4 | Verify | `/verify` | pending |
| 5 | Test | `/test` | pending |
| 6 | Concept check | `/concept-check` | pending |
| 7 | Ship | `/ship` | pending |
| 8 | Recommend | `/recommend` | pending |
| 9 | Pull request | `/create-pr` | pending |

Statuses: `pending`, `in progress`, `done`.

---

## 1. Concept

> Written in step 1, agreed with the user before step 2 starts. Prose, not code.

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
> made by accident later.

---

## 2. Plan

> Written in step 2. Concrete enough that step 3 is transcription, not invention.

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

What could make this harder than it looks, and the plan if it does.

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

---

## 7. Ship log

| Field | Value |
|---|---|
| Commits | |
| Pushed to | |

---

## 8. Recommendations

> Written in step 8. Follow-up work this change makes possible or desirable. Not bugs —
> a bug found here goes back to step 3 before shipping.

| # | Recommendation | Why it helps | Effort | Decision |
|---|---|---|---|---|
| R1 | | | | |

Decisions: `deferred`, `rejected`, or `round 2` (taken back through steps 1 to 7).

---

## 9. Pull request

| Field | Value |
|---|---|
| URL | |
| Opened as | draft |

---

## Rounds

> When a recommendation is taken up, append a new round here rather than editing the
> sections above. The original concept stays readable, and step 6 can still check the
> finished work against what was first agreed.

### Round 2 — <title>

Concept, plan and outcome for the follow-up, in the same shape as above.
