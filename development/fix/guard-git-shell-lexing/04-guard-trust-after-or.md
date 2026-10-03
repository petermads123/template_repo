# The git guard does not trust a switch that `||` may skip

<!-- claude-plan step=2 status=active -->

| Field | Value |
|---|---|
| Feature | `fix/guard-git-shell-lexing` |
| Round | `4` |
| Branch | `fix/guard-git-shell-lexing` |
| Started | `2026-10-03` |

## Progress

| # | Step | Skill | Runs | Status |
|---|---|---|---|---|
| 1 | Conceptualize | `/conceptualize` | with the user | done |
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

### Defect

| Field | Value |
|---|---|
| Observed | `violation("git status \|\| git checkout -b x && git commit -m x", "main")` returns `""` (allowed). In bash with `git` shadowed by a function keeping HEAD in a file, the command prints `COMMIT on main`. |
| Expected | Refused with the commit reason. `violation`'s docstring and STRUCTURE.md say a switch replaces the set of branches only across `&&`, and a commit is refused when `main` is any branch it could land on (round 2, A-criteria on the set-of-branches rule). |
| Reproduction | `violation("git status \|\| git checkout -b x && git commit -m x", "main")` → `""`; bash → `COMMIT on main`. Also, all allowed and all commit or push on `main` in bash: `git rev-parse --verify feat/x \|\| git checkout -b feat/x && git commit -m x` (feat/x exists); `git checkout main \|\| git checkout -b x && git commit -m x` from `feat/y`; `true \|\| git checkout -b x && git push origin HEAD`; `true \|\| echo a \| git checkout -b x && git commit -m x`; `true \|\| git checkout -b x "$(echo)" && git commit -m x`; `false \|\| true \|\| git checkout -b x && git commit -m x`; `true \|\|` newline `git checkout -b x && git commit -m x`; `if true \|\| git checkout -b x && git commit -m x; then :; fi`; the same inside `echo "$(...)"`. |
| Root cause | `.claude/hooks/guard_git.py:1672`, `ok = here \| {target} if unsure else {target}`: `ok` is the set of branches HEAD could be on if every command of the current `&&` chain succeeded, but a switch replaces it with `{target}` even when its pipeline is the right operand of `\|\|`. bash reads `a \|\| b && c` as `(a \|\| b) && c`, so `c` runs when `a` succeeded and the switch never ran. Line 1638 only reads the wrong value (the site). Sibling: `guard_git.py:1622` clears round 3's `!`/`coproc` `negating` state on a list end at any depth, so a `;`, `&&` or `\|\|` inside a substitution in the switch command ends the negation of the outer pipeline. |
| Introduced by | Older than this branch: `main`'s guard has the same flaw in its earlier form (`effective = target` after any switch, reset only on a non-`&&` separator). The set-of-branches form came in round 2 (3df5e1e), the `negating` state in round 3 (6994e72). |
| Class | (1) A switch in an `\|\|` operand followed by `&&`, in every form: through later pipeline stages (`\|`, `\|&`); after wrappers, assignments, redirections and reserved words; with substitutions in the switch command; chained `\|\|`; an `\|\|` after an `&&` chain; `coproc true \|\|`; a heredoc on the switch; an `&&` ending a line; the commit later in the chain after more `&&` segments; the commit inside a substitution; the whole inside `{ }`, `$( )` or an `if` condition; a named switch without `-b` (`git checkout main \|\| git checkout feat/x && git commit -m x` from `feat/y`); a push of `HEAD`. (2) The `negating` depth leak: `! true \| git checkout -b feat/x "$(true && true)" && git commit -m x` on `main` is allowed and bash commits on `main` (also `"$(true; true)"` and backticks); a new `\|\|` state built the same way would inherit it (`true \|\| git checkout -b x "$(true && true)" && git commit -m x`). Already refused, by `_join` reading `; } &&` and `) &&` as `;`: a group, subshell or compound command in the `\|\|` operand; `true \|\| ! git checkout -b x && ...` by the `unsure` branch. Checked and clean: `&`, non-last pipeline stages, `case`, `if`, loops, functions, groups. |
| Blast radius | Only `_judge`, behind `violation`; the caller is `guard_git.main`, the hook. No test pins `\|\| <switch> && <commit>`. The comment at `guard_git.py:1603–1605`, the module docstring and STRUCTURE.md's guard paragraph state the invariant the code breaks and are updated with the fix. Nothing depends on the wrong answer. |
| Scope | `the class`, plus the `negating` depth leak — the user's choice: the same mistake with the same fix shape, and a `\|\|` fix written like the `!` rule would inherit the leak. |

Critique — the `diagnosis-critic`'s findings and what was done with each (verdict: cause confirmed, class incomplete):

