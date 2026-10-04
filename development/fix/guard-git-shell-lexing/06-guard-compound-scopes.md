# The git guard keeps an `||` or `!` scope across a compound command

<!-- claude-plan step=9 status=active -->

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
| 2 | Plan | `/plan` | with the user | done |
| 3 | Implement | `/implement` | in `/build` | done |
| 4 | Verify | `/verify` | in `/build` | done |
| 5 | Test | `/test` | in `/build` | done |
| 6 | Concept check | `/concept-check` | in `/build` | done |
| 7 | Ship | `/ship` | in `/build` | done |
| 8 | Recommend | `/recommend` | with the user | done |
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
3. **`_loop_ranges` is a pattern, not a range to reuse; `if a && b; then` conditions do not bypass; PowerShell needs no change; `coproc <C> \| …` lands on the switch target in bash.** Applied: Class row and A4 (A4's `coproc` row later changed at step 2 — see section 2's Critique).

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
| A4 | These keep their outcome: create-or-switch allowed; `true \|\| { git checkout -b x && git commit -m x; }` allowed; `;;`, `;&`, `;;&` still end an `\|\|` or `!` scope opened inside a clause body (`:3778`); round 3's compound `&&` over-refusals (`git checkout -b feat/x && if true; then :; fi && git commit -m x`, `&& for … done &&`) still refused; the `coproc <C> \| …` forms become refused, as `coproc { …; } \| …` already is (changed at step 2, the user's choice: today they are allowed only through the bug this round fixes; bash commits on the switch target there, so this is a play-safe over-refusal); `(( 1 && 1 ))`, `{ true; }`, `(true; true)` and function definitions still refused. |
| A5 | A committed test, pure Python with no bash, crosses each scope opener (`true \|\|`, `false \|\|`, `!`) with each construct that holds a list terminator — `{ ; }`, `( ; )`, `$( ; )`, backticks, `if … fi`, `case … esac` with `a)` and `(a)` patterns, `while`/`until`/`for`/`select … done`, `[[ && ]]`, `(( && ))`, `f() { ; }` — bare and wrapped in `{ }`, and asserts `<opener> <construct> \| git checkout -b x && git commit -m x` is refused on `main` and allowed from another branch. |
| A6 | Nothing else changed: the existing 1613 tests pass unmodified and rounds 1–5's criteria still hold; a differential against the guard at 6f05520 over the suite's commands with compounds inserted sends every differing row to bash with `git` shadowed — the oracle first shown live by a plain commit landing on `main` — and every difference involves a reserved-word compound or `[[ ]]`, with the oracle agreeing or the new refusal play-safe, and zero rows where the new guard allows a commit or push that bash lands on `main`. |

### Open questions

None.

---

## 2. Plan

### Approach

**Chosen: pair the compounds in a pass over the segments, as round 3's `_loop_ranges` pairs loops
with `done`, and let each paired compound raise the same per-level group count that `{` and `(`
raise; read a `case` pattern's parentheses in the run walk.**

