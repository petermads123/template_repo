# The git guard keeps an `||` or `!` scope across a compound command

<!-- claude-plan step=2 status=active -->

| Field | Value |
|---|---|
| Feature | `fix/guard-git-shell-lexing` |
| Round | `6` |
| Branch | `fix/guard-git-shell-lexing` |
| Started | `2026-10-04` |

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
| 2 | `02-guard-substitutions-in-words.md` | Every command substitution extracted and judged before the command that contains it; a commit or push refused when `main` is any branch it could land on; heredocs in a substitution closing on `EOF)`; funsub plays safe; the guard never crashes open. |
| 3 | `03-guard-reserved-words.md` | Shell reserved words stepped over to find git; a `!`/`coproc`-led switch only widens `&&` trust; a switch anywhere in a loop counts for the whole loop; leaders read as arguments open no `case`. |
| 4 | `04-guard-trust-after-or.md` | After an `\|\|` operand, `&&` trusts the union of both sides; the `!`/`coproc` scope keyed by substitution depth and group level; `_segments` hands out raw operator runs with their depth. |
| 5 | `05-guard-quoted-operators.md` | A quoted word is never an operator, leader, assignment or redirection; the command is read both as bash and as PowerShell where they differ (an escaped operator, a bare brace argument, a carriage return), refusing if either reading refuses. 1613 tests, 0 bypass rows in a 22,908-row differential against bash. |

This round came from recommendation `R1` of round 5, which read:

> **Count reserved-word compounds (`if…fi`, `case…esac`, `while`/`until`/`for`/`select…done`) and `[[ … ]]` as levels in the key that `||` operands and `!`/`coproc` scopes use, and keep a `case` pattern's `)` out of the group count.** — A terminator inside such a compound ends a scope opened outside it, so the switch piped after it is trusted. Confirmed in bash 5.2 with `git` shadowed, guard allows and bash prints `COMMIT on main`: `true || if true; then echo; fi | git checkout -b x && git commit -m x`, and the same with `case a in a) :;; esac`, `while false; do :; done`, `until true; do :; done`, `for i in 1; do :; done`, `if { true; }; then echo; fi` (`{ true; }`, `(true; true)` and `f() { :; }` there are refused). Traced by the `defect-class` reader: `true || [[ a && b ]] | …`, `true || { case a in a) :;; esac; } | …`, and the `!` forms. Round 4's own operand rule (`_walk_run` raises the nest only on `(`/`{`); 8972524 allows them too. Effort: large.

Round 5's step 8 reader also proposed a committed pure-Python container matrix (round 5, section 8
notes): each scope opener × each construct holding a list terminator, bare and in `{ }`, asserted
refused on `main` — a natural part of this round.

What is already on the branch that this round must not break: every acceptance criterion of
rounds 1 to 5 (step 6 re-checks them), the 1613 guard tests, and in particular the `||` operand
union, the `!` scope, loop widening, both readings and quoted words.

---|---|---|

This round came from recommendation `<R#>` of round `<N>`, which read:

> <the recommendation, quoted from that round's section 8>

What is already on the branch that this round must not break:

---

## 1. Concept

### Defect

