# Git guard: recognising the command

<!-- claude-plan step=1 status=active -->

| Field | Value |
|---|---|
| Feature | `git-guard` (the folder) |
| Round | `2` |
| Branch | `claude/setup-recommendations-qoyxhf` |
| Started | `2026-09-21` |

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
| 10 | Review | `/watch-pr` | pending |

Statuses: `pending`, `in progress`, `done`.

## Builds on

| Round | File | What it delivered |
|---|---|---|
| 1 | `01-git-guard.md` | Rebuilt `guard_git.py`'s parsing on a quote-aware lexer, so punctuation in a commit message no longer switches the guard off. Judges each invocation against the branch that will be checked out when it runs, trusting a switch only across a run of `&&` and newlines. Refuses unreadable input naming `commit` or `push` on `main`. Gave `guard_git.py`, `plan_state.py` and `stop_gate.py` their first tests — 217 of them. Fixed one placeholder defect in `stop_gate.py`, accepted into that round's concept by the user at step 6. |

This round came from recommendations `R1`, `R2` and `R3` of round `1`, taken together
because they are one idea seen three ways. They read:

> **R1** — Find the git invocation inside a segment instead of assuming `tokens[0]`.
> Closes five of the nine remaining holes at once — `GIT_EDITOR=true git commit`,
> `sudo git push`, backticks, a leading redirection, and `GIT` in capitals on a
> case-insensitive filesystem.
>
> **R2** — Teach `push_targets_main` the refspec shapes it does not know: a push option
> that takes a value is read as the remote, so `git push -o ci.skip origin` slips through
> on `main`; `@` is git's alias for `HEAD` and only the literal is matched;
> `refs/heads/main` is not recognised as `main` when it is a *switch* target.
>
> **R3** — Decide the policy for a switch that cannot be resolved statically.
> `git checkout -` is treated as no switch at all, which is right when `-` goes somewhere
> safe and wrong when it goes to `main`.

What is already on the branch that this round must not break:

- **Round 1's eight acceptance criteria**, A1 to A9, re-checked in this round's step 6 as a
  regression pass. The differential that evidenced A5 — 783 generated commands, 1,566
  comparisons against the module on `main` — is the tool to re-run, not a set of test names
  to re-read.
- **217 tests** across the three hooks. A change that makes the guard stricter will move
  some of them; each move is a decision to record, not a number to restore.
- **The seven public signatures** in `guard_git.py`. R1 in particular pushes on
  `git_subcommand`, whose parameter list is documented in `STRUCTURE.md` and checked
  literally at step 4.
- **The allow-what-cannot-be-parsed posture.** Round 1 narrowed it deliberately: unreadable
  input is refused only when it names `commit` or `push` on `main`. R1 makes the guard
  stricter in a direction that risks false positives — `echo git commit` must not trip it —
  and a guard that blocks legitimate work is the failure its own docstring calls worse.

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
> a bug found here goes back to step 3 before shipping.

| # | Recommendation | Why it helps | Effort | Decision |
|---|---|---|---|---|
| R1 | | | | |

Decisions: `deferred`, `rejected`, or `next round` — a new numbered file in this folder,
taken back through steps 1 to 7 on the same branch.

---

## 9. Pull request

| Field | Value |
|---|---|
| URL | |
| Opened as | ready for review |

---

## 10. Review log

> Written in step 10, one row per review thread. The record of how the pull request got
> from opened to merged — the part nobody can reconstruct from the diff later.
>
> Quiet check-ins are not recorded. Nineteen rows of "nothing had changed" is noise.

| Thread | Who asked for what | Outcome |
|---|---|---|

Outcomes: `fixed and pushed`, `replied, left open`, `round N`, or — for a bot finding —
`dismissed: <reason>`. Every dismissal is also reported to the user, never only recorded here.

### Outcome

| Field | Value |
|---|---|
| Merged or closed | |
| Merge commit | |
| Instructed by | who said to merge, and where |
| Bot findings dismissed | each one, with its reason |
