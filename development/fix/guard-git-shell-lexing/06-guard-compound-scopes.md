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
