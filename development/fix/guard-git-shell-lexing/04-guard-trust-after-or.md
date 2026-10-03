# The git guard does not trust a switch that `||` may skip

<!-- claude-plan step=1 status=active -->

| Field | Value |
|---|---|
| Feature | `fix/guard-git-shell-lexing` |
| Round | `4` |
| Branch | `fix/guard-git-shell-lexing` |
| Started | `2026-10-03` |

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

Opened on a bug report — run `/fix` first.

| Round | File | What it delivered |
|---|---|---|
| 1 | `01-guard-git-shell-lexing.md` | A pass in front of `shlex` that reads comments, continuations and heredocs as bash does, with `UNMODELLED_OPENERS` and the play-safe refusal on `main`. |
| 2 | `02-guard-substitutions-in-words.md` | Every command substitution extracted and judged before the command that contains it (`Segment.depth`, `SUBSTITUTED`); a commit or push refused when `main` is any branch it could land on; heredocs in a substitution closing on `EOF)`; funsub plays safe; the guard never crashes open. |
| 3 | `03-guard-reserved-words.md` | Shell reserved words (`if then else elif while until do ! coproc`) stepped over to find git; a switch led by `!` or `coproc`, or inside the pipeline or group they lead, only widens `&&` trust; a switch anywhere in a loop counts for the whole loop (bash and PowerShell); leaders read as arguments open no `case`. 1042 tests, 0 bypass rows in an 8,804-row differential against bash. |

This round came from recommendation `R1` of round 3, which read:

> **A switch after `||` only widens what a later `&&` trusts (`ok = here | {target}`), as a `!`- or `coproc`-led switch already does.** — `a || git checkout -b x && git commit` groups as `(a || b) && c`: when `a` succeeds the switch is skipped and the commit runs on the starting branch. Checked in bash with `git` shadowed: `git rev-parse --verify feat/x || git checkout -b feat/x && git commit -m x` and `git status || git checkout -b x && git commit -m x` commit on `main` and the guard allows both; `git checkout main || git checkout -b x && git commit -m x` from `feat/y` commits on `main`, allowed. A silent commit to `main` in ordinary shell; the trust rule dates from round 1, so it is outside round 3's promise (`defect-class` reader). Effort: small.

What is already on the branch that this round must not break: every acceptance criterion of
rounds 1 to 3 (step 6 re-checks them), the 1042 guard tests, and in particular `&&` trust for
`git checkout -b feat/x && git commit`, the `!`/`coproc` rule, loop widening and substitution
extraction.

---|---|---|

This round came from recommendation `<R#>` of round `<N>`, which read:

> <the recommendation, quoted from that round's section 8>

What is already on the branch that this round must not break:

---

## 1. Concept

> Written in step 1, agreed with the user before step 2 starts. Prose, not code. Steps 3
> to 7 run without the user, and the one thing that stops them is a finding that would
> change this section — so what is not decided here is decided by a halt.

### Defect

> Fix rounds only — a round 1 that `/fix` opened, or a later round opened on a bug report,
> whatever its folder is called. Delete this block on a feature round; its presence, filled,
> is the only thing that marks a round as a fix round to every step after this one. Its
> starting content is the `/fix` diagnosis, agreed with the user like the rest of section 1
> and written to disk with it. The root cause is on the halting line: a build that finds a
> different cause halts rather than fixing what it found.

| Field | Value |
|---|---|
| Observed | What happens, quoted from the reproduction. |
| Expected | What should happen, and what says so — a docstring, a test, an earlier round's criterion. |
| Reproduction | The exact command or call and its output. Step 3 turns this into the first test and runs it red before fixing. |
| Root cause | `file.py:NN`, and the decision on that line that is wrong. |
| Introduced by | The commit, or "older than the history here". |
| Class | Other inputs the same cause breaks, and the same shape elsewhere in the repo. |
| Blast radius | Callers of the cause, tests that will move, anything that depends on the current behaviour. |
| Scope | `this instance` or `the class` — the user's decision, with the reason. What the class holds that is not taken goes under Explicitly out of scope by name. |

Critique — the `diagnosis-critic`'s findings and what was done with each:

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
>
> On a fix round the first criterion is the reproduction passing — "Given <the
> reproduction's input>, <expected> rather than <observed>" — and the last is that nothing
> else changed, phrased so step 6 can evidence it with more than a green suite. If the
> scope is `the class`, each input in the class gets its own row.

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
> planned" is a complete and good entry. On a fix round, also the reproduction test's red
> run, pasted here before the fix was written — step 6 cites it.

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

> Written in step 8. Only follow-ups that are critical and belong to this work, which most
> rounds do not have: replace the table with `None.` when there are none. Lesser ideas are
> one-line notes in `DEVELOPMENT.md`, not rows here. Not bugs in what this round built —
> those go back through `/build` before the pull request. A critical defect outside what
> section 1 promised, such as a class member it put out of scope, is a recommendation here,
> and its round opens through `/fix`.

| # | Recommendation | Why it is critical | Effort | Decision |
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