1. **Pairing pass.** A new private `_compound_spans(parsed, runs)` walks the invocations with one
   stack per substitution depth and returns, for each invocation index, the compound kinds that open
   there in order (`dict[int, tuple[str, ...]]`, e.g. `("if", "case")`) and how many close there
   (`dict[int, int]`). Openers are the reserved words a shell reads as the start of a
   compound at command position: `if`, `while` and `until` among an invocation's leading words
   (they are leaders, so several can chain: `if while false; do :; done; then`), and `case`, `for`,
   `select` or `[[` as its command word (the word after leaders, `!`, `time` and its options,
   `coproc`, assignments and redirections, exactly where `_walk_prefix` stops). Closers are an
   invocation whose first token is `fi`, `esac` or `done` (a `done` closes when the last operator of its raw run at its own depth is `;`, a newline,
   `&` or the `;;` family — so `do (true); done` and `do { :; }; done` pair — and not when the next
   segment's separator is `)`, a case pattern), and an invocation that holds a `]]`
   token while a `[[` is open at its depth. A `[[` whose `]]` is in the same invocation (`[[ a ]]`,
   `if [[ a ]]; then`) is not reported at all — nothing inside it can split the run. Each closer pops the innermost open compound of its
   kind's family (`fi`↔`if`, `esac`↔`case`, `done`↔`while`/`until`/`for`/`select`, `]]`↔`[[`). An
   opener with no closer at its depth, or a closer that does not match, is ignored — bash rejects
   that command as a syntax error, so it runs nothing, and ignoring it leaves today's reading. A
   quoted keyword carries round 5's quote mark and matches nothing.
2. **The walk.** `_walk_run` stays the only place that touches `nest` and the case keys. `_judge`
   passes it two new private run markers, like round 4's `_CLOSED`, appended to an invocation's run
   after its own operators: `_COMPOUND_OPEN` (one per kind opening there, carrying the kind) and
   `_COMPOUND_CLOSE` (one per compound closing there). `_walk_run` handles both before any
   case-pattern logic: an open raises `nest[level]` (and, for `case`, records the new key as
   expecting a pattern); a close ends every `||` operand and `!` scope keyed above the outer group
   (`ok |= base` for each, exactly as a `)`/`}` close does), drops the case key, and lowers the
   level. So `true || if true; then echo; fi | git checkout -b x && git commit` reads
   its two `;` one level deep, the `fi` closes that level, the `|` and the `&&` are back at the
   operand's key, and the `&&` unions `main` back in.
3. **`case` patterns.** `_walk_run` keeps, for each key that a `case` opened, whether a pattern is
   expected: true at the opener and after each `;;`, `;&` or `;;&` at that key. While a pattern is
   expected, a `(` at that key (the optional leading parenthesis of `(a)`) is not a group, and the
   first `)` at that key ends the pattern instead of closing a group. A real subshell later in the
   clause body (`a) (cd x; y) ;;`) is read as today. The run pins stay as they are: the `)` still
   reaches the run; only how the walk reads it changes.

This removes the cause at `_walk_run` (`:1930–1935`): the group level now moves for every construct
that holds a list, not only for brackets.

**Rejected:**
- **Have `_scan` emit private markers for compound openers, closers and pattern parentheses.** The
  pre-pass knows command position, but it is the most verified and most delicate code in the
  module, and moving the pattern `)` out of the runs flips the `RUN_PINS` case row that section 1
  keeps.
- **Keep every operand open to the end of the command once a compound appears.** It fixes nothing:
  an operand that never closes never unions `main` back in, so the commit is still trusted.
- **A separate pairing for PowerShell.** The pairing runs in both readings on the same tokens, so a
  bash compound pairs in the PowerShell reading too (only refusing more); PowerShell's own `if`,
  `while`, `foreach` take braces, which are already groups, and never meet a `fi`/`done`/`esac`, so
  they go unpaired.

### Modules

| Path | New or changed | Purpose |
|---|---|---|
| `.claude/hooks/guard_git.py` | changed | Private `_compound_spans`; `_judge` raises and lowers `nest` around the compounds; `_walk_run` reads a `case` pattern's parentheses; module docstring |
| `tests/test_guard_git.py` | changed | Round 6 heading: reproduction, the class forms, the pins A4 keeps, and the container matrix |
| `STRUCTURE.md` | changed | Guard section prose (compounds are groups for `\|\|` operands and `!` scopes; `case` patterns) and the round 6 tests paragraph |

### Public API

No public signature or constant changes. `violation`, `segments`, `git_subcommand` and the rest
keep their signatures; `segments` output is unchanged.

| Signature | Module | Purpose | Covers |
|---|---|---|---|
| `violation(command: str, branch: str) -> str` | `guard_git.py` | Unchanged signature. A reserved-word compound or `[[ ]]` inside an `\|\|` operand or `!` scope no longer ends it. | A1–A6 |

### Implementation guide

1. **Reproduction first (fix round).** Add `test_violation_refuses_an_or_switch_after_an_if_compound`
   asserting `violation("true || if true; then echo; fi | git checkout -b x && git commit -m x", "main")`
   starts with the commit reason, under a new heading "round 6: compounds keep an `||` or `!` scope"
   at the end of the file. Run it red, paste the run into section 3, commit before any production
   change. If it is already green, halt.
2. **`_compound_spans(parsed: list[Segment], runs: list[_Run]) -> tuple[dict[int, tuple[str, ...]], dict[int, int]]`.**
   Opens (kinds, in order) and closes per invocation index, as approach item 1. Reuse `_walk_prefix`
   for the leading words and the command word. The `done` rule reads the raw run (approach item 1);
   `_loop_ranges` keeps its own rule unchanged. When a substitution at depth d ends (`_CLOSED`, or
   the depth dropping), the pairing stacks for depth d and deeper are cleared, as `nest` is.
3. **`_judge`.** Compute the spans once per reading, next to `loops`. Append the closes and then
   the opens as markers to each invocation's run before calling `_walk_run` (closes first: a `fi`
   never opens on the same invocation, and a closer's own operators belong inside the compound).
   **Where a `!`/`coproc` scope is keyed:** today line ~2053 adds `(depth, nest[depth])` after the
   walk; with the opens applied, that would key `! if …` inside the `if`. Key it instead at
   `(depth, nest_before + k)`, where `nest_before` is the level before this invocation's opens and
   `k` is the number of `if`/`while`/`until` leaders that come before the first `!` or `coproc` in
   the leader chain (command-word openers — `case`, `for`, `select`, `[[` — come after every leader
   and never count). So `! if true; then …; fi | git checkout …` keys the negation outside the `if`,
   while `if ! git diff --quiet; then git checkout -b feat/x && git commit -m x; fi` keys it inside,
   and the `;` before `then` ends it there as today.
4. **`_walk_run` case state.** Add a private parameter, a dict from case key to "expecting a
   pattern", owned by `_judge` and passed on every call. `_COMPOUND_OPEN` for `case` adds the new
   key, expecting; `_COMPOUND_CLOSE` drops it (it is handled before the pattern logic, so the close
   that follows an `esac` directly after `;;` is never swallowed as a pattern's `)`). Otherwise: a
   `(` at a key expecting a pattern is skipped; the first `)` at such a key clears the expectation
   and is skipped; `;;`, `;&`, `;;&` at a case key set it again (after their usual close). Case keys
   at depth d and deeper are cleared when a substitution at depth d ends.
5. **Docs.** Module docstring and STRUCTURE.md guard section: compounds and `[[ ]]` are groups for
   `||` operands and `!` scopes; a `case` pattern's parentheses are not. The tests entry gets a
   round 6 paragraph.

### Test intents

| # | Must prove | Covers |
|---|---|---|
| T1 | `true \|\| if true; then echo; fi \| git checkout -b x && git commit -m x` on `main` refused with the commit reason: red before, green after | A1 |
| T2 | Every A2 compound in every A2 position after `true \|\|` and `git status \|\|` refused on `main` (each checked in bash with the oracle); the same commands from another branch allowed; a push of `HEAD` in that shape refused; `[[ a ]]`, `if [[ a ]]; then :; fi` and `while [[ a ]]; do :; done` after `true \|\|` still refused (a one-invocation `[[ ]]` leaves the level balanced); loop bodies ending in `( )` and `{ }` (`while false; do (true); done`, `do { :; }; done`) refused; `true \|\| case a in a) :;; esac \| git checkout -b x && git commit -m x` refused with `esac` directly after `;;` | A2 |
| T3 | The A3 `!` forms (feat/x existing) refused on `main`, including `! if …` and `! [[ a && b ]] …`; `{ case a in a) :;; esac; } \| …` and `( case a in a) :;; esac ) \| …` after `\|\|` and `!` refused; `case a in (a) …` patterns; a real subshell inside a clause body still a group | A3 |
| T4 | The A4 list keeps its outcome, including `:3778`'s terminator test and the `RUN_PINS` case row unchanged; `if ! git diff --quiet; then git checkout -b feat/x && git commit -m x; fi` stays allowed on `main` (the `!` keyed inside the `if`); the `coproc <C> \| git checkout -b x && git commit -m x` forms pinned as refused (A4's step 2 change), next to `coproc { true; } \| …`; an unmatched opener or closer (`true \|\| if true; then echo \| …`, a stray `fi`) leaves today's reading | A4 |
| T5 | The container matrix of A5: openers `true \|\|`, `false \|\|`, `!` × constructs `{ ; }`, `( ; )`, `$( ; )`, backticks, `if … fi`, `case … esac` (`a)` and `(a)`), `while`/`until`/`for`/`select … done`, `[[ && ]]`, `(( && ))`, `f() { ; }`, bare and wrapped in `{ }`: `<opener> <construct> \| git checkout -b x && git commit -m x` refused on `main` and allowed from `feat/y`, as one parametrized test with readable ids | A5 |
| T6 | See below. | A6 |

T6 in full. The existing suite passes unmodified; rounds 1–5's criteria are re-checked. The
differential runs at step 6:
- **Baseline.** `git show 6f05520:.claude/hooks/guard_git.py`, loaded from the scratchpad with
  `.claude/hooks` on `sys.path` and registered in `sys.modules`.
- **Corpus.** Every `(command, branch)` the suite passes to `violation`, captured with a scratch
  `-p` plugin.
- **Variants.** Prefixes `true || <C> | `, `! <C> | ` and `true || git status | <C> | ` for a
  representative `<C>` of each compound family, and each command wrapped as the body of
  `if true; then …; fi`; branches `main` and `feat/x`.
- **What goes to bash.** Differing rows only, oracle as in round 5 (shown live first). PowerShell-only
  rows listed, not run.
- **Pass condition.** Every difference involves a reserved-word compound or `[[ ]]`; the oracle
  agrees or the new refusal is play-safe; zero rows where the new guard allows a commit or push
  that bash lands on `main`.

### Risks

- **A closer that is not one.** `done` as an argument, a quoted `fi`, an `esac` inside a pattern:
  the command-position and quote-mark rules decide; if a test shows a word read as a closer where
  bash does not, fix inside the build. An unmatched closer is ignored, so the error direction is
  "today's reading", never a new hole.
- **A level left raised.** Any path that raises without a matching lower leaves later operators one
  level too deep, so an `&&` misses the operand it should close — that is a new bypass, not a safe
  error. The pairing only reports matched compounds and the closes are applied before the opens; if
  a test shows the level unbalanced after a compound, fix inside the build.
- **An existing test changes outcome.** Halt — unless it is a refusal that stays a refusal, or the
  `coproc <C> \| …` change A4 now names.
- **PowerShell.** If a PowerShell test changes outcome, halt.
- **The cause is elsewhere.** If an A1–A3 form stays allowed once compounds raise the level, for a
  reason other than the Root cause row, halt.

### Coverage

- **Every criterion has a Public API entry:** A1–A6 through `violation`.
- **Every criterion has a test intent:** A1→T1, A2→T2, A3→T3, A4→T4, A5→T5, A6→T6.
- **Nothing in the Public API lacks a criterion.** No new public surface.

Re-checked after the critique: the Public API is unchanged; A4 changed at the user's choice and T2,
T3 and T4 gained rows, all still covered.

### Critique

`plan-critic` verdict: accept with changes. Every finding applied:

1. **Where a `!`/`coproc` scope is keyed relative to the raise was undecided; both simple choices
   break something (`! if …` stays a bypass, or `if ! …; then … fi` becomes refused).** Applied:
   guide 3 keys the scope at the level before the opens plus the `if`/`while`/`until` leaders ahead
   of the `!`; T3 and T4 rows.
2. **Done right, the fix refuses the `coproc <C> \| …` forms that A4 said stay unchanged.** Put to
   the user, who accepted the change: A4 amended, T4 pins it, Risks updated.
3. **Counts per index lose the order, so `[[ a ]]` on one invocation could leave the level raised —
   a new bypass.** Applied: the pairing returns kinds in order and skips a one-invocation `[[ ]]`;
   closes apply before opens; T2 rows; a Risks row on unbalanced levels.
4. **The close path is a closure inside `_walk_run`, and a spliced `)` would be swallowed as a case
   pattern after `;;`.** Applied: two private run markers handled before the pattern logic, with
   `_walk_run` the only place that touches `nest` and the case keys (approach item 2, guides 3–4);
   T2 row for `esac` after `;;`.
5. **`_loop_ranges`' `done` rule misses a `done` after a group or subshell, leaving those loops a
   bypass.** Applied: the pairing reads the raw run's last operator; T2 rows.
6. **Clean-up when a substitution ends was unspecified.** Applied: guides 2 and 4.
7. **The PowerShell note in Rejected was inaccurate.** Applied: reworded.

---

## 3. Implementation notes

> Written in step 3. Only deviations from the plan above, each with its reason. "Built as
> planned" is a complete and good entry. On a fix round, also the reproduction test's red
> run, pasted here before the fix was written — step 6 cites it.

Reproduction, red before the fix (`.venv/bin/pytest tests/test_guard_git.py -k test_violation_refuses_an_or_switch_after_an_if_compound -q`):

```
>       assert reason.startswith(COMMIT_REASON)
E       AssertionError: assert False
E        +  where False = <built-in method startswith of str object at 0xa314a0>('Refused: this would commit to `main`')
E        +    where <built-in method startswith of str object at 0xa314a0> = ''.startswith
tests/test_guard_git.py:4798: AssertionError
FAILED tests/test_guard_git.py::test_violation_refuses_an_or_switch_after_an_if_compound
1 failed, 1522 deselected in 0.66s
```

`violation` returned `""` (allowed), the shape the Defect block's Observed row describes.

Green after the fix: the same test passes, and the whole suite is 1614 passed (1613 before plus the reproduction), no existing test changed outcome.

Deviations from the plan, none of which touch section 1:

- `_compound_spans` returns a third dict besides the plan's two: for each invocation that opens a matched compound, how many of those are `if`/`while`/`until` leaders written before its first `!` or `coproc`. `_judge` needs it to key a `!` scope between the leaders' opens and the command word's open (guide 3); counting leaders without regard to which ones paired would raise the key past a level that was never raised. Matched openers are a subset, not a prefix, of an invocation's kinds (a closer pops the top of the stack first), so the pairing records ordinals.
- A private helper `_openers(tokens)` finds the kinds an invocation opens and the leader count, and `_own_operators(segment, run)` lists a run's operators at the invocation's own depth. Neither is public.
- `_judge` passes the markers to `_walk_run` as one extra call per invocation (two when a `!`/`coproc` scope has to be keyed between the leaders and the command word) rather than appending them to the invocation's run. The result is the same sequence of operators; a separate call keeps the newline-only test of the invocation's own run untouched and lets `_judge` read the level in between. `_walk_run` still ignores markers in that test and handles them before the case-pattern logic.
- A closing word `fi`, `esac` or `done` is a pattern, not a closer, when the next invocation's own run opens with `)` and carries only `(` or `{` after it; a plain `next separator is )` test (as `_loop_ranges` uses) would also reject `( while x; do :; done ); y`.
- Resolved at step 4 (was a known residual): a closer written `\done` as the first word of an invocation read as `done`, so `true || while false; do :; \done; :; done | git checkout -b x && git commit -m x` paired the loop at the wrong word and was allowed while bash lands the commit on `main`. Classified at step 4 as a code deviation that broke A2 (not a note to carry forward) and fixed there; see section 4, Escaped closer bypass.

Sanity check against bash 5.2 (git shadowed by a function keeping HEAD in a temp file, an empty checkout argument failing, `PATH=/usr/bin:/bin`, stdin closed, a timeout; shown live first by a plain `git commit -m x` landing `COMMIT on main`): the 45 rows of scratchpad `r6_class.py` (15 constructs x `true ||`, `!`, `coproc`), the 26 rows of `dc6_rows.txt` and 20 extra rows (`r6/extra.py`) all agree: every row where bash lands on `main` is refused, none allowed. Allowed rows land on `x` or run nothing in bash (`true || if true; then git checkout -b x && git commit; fi`, `if ! git diff --quiet; then git checkout -b feat/x && git commit -m x; fi`, create-or-switch). Perf: 3,000 nested `if` openers with closers finish in 0.4 s, 5,000 in 1.2 s.

Step 5 changes (production code, all inside the class and the Root cause row's site; none touches section 1):

- Confirmed bypasses found by the step 5 readers and the orchestrator's bash check (thirteen shapes: a word that only looks like an opener after an assignment, a redirection, a wrapper or `\!`; a closer written straight after `)`, `}` or another closer; `coproc NAME <compound>`; an empty last `case` clause). Red first (186 rows, commit 9386579), then fixed.
- `_openers(tokens)` now follows bash's reserved-word rule: it walks only reserved words that take a command (`then`, `do`, `else`, `elif`, `!`, `if`, `while`, `until`, `time` + options, `coproc` + optional name) and stops at anything else; it no longer reuses `_walk_prefix`. It returns a third value (whether a `[[` is closed in the same invocation). A quoted or escaped word is never reserved; `\!` is told apart from `!` by a second private mark `_BANG_MARK` (`_ESCAPED_BANG`), which `_plain` strips, `_walk_prefix` and `_group_position` still read as the round 3 leader, and `_openers` does not.
- `_compound_spans` closes on a closing word after `;`, newline, `&`, a `case` terminator, `)` or `}`; on each further closing word of a run (`fi fi`); and on the run after a `]]` that closed a `[[`. It returns a fourth value, `paired`.
- Safety net (orchestrator's decision B): when `paired` is false (an opener left open, a closer that matches nothing or the wrong kind, a closing word where none can stand, an opener dropped when a substitution ends), `_judge` treats every branch switch in the bash reading as unsure (`ok = here | {target}`), so a mis-pairing can only over-refuse. The PowerShell reading is exempt: it has no `fi`, and its `if (...) { }` would otherwise always be unpaired. No existing test changed outcome.
- `_group_position` reads a brace after a run of `fi`, `esac`, `done` as a group, so `{ if true; then :; fi }` is a group in the bash reading too (it was refused only through the PowerShell reading).
- Docstrings (module and private) and STRUCTURE.md brought in line with all of the above.

---

## 4. Verification log

> Written in step 4: the static half. Command output, not a summary of it.

| Check | Result |
|---|---|
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `43 files already formatted` |
| `mypy` | `Success: no issues found in 11 source files` |
| `pytest -q` | `1674 passed` (1614 after step 3, plus the 60 rows of the escaped-closer test); no existing test changed outcome |
| Plan completeness | every signature in the Public API table exists as written: `violation(command: str, branch: str) -> str` unchanged; `segments`, `git_subcommand`, `push_targets_main`, `switch_target`, `UNMODELLED_OPENERS`, `SUBSTITUTED`, `Segment` unchanged. No Missing, no Unplanned public surface; the deviations are the five in section 3, all private. |
| `STRUCTURE.md` | in sync. The `structure-auditor` report (before step 4) found the signature table correct and three prose gaps; edits 1 and 2 applied after checking each against the code (`_BEFORE_CLOSER`, `_openers`, `_compound_spans`, `_UNCERTAIN_LEADERS`), with the module docstring's matching gaps; edit 3 (record `\done` as a known miss) was not applied, the bypass was fixed instead. |
| `python -m <package>.<module>` | no new module; `guard_git.py` is a hook entry point (`main()` reads stdin, exit 0). `template_repo.hello_world` does not resolve because the package is not installed in this environment, unchanged by this round. |

### Escaped closer bypass (deviation 5), fixed in this step

Classification: a **code deviation that breaks A2**. A2 requires every compound inside an `||` operand to be refused in every position; a compound whose closer-looking word is escaped or quoted mid-word (`\done`, `d\one`, `do''ne`, `d"o"ne`, `f\i`, `es\ac`, `[[ x == \]] && b ]]`) was paired at the wrong word, so the level fell back to the operand's key and the switch was trusted. Not a change to section 1, so no halt: it is the A2 promise, unmet.

Cause, at the same site the Defect block names (`_walk_run`'s level moving only for paired compounds), reached through the pre-pass: `_scan` wrote the quote mark only in front of a word that *starts* with a quote, so a backslash, or a quote in the middle of a word, left `\done` reading as `done`.

Red first: `test_violation_refuses_a_switch_after_a_compound_with_an_escaped_closer`, 60 rows (30 bodies x `true ||` and `!`), each row first run in bash 5.2 (git shadowed by a function keeping HEAD in a temp file, an empty checkout argument failing, `PATH=/usr/bin:/bin`, stdin closed, a 10 s timeout, the oracle shown live first by a plain `git commit -m x` printing `COMMIT on main`): all 60 land the commit on `main`. Pre-fix run: `60 failed` (commits c89651e, bed1b0d).

Fix (`_scan`, `guard_git.py`): a `mark()` closure writes the quote mark in front of the first quote or backslash escape of a word, wherever it sits (single quote, double quote, an escaped operator character, any other escape outside double quotes and outside `${ }`), once per word. It replaces the `starts_word` test. The mark only reaches the syntax checks (leaders, assignments, redirections, compound openers and closers, the `done` test); every text comparison already strips it through `_plain`. One exception: `\!` stays unmarked, because marking it flips the recorded round 3 over-refusal `\! git commit -m x` (three existing tests: `test_violation_pins_a_quoted_or_misplaced_leader_as_an_over_refusal`, `test_violation_pins_the_both_shell_over_refusals`, `test_violation_still_reads_a_quoted_name_as_the_name_it_spells`) to allowed. Bash does run a command named `!` there, so allowing would be right, but the pin says changing it is a decision, and the brief says halt on any changed test; the exception keeps all 1613 + 1 earlier tests unmodified. Dropping the exception is a one-line change plus those three rows, for the user to decide.

After the fix: the 60 rows pass; `1674 passed`.

Oracle evidence after the fix (scratchpad `r6b/`): `esc.py`, 84 rows (7 `done` spellings x 4 loop kinds, 5 `fi`, 4 `esac`, 5 `]]` spellings, after `true ||` and `!`): 0 bypass (56 before the fix). `esc2.py`, 756 rows: escaped and quoted forms of every opener (`\if`, `i\f`, `'if'`, `"if"`, `\case`, `ca''se`, `\while`, `\for`, `\until`, `\select`, `\[[`, `[\[`, `'[['`, `"[["`) as commands and arguments, and of every closer (`\fi`, `\esac`, `\done`, `\]]`, `']]'`, `d''one`) inside `if`, `while`, `{ }`, `( )`, `$( )` and `case` bodies, nested, after `true ||`, `false ||`, `!` and `true || git status |`: 0 rows where the guard allows and bash lands on `main`; 180 rows refused where bash lands nothing (syntax errors, play-safe). Differential of the previous guard (353e2fa) and the new one over the 511-command suite corpus on `main` and `feat/x`: 1185 rows, 0 differences.

---

## 5. Test log

> Written in step 5: the dynamic half.

| Intent | Test names | Result |
|---|---|---|
| T1 (A1) | `test_violation_refuses_an_or_switch_after_an_if_compound` (the step 3 reproduction, unchanged: red in section 3, green) | pass |
| T2 (A2) | `test_violation_refuses_these_scope_commands_on_main_and_not_elsewhere` (20), `test_violation_refuses_a_switch_after_a_double_bracket_test` (27), `test_violation_refuses_a_switch_after_chained_leaders_and_a_timed_loop` (30), `test_violation_refuses_a_switch_after_a_timed_compound_before_either_pipe` (4), `test_violation_refuses_a_push_of_head_after_a_compound_in_a_scope` (36), `test_violation_refuses_a_switch_after_a_compound_with_an_escaped_closer` (60, step 4) | pass |
| T3 (A3) | `test_violation_reads_a_case_patterns_parentheses_as_the_patterns` (36), `test_violation_refuses_a_switch_after_a_compound_closed_by_a_brace` (12), the `!` rows of the T2 tests | pass |
| T4 (A4) | `test_violation_still_allows_these_scope_commands` (15), `test_violation_refuses_a_switch_after_a_coproc_compound` (39), `test_pairing_reports_a_command_it_could_not_pair` (20), `test_violation_trusts_no_switch_in_a_command_whose_compounds_do_not_pair` (20), `test_violation_trusts_the_same_switch_when_the_compounds_do_pair`, `test_violation_does_not_apply_the_pairing_net_to_the_powershell_reading`; the 1613 earlier tests unmodified (`:3778` and `RUN_PINS` among them) | pass |
| T5 (A5) | `test_violation_refuses_a_scope_opener_before_every_container_construct` (198 rows, pure Python); `test_violation_judges_deeply_nested_compounds_quickly` (6) | pass |
| Reader findings (thirteen confirmed bypasses) | `test_violation_refuses_a_switch_after_a_compound_holding_a_misplaced_opener` (96), `..._after_a_closer_that_follows_a_group_or_a_closer` (69), `..._after_a_case_with_an_empty_last_clause` (36), `test_pairing_finds_a_partner_for_every_opener_and_closer_in_a_valid_compound` (107), `test_group_position_reads_a_brace_after_closing_words_as_a_group` / `..._after_an_argument_as_a_word` (4 each), `test_violation_reads_a_brace_after_a_closer_as_a_group_in_the_bash_reading` (12), the escaped-bang tests (`test_segments_shows_an_escaped_bang_as_a_bang_without_its_mark`, `test_pairing_does_not_open_a_compound_after_an_escaped_bang`, `test_a_forged_bang_mark_is_blanked_before_it_can_make_a_leader`, `test_violation_still_steps_over_an_escaped_bang_as_a_leader`), `test_violation_keeps_the_answers_of_rounds_1_to_4` (19) | pass |
| T6 (A6) | Existing suite unmodified (no removed line in `tests/test_guard_git.py` against dc1e629); the differential against 6f05520 ran in step 6 (section 6) | pass; differential in section 6 |

Run: `ruff check .` clean, `ruff format --check .` clean, `mypy` clean, `pytest -q` 2476 passed (1674 after step 4, plus 802 in step 5).

Readers: the `input-space` and `contract` test-designers plus the orchestrator's bash check (`r6_designer_reports.md`).
All thirteen bypasses the check confirmed were real and inside A2/A3 (the Root cause row's class), so each was a bug to fix in place, red first (186 rows, 9386579), not a halt:
the production changes are in section 3, Step 5 changes. Contradictions they found, all resolved in the docstrings and STRUCTURE.md: misplaced openers read as bypass not over-refusal; closers valid after `)`, `}` and another closer; `coproc NAME <compound>`; `_group_position` after a closing word; "no opener" versus "not the innermost". Every other designer case (contract 6-15, input-space 5-11) was re-run through the guard and bash in this step (`r6t/dcheck.py`, 124 rows): all agree, and each already has a test of the same shape; the one disagreement was a mis-built row of mine (the backtick form `echo \`true || if ...\``: bash prints nothing because the inner output is captured, the guard refuses, play-safe).

Sweep (scratchpad `r6t/sweep.py`, bash 5.2, `git` shadowed by a function keeping HEAD in a file, an empty checkout argument failing, `PATH=/usr/bin:/bin`, stdin closed, 5 s timeout, the oracle shown live first by a plain commit printing `COMMIT on main`): 14 compound kinds (`if`, `while`, `until`, `for`, `select`, three `case` forms, `[[ ]]`, `{ }`, `( )`, `(( ))`, a function, a substitution) x 16 opener spellings (bare, assignment, redirection, backslash, wrappers, `time`, `!`, `coproc`, `\!`, quoted) x 3 closer spellings (bare, `\closer`, `'closer'`) x 11 host positions (bare, in `if`/`while` bodies with `;` or a closer written straight after, in `{ }`, `( )`, `case` clauses, with a redirection, in a substitution) x 7 scopes (`true ||`, `false ||`, `!`, `true || git status |`, `true || time`, `true || !`, `{ true ||`) x 3 tails (`|`, newline `|`, `|&`): 115,416 rows, bash lands on `main` in 12,156, guard allows 0 of those (the bypass count); 88,710 over-refusals (bash lands nothing, guard refuses), 14,550 allowed where bash lands nothing, 0 errors. The same figure in the earlier run (11:39) and in this one.

Edge cases considered and deliberately skipped, with reasons:

- A `[[ ... ]]` split across a `$( )` boundary or a `case` terminator: bash rejects it; covered by the unpaired shapes of `test_pairing_reports_a_command_it_could_not_pair`.
- PowerShell `if (...) { }` and `foreach`: braces are groups already, and the pairing net is exempt for that reading; one pin (`test_violation_does_not_apply_the_pairing_net_to_the_powershell_reading`).
- Compounds deeper than the five-thousand-link limits of round 5: covered by the depth test (2000 nested `case` and `if`, 3000 unclosed `[[`, 5000 stray closers) rather than repeated.
- Compounds with a redirection before the body (`fi >f`), function bodies called later, and variable branch targets: recorded misses of earlier rounds (section 1, out of scope).

---

## 6. Concept check

> Written in step 6, against section 1 — not against section 2. The question is whether
> the thing built is the thing agreed, not whether it matches the plan.

| # | Criterion | Met | Evidence |
|---|---|---|---|
| A1 | `true \|\| if true; then echo; fi \| git checkout -b x && git commit -m x` refused on `main` with the commit reason | yes | Red: section 3's run of `test_violation_refuses_an_or_switch_after_an_if_compound` (`violation` returned `""`, 1 failed, commit 2f14f81, before any production change). Green: the same test passes at HEAD (`1 passed`, re-run in step 6). Bash 5.2 with the oracle shown live (a plain `git commit -m x` on `main` printed `COMMIT@main`, from `feat/x` it did not): the same command lands on `main`. Root cause row against the diff: the fix is in `_walk_run` (`guard_git.py:2191-2212`, `_COMPOUND_OPEN`/`_COMPOUND_CLOSE` raise and lower `nest`, fed by `_judge` at `:2318-2322`), not at the `ok = {target}` site. |
| A2 | Every reserved-word compound and `[[ && ]]` in an `\|\|` operand refused on `main` in every position | yes | `crit_check.py` (scratchpad `r6c/`), the criteria rows of A2 in bash: first, later stage (`true \|\| git status \| case a in (a) :;; esac \| ...`), after `time`, redirection after the closer, `\|&`, across lines, inside `echo $( )`, `if { true; }; then`, `select`, `[[ a && b ]]`: all refused, each lands on `main` in bash. Tests: `test_violation_refuses_these_scope_commands_on_main_and_not_elsewhere` (20), `..._after_a_double_bracket_test` (27), `..._after_chained_leaders_and_a_timed_loop` (30), `..._after_a_timed_compound_before_either_pipe` (4), `..._after_a_compound_with_an_escaped_closer` (60). Differential, section 6: 8,279 differing rows land on `main` in bash and none is allowed by the new guard (0 bypass in 19,552 oracle-run rows). |
| A3 | The same compounds after `!`; `{ case ... esac; }` and `( case ... )` after `\|\|` or `!` | yes | `crit_check.py` rows `! if true; then :; fi \| git checkout -b feat/x && git commit -m x`, `true \|\| { case a in a) :;; esac; } \| ...`, `! ( case a in a) :;; esac ) \| ...` refused, each lands on `main`. `test_violation_reads_a_case_patterns_parentheses_as_the_patterns` (36), `..._after_a_compound_closed_by_a_brace` (12). The `bang0`-`bang9` variants of the differential: 614 differing rows each, 0 bypass. |
| A4 | Keeps: create-or-switch, `true \|\| { ...; }`, `;;`/`;&`/`;;&` terminating a scope inside a clause, round 3's compound `&&` over-refusals, `coproc <C> \| ...` now refused, `(( && ))`, `{ true; }`, `(true; true)`, function definitions still refused | yes | `crit_check.py` rows of A4 (create-or-switch and `true \|\| { git checkout -b x && git commit -m x; }` allowed; `git checkout -b feat/x && if true; then :; fi && git commit -m x` and the `for` form refused; `coproc if true; then :; fi \|` and `coproc { true; } \|` refused; `(( 1 && 1 ))`, `{ true; }`, `(true; true)`, `f() { :; }` refused; `if ! git diff --quiet; then git checkout -b feat/x && git commit -m x; fi` allowed): 0 mismatches. `:3778` and the `RUN_PINS` case row are in the suite unmodified (`git diff 6f05520 -- tests/test_guard_git.py` has no removed line). `test_violation_refuses_a_switch_after_a_coproc_compound` (39), `test_violation_still_allows_these_scope_commands` (15). The step 2 `coproc` change: `coproc <C> \| ...` was allowed at 6f05520 and is refused now; the plain differential shows it as `new refuses` only, and the `coproc` forms in the sweep are bash-committing on the switch target (play-safe over-refusal as recorded). |
| A5 | A committed pure-Python matrix: 3 openers x the constructs, bare and in `{ }`, refused on `main`, allowed from another branch | yes | `test_violation_refuses_a_scope_opener_before_every_container_construct`, `tests/test_guard_git.py:5349`: `MATRIX_OPENERS` (`true \|\|`, `false \|\|`, `!`) x 22 `MATRIX_CONSTRUCTS` (all the A5 constructs plus nests) x 3 shapes (bare, braced construct, braced command) = 198 rows, asserting `COMMIT_REASON` on `PROTECTED` and `""` on `feat/y`; no bash is called in it. |
| A6 | Nothing else changed; differential against 6f05520 | yes, with one explained exception | Suite: `2476 passed`; no existing test changed (no removed line in the test file against 6f05520). Differential (scratchpad `r6c/`, baseline `git show 6f05520:.claude/hooks/guard_git.py`): corpus 2,745 `(command, branch)` pairs / 1,811 commands captured by a `-p` plugin; 34 variants (plain; `true \|\| <C> \|`, `! <C> \|`, `true \|\| git status \| <C> \|` for ten compounds covering if/case(a)/case((a))/while/until/for/select/`[[ ]]`/`{ case }`/`( case )`; `if true; then ...; fi` in two spellings) x `main`/`feat/x` = 117,966 rows; 19,657 differ, all new-refuse/base-allow (0 rows where the new guard allows what the old refused); oracle-run 19,552 (99 PowerShell-only rows listed in `skipped_ps.json`, not run; 6 hostile skipped): bash lands on `main` in 8,279 (the bug), lands nothing in 5,925, is a syntax error in 5,338, 10 time out (`until ! git diff --quiet; do git checkout -b feat/x && git commit ...`: the shadowed `git diff` makes it loop; the body switches to `feat/x` before it commits, so nothing lands on `main`; the new refusal is play-safe). Bypass rows (new allows, bash lands on `main`) among the differing rows: 0. Every difference involves a compound word or `[[ ]]` except two plain rows, below. |

Differential detail, as asked in the brief:

- **Plain commands, the realistic cost.** The suite's plain commands: 3,622 rows (corpus x `main`/`feat/x`), 531 outcome changes between 6f05520 and HEAD. 528 of them are commands only round 6's own tests pass (compounds, stray closers, the pairing shapes); over the 913 plain rows from the suite as it stood at 6f05520 (the old test file run against HEAD, 1,361 pairs) **3 changed, all refusals that stay refusals**: `echo;git commit -m x` and `git commit -m x` and `if git commit -m x` on `main`. U+E00B is the new `_BANG_MARK` (step 5, told apart from `!` so `\!` opens no compound); a forged private character is blanked, as round 5 already does for the others, so the text reads as the plain commit it hides. Bash lands nothing on the literal text (`echo\ue00b` and `\ue00bgit` are not commands), so these are play-safe refusals of input no real command line carries. The first two contain neither a compound word nor `[[ ]]`, so A6's "every difference involves a reserved-word compound" holds literally for 19,655 of the 19,657 differing rows and for these two by way of the new mark that the compound fix introduced: recorded here, not a halt, since it only refuses more and no real command contains the character.
- **The pairing net (step 5, decision B).** Rerun with the net disabled (`nonet_guard_git.py`, the `or not (paired or powershell)` term removed): it changes 0 of the 913 old-suite plain rows, 28 plain rows of round 6's own tests and 795 variants of those (all `refuses more`, none `allows more`). Run in bash: 779 are syntax errors, 43 run nothing on `main` (an unterminated backtick compound), 1 lands on `main` (the 1,000-deep `if true; then (` test: the net refusing it is right). No existing test changed outcome, because the net only turns an unsure switch into a refusal and the suite passed unmodified.
- **Every row the new guard allows, through bash.** 56,090 allowed rows; 55,205 run (862 PowerShell-only rows not run, 23 hostile skipped): 44,359 land nothing, 10,759 are syntax errors, 16 time out (the `until ! git diff --quiet` loop above, which switches to `feat/x` first), **71 land on `main`**, all on `main` and all allowed by 6f05520 too, and all three recorded misses of rounds 1-5: `git $'\x63ommit' -m x` (a hex-escaped subcommand, 13 rows), `echo $'it\'s'; git co""mmit -m x # '` (a split-quote subcommand, 32) and `echo "${x:-'$(git commit -m x)'}"` / `echo "${x:-'}" "$(git commit -m x)" "'}"` (a lone `'` inside a quoted `${ }`, 26): all variants of four plain commands. None is new and none involves a compound word.
- **Criteria rows.** `crit_check.py` runs 133 literal examples from the acceptance criteria of rounds 1-6 through the new guard and, where bash can run them, the oracle: 0 mismatches against the stated outcome, 0 rows allowed that bash lands on `main`.

Drift found, and what was done about it: none to the code. Noted: (1) the two forged-private-character plain rows above, which A6's wording does not name; (2) the `\!` exception to the quote mark that step 4 left (the round 3 over-refusal pins) is still in place and still a user decision to drop; (3) `STRUCTURE.md` brought in line with the `structure-auditor`'s eight edits, each checked against the code first (all eight applied: a stale `done` rule sentence, two private names, the matrix opener set, the push-shape, whole-commands and depth counts, and the round 6 mention in the shell-lexing intro).

### Earlier rounds still hold

> Later rounds only. Re-check every acceptance criterion from every earlier round in this
> folder: this round changed code they depend on, and their tests passing is necessary but
> not sufficient — a criterion can be satisfied by tests that no longer describe what the
> feature does.

| Round | # | Criterion | Still met | Evidence |
|---|---|---|---|---|
| 1 | A1 | The reported heredoc-with-a-stray-quote allowed on `main` | yes | `crit_check.py` row, bash lands nothing; guard allows. |
| 1 | A2 | Heredoc bodies are data; unquoted-delimiter substitutions judged; `git commit -F - <<'EOF'` refused as a commit | yes | Seven rows (`cat <<'EOF'`, `<<-` with a tab, `$(git commit)` and backtick `git push` bodies, the command after the heredoc, `-F -`, allowed on `feat/x`), all as stated. |
| 1 | A3 | `#` read as bash does | yes | Three rows (`# it's fine` newline commit refused, `echo ok # git commit` allowed, `echo ok#1 && git commit` refused). |
| 1 | A4 | Backslash-newline joins | yes | `git \\\ncommit` refused on `main`, `git \\\npush origin main` refused on `feat/y`. |
| 1 | A5 | Plays safe on the unmodelled forms | yes | The `$'it\'s'` and `cat <<EOF >/dev/null` reproductions refused on `main`, allowed on `feat/x`. |
| 1 | A6 | Nothing else changed; the one accepted cost | yes | The suite passes unmodified; round 1's differential is unchanged by this round (the 913 old-suite plain rows differ in 3, section 6). |
| 2 | A1-A3 | Substitutions in words, quotes and backticks judged in every position | yes | 13 rows of `crit_check.py` (the `"$( )"`, `${x:-$( )}`, `[[ -n "$( )" ]]`, `declare`, `<<<`, nested `$( ( ) )`, backtick forms, and `EOF)` closing lines) refused as stated, bash lands each on `main`. |
| 2 | A4 | Process substitution judged | yes | `diff <(git commit -m x) /dev/null` refused on `main`, `diff <(git push origin main) f` refused from a branch. |
| 2 | A5 | A substitution runs before its command; `&&` carries into it | yes | `git commit -m "$(git checkout -q main)x"` refused from a branch; `git checkout -b feat/y && out="$(git commit -m y)"` allowed on `main`. |
| 2 | A6 | `main` as any branch it could land on | yes | Five rows as stated (`; `, newline, `\|\| true;`, `(git checkout main) &&`), `git checkout feat/y; git commit` allowed, `git checkout -b feat/x; git commit` refused on `main`. |
| 2 | A7 | Funsub plays safe | yes | `echo ${ git commit -m x; }` refused on `main`, allowed from a branch. |
| 2 | A8 | Harmless substitutions allowed; the pipeline's own commit form | yes | `$(git status)` and `` `date` `` allowed; the `$(cat <<'EOF' ... )` commit refused on `main`, allowed on a branch. |
| 2 | A9 | Nothing else changed | yes | Suite unmodified and green; no test of rounds 1-5 removed or edited. |
| 3 | A1-A3 | Reserved words stepped over; a switch after one counted | yes | Seventeen rows of `crit_check.py` (`if`, `elif`, `while`, `until`, `! !`, `coproc`, arithmetic `for`, `ls \| if`, `x=$(if ...)`, push from a branch, three switches after a leader), as stated. |
| 3 | A4 | Trust: `!`-led switch only widens; the accepted cost | yes | `! git checkout -b feat/x && git commit`, `if ! git checkout -b feat/x; then`, `if git checkout -b feat/x; then`, `while git checkout -b ...` refused; `git checkout -b feat/x && git commit` allowed. |
| 3 | A5 | A switch anywhere in a loop counts for the whole loop | yes | Both loop rows refused from `feat/y`. |
| 3 | A6 | Words that are not commands stay words | yes | `echo if git commit`, `for git in commit`, `git commit -m then`, the `-C` switch after `then` allowed; `{ }`, `time`, `case`: refused. |
| 3 | A7 | Nothing else changed | yes | Suite unmodified and green. |
| 4 | A1-A3 | The `\|\|` operand and the `!` scope | yes | Nine rows of `crit_check.py` incl. `git status \|\| git checkout -b x && git commit`, later stage `\|`/`\|&`, `time`, chained `\|\|`, push of `HEAD`, the named switch from `feat/y`, and the `"$(true && true)"` leak: all refused. Round 6 changes the key those scopes use; the terminator and group pins are in the suite, unmodified. |
| 4 | A4 | The five allowed forms stay allowed | yes | All five allowed on `main` (create-or-switch, `git fetch \|\| true && ...`, `true \|\| false && ...`, `true \|\| { ...; }`, `&& ! git diff --cached --quiet &&`). |
| 4 | A5 | Nothing else changed | yes | Suite unmodified and green. |
| 5 | A1, A2 | Quoted operators are never operators | yes | `true \|\| echo ";" \|` and `${x:-;}` and `! true \| echo ';' \|` refused on `main`; `segments('echo ";" x')` one invocation (suite, unmodified). |
| 5 | A3 | Shell-dependent tokens play safe | yes | `\;`, bare `{`, `ForEach-Object { }`, `Invoke-Command -ScriptBlock { }`, `Start-Job { }` refused. |
| 5 | A4 | Carriage return | yes | `&&\r\n` and the `git commit\r\n` / `git push origin main\r\n` rows refused. |
| 5 | A5 | A quoted word at command position is not syntax | yes | `'if'`, `'!'`, `"!"`, `"X=1"`, `'>'`, `echo ";" git commit` allowed on `main`; `\!`, `x=1 if`, `>/dev/null !`, `sudo -n !`, `'!' git checkout -b x && git commit`, `"git" commit` refused. |
| 5 | A6 | Nothing else changed | yes | Suite unmodified; round 5's rows in this round's differential agree (3 plain differences, section 6). |

Regression result: all rounds 1-5 criteria hold. 2,476 tests pass, none of rounds 1-5's edited or removed.

---

## 7. Ship log

Gates on the whole tree: ruff check clean, ruff format 43 files formatted, mypy clean (11 files), pytest 2476 passed. Review: no TODO/FIXME/debug, no stray files (only plan files, guard, tests, STRUCTURE.md in the diff against main), every step left a commit. The interrupted step 5 run is recorded by its WIP commits above.

| Field | Value |
|---|---|
| Commits | `f3afcc5 Concept check: the git guard keeps an \|\| or ! scope across a compound command`<br>`4e80d56 Test: round 6 compound scopes, edge-case suite and sweep`<br>`4cbbf99 WIP step 5: push-of-HEAD shapes and single-invocation [[ ]] rows, docs brought up to the reserved-word rule`<br>`6e29ac7 WIP step 5: a brace after a closing word is a group in the bash reading, docstring brought up to the rule`<br>`fc2ce18 WIP step 5: round 6 edge-case suite (misplaced openers, closer runs, coproc, pairing net, container matrix)`<br>`e360d1d WIP step 5: bash's reserved-word rule for openers and closers, and a pairing failure plays safe`<br>`9386579 WIP step 5: reserved-word position and closer-run bypasses, red (186 rows)`<br>`dc1e629 Verify: the git guard keeps an \|\| or ! scope across a compound command`<br>`dbd8074 WIP step 4: mark a word with a quote or escape anywhere in it, closing the escaped-closer bypass`<br>`bed1b0d WIP step 4: escaped closer reproduction, red (60 rows)`<br>`c89651e WIP step 4: escaped closer reproduction, red`<br>`353e2fa Keep an \|\| or ! scope across reserved-word compounds in the git guard`<br>`2f14f81 WIP step 3: reproduction, red`<br>`257a564 Plan accepted: the git guard keeps an \|\| or ! scope across a compound command`<br>`a003b23 Plan: the git guard keeps an \|\| or ! scope across a compound command`<br>`8dd8b56 Plan: remove leftover template text in Builds on`<br>`bc42c3d Plan (draft, before critique): the git guard keeps an \|\| or ! scope across a compound command`<br>`39818fc Concept: the git guard keeps an \|\| or ! scope across a compound command`<br>(plus the Ship commit that closes the round) |
| Pushed to | `origin/fix/guard-git-shell-lexing` |

---

## 8. Recommendations

> Written in step 8. Only follow-ups that are critical and belong to this work, which most
> rounds do not have: replace the table with `None.` when there are none. Lesser ideas are
> one-line notes in `DEVELOPMENT.md`, not rows here. Not bugs in what this round built —
> those go back through `/build` before the pull request. A critical defect outside what
> section 1 promised, such as a class member it put out of scope, is a recommendation here,
> and its round opens through `/fix`.

None.

Notes, not critical (kept here rather than in `DEVELOPMENT.md` at the user's instruction):

- `defect-class` reader: nothing critical, no bugs against section 1. `_loop_ranges` still pairs loops
  with its own `done` rule (it rejects a `done` after `)`/`}`, ignores `fi done` runs, opens on a
  misplaced `x=1 while`); every difference only lengthens a loop, so it only refuses more. Taking its
  pairs from `_compound_spans` would remove the second rule before a later change reverses that.
  Medium effort.
- The pure-Python container matrix could take the sweep's other openers (`true || git status |`,
  `{ true ||`, `true || time`, `true || !`) and tails (newline then `|`, `|&`), which were swept
  only in scratch code. Small effort.
- Nearest out-of-scope member: the recorded miss "a redirection on a compound command, which bash
  runs before its body" (`{ git commit -m x; } > "$(git checkout main)"` from a branch); unchanged,
  out of scope by section 1, contrived.

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