1. **The `negating` state clears at any depth (line 1622), an existing bypass and a trap for the new rule.** Applied: added to the class and taken into scope (A3).
2. **Eleven shapes missing from the class.** Applied: listed in the Class row and in A2.
3. **The operand's extent must be measured from the `||`'s own depth and group level, not "any group since".** Applied: `true || { git checkout -b x && git commit -m x; }` stays allowed (A4) while `{ true || git checkout -b x && git commit -m x; }` is refused (A2).
4. **The already-refused cases are refused by the separator join, not by any `||` logic.** Applied: recorded in the Class row; no new rule for groups or compound commands.
5. **Doc blast radius (comment at 1603–1605, STRUCTURE.md).** Applied: Blast radius row.

### What this is

A branch switch is trusted by the `&&` after it only when it is certain to have run. A switch
in the right operand of an `||` — which runs only when the left side failed — adds its branch
to what the next `&&` can trust instead of replacing it, so the branch the command started on
stays in play; the operand runs from the `||` through its pipeline and substitutions to the
next `&&`, `;`, newline or `&` at the `||`'s own depth and group level. That keeps the
create-or-switch idiom (`git checkout -b feat/x || git checkout feat/x && git commit`)
allowed, because both sides land on `feat/x`. Round 3's `!`/`coproc` rule is made to end only
at a list end at its own depth, so a `;`, `&&` or `||` inside a `$( )` in the same command no
longer cancels it. The fix removes the replacement at `guard_git.py:1672` for `||` operands and
the any-depth clear at `guard_git.py:1622`.

### Why it is worth building

See the Defect block: a silent commit to `main` in ordinary shell, against the rule
`CLAUDE.md` sets and the guard exists to enforce.

### Inputs and outputs

Unchanged: `violation(command, branch)` takes the command line and the checked-out branch and
returns a refusal reason or `""`. Only which commands are refused changes.

### How it connects to the rest of the repo

Changes `_judge` in `.claude/hooks/guard_git.py`; `guard_git.main` (the `PreToolUse` hook)
calls it through `violation`. Tests in `tests/test_guard_git.py`; prose in the module
docstring and STRUCTURE.md's guard section. No other hook touches it.

### Explicitly out of scope

Recorded in round 3's section 8, not in `DEVELOPMENT.md` (the user's instruction):

- a redirection on a compound command, which bash runs before its body;
- a switch target that is a variable (`git checkout "$b"`);
- PowerShell glued braces (`if($?){git commit}`) and `ForEach-Object`/`%` pipelines;
- a `coproc` or `&` loop racing a foreground switch;
- wrappers not stepped over (`command`, `exec`, `builtin`, `eval`, `xargs`);
- modelling bash's `if`/`while` logic exactly (round 3's play-safe choice stands).

### Acceptance criteria

| # | The finished feature... |
|---|---|
| A1 | Given `git status \|\| git checkout -b x && git commit -m x` with `main` checked out, `violation` refuses with the commit reason rather than returning `""`. |
| A2 | Every other `\|\|`-operand form in the Class row is refused with the commit (or push) reason on `main`, or from `feat/y` for the named switch: a later pipeline stage (`\|`, `\|&`); a wrapper, assignment, redirection or reserved word before the switch; a substitution in the switch command; chained `\|\|`; `\|\|` after an `&&` chain; `coproc true \|\|`; a heredoc on the switch; `&&` ending a line; the commit after further `&&` segments; the commit inside a `$( )`; the whole inside `{ }`, `$( )` or an `if` condition; `true \|\| git checkout -b x && git push origin HEAD`; `git checkout main \|\| git checkout feat/x && git commit -m x` from `feat/y`. |
| A3 | `! true \| git checkout -b feat/x "$(true && true)" && git commit -m x` is refused on `main`, as are its `"$(true; true)"` and backtick variants, and `true \|\| git checkout -b x "$(true && true)" && git commit -m x`. |
| A4 | These stay allowed on `main`: `git checkout -b feat/x \|\| git checkout feat/x && git commit -m x`; `git fetch \|\| true && git checkout -b x && git commit -m x`; `true \|\| false && git checkout -b x && git commit -m x`; `true \|\| { git checkout -b x && git commit -m x; }`; `git checkout -b feat/x && ! git diff --cached --quiet && git commit -m x`. |
| A5 | Nothing else changed: the existing 1042 tests pass unmodified and rounds 1–3's criteria still hold; a differential against the guard at 43eeea3 over the suite's commands, with `\|\|` and `!` variants, sends every differing row to bash with `git` shadowed — the oracle first shown live by a plain commit landing on `main` — and every difference involves `\|\|` or the `negating` leak, with the oracle agreeing or the new refusal play-safe, and zero rows where the guard allows a commit or push that bash lands on `main`. |

### Open questions

None.

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