| Field | Value |
|---|---|
| Observed | `violation("true \|\| if true; then echo; fi \| git checkout -b x && git commit -m x", "main")` returns `""` (allowed). In bash 5.2 with `git` shadowed by a function keeping HEAD in a file (`PATH=/usr/bin:/bin`, the oracle shown live by a plain commit), it prints `COMMIT on main`. |
| Expected | Refused with the commit reason. Round 4's criteria and STRUCTURE.md promise an `\|\|` operand runs "to the next `&&`, `;`, `&`, newline or `case` clause terminator at its own substitution depth and group level", and a `!` scope likewise; a `;` inside a compound command is not at the operand's level. |
| Reproduction | The call above. Also allowed, all `COMMIT on main` in bash (scratchpad `r6_class.py`, 18 rows): each of `if true; then echo; fi`, `if { true; }; then echo; fi`, `case a in a) :;; esac`, `case a in (a) :;; esac`, `while false; do :; done`, `until true; do :; done`, `for i in 1; do :; done`, `select i in; do :; done`, `[[ a && b ]]` and `{ case a in a) :;; esac; }` in `true \|\| <C> \| git checkout -b x && git commit -m x` and in `! <C> \| git checkout -b feat/x && git commit -m x` (feat/x exists). Refused correctly today: `{ true; }`, `(true; true)`, `{ if true; then :; fi; }`, `(( 1 && 1 ))`, `f() { :; }`, `[[ a \|\| b ]]`. |
| Root cause | `.claude/hooks/guard_git.py:1930–1935` (`_walk_run`): the per-level group count `nest` moves only on the `(`/`{` and `)`/`}` operators of a segment's run. Reserved-word compounds (`if…fi`, `case…esac`, `while`/`until`/`for`/`select…done`) and `[[ … ]]` sit in segment tokens, not in runs, so the walk opens no level for them; a `;`, `;;`, newline or `&&` inside one lands on the same (depth, group) key as an `\|\|` operand or `!` scope opened outside it, and `close()` ends that scope there. A `case` pattern's `)` reaches the run as `)` and lowers `nest` (`{ case a in a) :;; esac; }`, `( case … )`). Site: `_judge`'s switch update (`ok = {target}`, `:2046`), which then trusts the switch piped after the compound. |
| Introduced by | Round 4 (1a498a8 and its step 5 changes), which introduced the keyed operand and scope; 43eeea3 and 8972524 allow these forms too. Not a regression of a working guard: before round 4 every `\|\|` form was allowed. |
| Class | Every reserved-word compound and `[[ ]]` anywhere inside an `\|\|` operand or a `!` scope: as the first command, as a later pipeline stage (`true \|\| git status \| case … esac \| …`), after a leader (`time if …`), with a redirection after the closer (`fi 2>/dev/null \|`), before `\|&`, written across lines (`if true\nthen :\nfi \| …`), inside `$( )`, nested; a `case` pattern's `)` inside `{ }` or `( )`. Not in the class (refused, by structure): function definitions, `(( && ))` (its `((` arrives as two `(`), `[[ a ]]` with no operator inside. Same shape elsewhere: round 3's `_loop_ranges` pairs loop words with `done` but has no `if`/`case`/`[[` pairing — a pattern to copy, not a range to reuse. PowerShell's reading runs the same walk but braces are groups there; a bypass needs both readings to allow, so the bash reading is the one to fix. |
| Blast radius | `_walk_run` and `_judge` only. Pins that constrain the fix: `tests/test_guard_git.py:3778` (`test_violation_ends_a_scope_at_a_case_clause_terminator`: `;;`, `;&`, `;;&` still end an `\|\|` or `!` scope opened inside a clause body) and the `RUN_PINS` row `"case x in a) b ;; c) d ;; esac"` (the pattern `)` pinned as a run operator; a fix in how `_walk_run` reads it does not flip it, a fix in `_segments` would). Round 3's "a compound command ends an `&&` chain's trust" over-refusals come from `_judge`'s `ok = set(here)` on the `fi`/`done` segment, not from `_walk_run`, so a fix confined to the scope keys leaves them as they are. Nothing depends on the wrong answer. |
| Scope | `the class`, plus a committed pure-Python container matrix test — the user's choice: the same cause in every position, and a matrix that needs no bash (so it runs on the Windows targets) is what would have caught this before it shipped. |

Critique — the `diagnosis-critic`'s findings and what was done with each (verdict: cause confirmed, class incomplete):

1. **The class is wider: a later pipeline stage, `\|&`, a leader, a redirection after the closer, newline-written forms, inside `$( )`, `( case … )`, and the `!` form in a group.** Applied: Class row and A2/A3.
2. **Two pins constrain the fix (`:3778`, the `RUN_PINS` case row); round 3's compound over-refusals come from `_judge`, not `_walk_run`.** Applied: Blast radius and A4.
3. **`_loop_ranges` is a pattern, not a range to reuse; `if a && b; then` conditions do not bypass; PowerShell needs no change; `coproc <C> \| …` lands on the switch target in bash.** Applied: Class row and A4.

### What this is

A compound command written with reserved words — `if … fi`, `case … esac`, `while`/`until`/`for`/
`select … done` — and `[[ … ]]` become groups of their own in the key that `||` operands and
`!`/`coproc` scopes use, exactly as `{ … }` and `( … )` already are, so a terminator inside one no
longer ends a scope opened outside it, and a `case` pattern's `)` no longer counts as a group close.
The fix removes the cause at `_walk_run` (`:1930–1935`), where the group level moves only on
brackets. A committed matrix of scope openers against every construct that can hold a list
terminator guards the whole family without needing bash.

### Why it is worth building

See the Defect block: a silent commit to `main` in ordinary shell, against the rule `CLAUDE.md`
sets and the guard exists to enforce.

### Inputs and outputs

Unchanged: `violation(command, branch)` takes the command line and the checked-out branch and
returns a refusal reason or `""`. Only which commands are refused changes.

### How it connects to the rest of the repo

Changes `_walk_run` and the run walk in `_judge` (and, if the plan needs it, what `_segments`
records) in `.claude/hooks/guard_git.py`; `guard_git.main` (the `PreToolUse` hook) calls it through
`violation`. Tests in `tests/test_guard_git.py`; prose in the module docstring and STRUCTURE.md's
guard section. No other hook touches it.

### Explicitly out of scope

Recorded in the plan file, not in `DEVELOPMENT.md` (the user's instruction):

- modelling bash's actual `if`/`while` logic (round 3's play-safe choice stands);
- the recorded misses of rounds 1–5 (hex-escape and split-quote subcommand, lone `'` in a quoted
  `${ }`, variable switch target, compound redirection order, PowerShell glued braces and
  `ForEach-Object`, the `coproc`/`&` loop race, unlisted wrappers, functions judged where defined);
- the over-refusal of `[[ a || b ]] | …`, which only refuses more.

### Acceptance criteria

| # | The finished feature... |
|---|---|
| A1 | Given `true \|\| if true; then echo; fi \| git checkout -b x && git commit -m x` with `main` checked out, `violation` refuses with the commit reason rather than returning `""`. |
| A2 | Every reserved-word compound and `[[ && ]]` inside an `\|\|` operand is refused on `main` in every position: first, a later pipeline stage, after `time`, with a redirection after the closer, before `\|&`, written across lines, and inside `$( )` — covering `if … fi` (also `if { true; }; then`), `case … esac` with `a)` and `(a)` patterns, `while`, `until`, `for` and `select … done`, and `[[ a && b ]]`. |
| A3 | The same compounds after `!` (`! <C> \| git checkout -b feat/x && git commit -m x`, feat/x existing) are refused on `main`; `{ case a in a) :;; esac; } \| …` and `( case a in a) :;; esac ) \| …` after `\|\|` or `!` are refused. |
| A4 | These keep their outcome: create-or-switch allowed; `true \|\| { git checkout -b x && git commit -m x; }` allowed; `;;`, `;&`, `;;&` still end an `\|\|` or `!` scope opened inside a clause body (`:3778`); round 3's compound `&&` over-refusals (`git checkout -b feat/x && if true; then :; fi && git commit -m x`, `&& for … done &&`) still refused; the `coproc <C> \| …` forms unchanged; `(( 1 && 1 ))`, `{ true; }`, `(true; true)` and function definitions still refused. |
| A5 | A committed test, pure Python with no bash, crosses each scope opener (`true \|\|`, `false \|\|`, `!`) with each construct that holds a list terminator — `{ ; }`, `( ; )`, `$( ; )`, backticks, `if … fi`, `case … esac` with `a)` and `(a)` patterns, `while`/`until`/`for`/`select … done`, `[[ && ]]`, `(( && ))`, `f() { ; }` — bare and wrapped in `{ }`, and asserts `<opener> <construct> \| git checkout -b x && git commit -m x` is refused on `main` and allowed from another branch. |
| A6 | Nothing else changed: the existing 1613 tests pass unmodified and rounds 1–5's criteria still hold; a differential against the guard at 6f05520 over the suite's commands with compounds inserted sends every differing row to bash with `git` shadowed — the oracle first shown live by a plain commit landing on `main` — and every difference involves a reserved-word compound or `[[ ]]`, with the oracle agreeing or the new refusal play-safe, and zero rows where the new guard allows a commit or push that bash lands on `main`. |

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
