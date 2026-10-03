# The git guard does not trust a switch that `||` may skip

<!-- claude-plan step=7 status=active -->

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
| 2 | Plan | `/plan` | with the user | done |
| 3 | Implement | `/implement` | in `/build` | done |
| 4 | Verify | `/verify` | in `/build` | done |
| 5 | Test | `/test` | in `/build` | done |
| 6 | Concept check | `/concept-check` | in `/build` | done |
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

---

## 1. Concept

### Defect

| Field | Value |
|---|---|
| Observed | `violation("git status \|\| git checkout -b x && git commit -m x", "main")` returns `""` (allowed). In bash with `git` shadowed by a function keeping HEAD in a file, the command prints `COMMIT on main`. |
| Expected | Refused with the commit reason. `violation`'s docstring and STRUCTURE.md say a switch replaces the set of branches only across `&&`, and a commit is refused when `main` is any branch it could land on (round 2, A-criteria on the set-of-branches rule). |
| Reproduction | `violation("git status \|\| git checkout -b x && git commit -m x", "main")` → `""`; bash → `COMMIT on main`. Also, all allowed and all commit or push on `main` in bash: `git rev-parse --verify feat/x \|\| git checkout -b feat/x && git commit -m x` (feat/x exists); `git checkout main \|\| git checkout -b x && git commit -m x` from `feat/y`; `true \|\| git checkout -b x && git push origin HEAD`; `true \|\| echo a \| git checkout -b x && git commit -m x`; `true \|\| git checkout -b x "$(echo)" && git commit -m x`; `false \|\| true \|\| git checkout -b x && git commit -m x`; `true \|\|` newline `git checkout -b x && git commit -m x`; `if true \|\| git checkout -b x && git commit -m x; then :; fi`; the same inside `echo "$(...)"`. |
| Root cause | `.claude/hooks/guard_git.py:1672` at 43eeea3 (`_judge`, now line 1800 and unchanged), `ok = here \| {target} if unsure else {target}`: `ok` is the set of branches HEAD could be on if every command of the current `&&` chain succeeded, but a switch replaces it with `{target}` even when its pipeline is the right operand of `\|\|`. bash reads `a \|\| b && c` as `(a \|\| b) && c`, so `c` runs when `a` succeeded and the switch never ran. Line 1638 at 43eeea3 (now 1766) only reads the wrong value (the site). Sibling: `guard_git.py:1623` at 43eeea3 (now `_walk_run`, line 1631, and the cleanup at 1754) clears round 3's `!`/`coproc` `negating` state on a list end at any depth, so a `;`, `&&` or `\|\|` inside a substitution in the switch command ends the negation of the outer pipeline. |
| Introduced by | Older than this branch: `main`'s guard has the same flaw in its earlier form (`effective = target` after any switch, reset only on a non-`&&` separator). The set-of-branches form came in round 2 (3df5e1e), the `negating` state in round 3 (6994e72). |
| Class | (1) A switch in an `\|\|` operand followed by `&&`, in every form: through later pipeline stages (`\|`, `\|&`); after wrappers, assignments, redirections and reserved words; with substitutions in the switch command; chained `\|\|`; an `\|\|` after an `&&` chain; `coproc true \|\|`; a heredoc on the switch; an `&&` ending a line; the commit later in the chain after more `&&` segments; the commit inside a substitution; the whole inside `{ }`, `$( )` or an `if` condition; a named switch without `-b` (`git checkout main \|\| git checkout feat/x && git commit -m x` from `feat/y`); a push of `HEAD`. (2) The `negating` depth leak: `! true \| git checkout -b feat/x "$(true && true)" && git commit -m x` on `main` is allowed and bash commits on `main` (also `"$(true; true)"` and backticks); a new `\|\|` state built the same way would inherit it (`true \|\| git checkout -b x "$(true && true)" && git commit -m x`). Already refused, by `_join` reading `; } &&` and `) &&` as `;`: a group, subshell or compound command in the `\|\|` operand; `true \|\| ! git checkout -b x && ...` by the `unsure` branch. Checked and clean: `&`, non-last pipeline stages, `case`, `if`, loops, functions, groups. |
| Blast radius | Only `_judge`, behind `violation`; the caller is `guard_git.main`, the hook. No test pins `\|\| <switch> && <commit>`. The comment above `ok` in `_judge` (1603–1605 at 43eeea3, now 1725–1730), the module docstring and STRUCTURE.md's guard paragraph state the invariant the code breaks and are updated with the fix. Nothing depends on the wrong answer. |
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

### Approach

**Chosen: close each `||` operand by merging what its left side trusted back into `ok`, with
groups and substitution depth read from the separator runs `_segments` already collects.**

`ok` means "the branches HEAD could be on if every command of the current `&&` chain
succeeded". For `a || b`, the list succeeds when `a` succeeds or when `b` does, so once the
operand `b` is over, `ok` must be `ok_after_a | ok_after_b`. The fix keeps that union
explicitly instead of special-casing the switch:

- At an `||`, remember `ok` as it stands (what the left side trusted) as the operand's
  **base**. A second `||` at the same place adds the current `ok` to that base (chained
  `a || b || c`).
- When the operand ends, set `ok |= base`. It ends at `&&`, `;`, newline or `&` at the
  `||`'s own depth and group level, or when the group it sits in closes, or at the end of
  the command. `|` (including `|&`) and anything deeper (inside a group opened after the
  `||`, or inside a substitution) does not end it.
- The `&&` that ends it then reads the widened `ok` as it does today.

This removes the cause at line 1672 without touching it: a switch inside the operand may
still replace `ok` for commands *inside* the operand (so
`true || { git checkout -b x && git commit -m x; }` stays allowed), but what leaves the
operand is the union. Create-or-switch stays allowed because both sides trust `feat/x`.

Groups are the obstacle: `_join` folds `|| {`, `; } &&` and `)&&` into a single separator,
and `_governs` reduces a glued punctuation token (`)&&`, `||(`, `);`) to one piece, so neither
`Segment.separator` nor `pending` can say where a group opened or closed. `_segments` keeps a
second list beside `pending` holding the **raw operators** of each run in written order, and
hands those runs out through a private optional parameter; `_judge` walks each run's
operators in order. That keeps the public `Segment`, `pending` and `_join` unchanged.

Round 3's `negating` state gets the same keying. It is set at the `!`/`coproc` segment's
(depth level, group level) and cleared only by a list end at that key, or by the group it
sits in closing. A `;`, `&&` or `||` inside a substitution or a deeper group no longer clears
it.

**Rejected:**
- **Treat a switch after `||` as unsure, as `!` is** (`ok = here | {target}`). It misses a
  switch in a later pipeline stage or after a substitution (the separator on the switch's
  segment is then `|` or `SUBSTITUTED`), and refuses the create-or-switch idiom that A4
  keeps.
- **Add group fields to the public `Segment`.** It changes the public dataclass and every
  test that pins segment tuples.
- **A real bash grammar (AST) parser.** Far beyond a small fix, and it would replace the
  pre-pass three rounds have verified.

### Modules

| Path | New or changed | Purpose |
|---|---|---|
| `.claude/hooks/guard_git.py` | changed | `_segments` hands out each segment's separator run; `_judge` tracks open `\|\|` operands and re-keys `negating` by depth and group level; comment at 1603–1605 and module docstring |
| `tests/test_guard_git.py` | changed | New tests for A1–A5 under a round 4 heading; existing tests untouched |
| `STRUCTURE.md` | changed | Guard section prose on `\|\|` trust and the `!` scope; tests entry gains the round 4 paragraph |

### Public API

No public signature or constant changes. `segments`, `Segment`, `git_subcommand`,
`switch_target`, `push_targets_main` and `violation` keep their signatures; only which
commands `violation` refuses changes, as section 1 says.

| Signature | Module | Purpose | Covers |
|---|---|---|---|
| `violation(command: str, branch: str) -> str` | `guard_git.py` | Unchanged signature. After an `\|\|` operand, `&&` trusts what either side trusted; a `!`/`coproc` scope is not ended by separators inside a substitution or deeper group. | A1–A5 |

Private and not listed: the `_segments` run parameter, the operand stack in `_judge`, a
small helper for the (depth level, group level) key if the build wants one.

### Implementation guide

1. **Reproduction first (fix round).** Add `test_violation_refuses_a_commit_after_an_or_switch_on_main`
   asserting `violation("git status || git checkout -b x && git commit -m x", "main")`
   starts with the commit reason, under a new heading "round 4: trust after `||`" at the end
   of the file. Run it red, paste the run into section 3, commit before any production
   change. If it is already green, halt.
2. **Runs out of `_segments`.** Keep a second list, `raw`, beside `pending`. Wherever a
   separator piece is appended to `pending`, append to `raw` that piece's operators split in
   written order — `re.findall(r"\|\||&&|\|&|;;&?|;&|[;&|(){}\n]", piece)` — so `)&&` gives
   `)`, `&&`, `||(` gives `||`, `(`, and `))` gives `)`, `)`. Reset `raw` wherever `pending` is
   reset, save it in `opened` with `pending`, and restore it on the empty-group `_CLOSE` path
   exactly as `pending` is. Give `_segments` a keyword-only
   `runs: list[tuple[str, ...]] | None = None`; when given, `flush` appends `tuple(raw)` for
   each segment it appends — empty for a `SUBSTITUTED` segment, the inherited run for the
   first segment of a substitution (as `separator` is inherited). `pending`, `_join`,
   `segments` and every other caller are unchanged.
3. **The key.** For segment *i*, its run belongs to the **level**
   `min(depth_i, depth_{i-1})` (`depth_{-1}` = 0): the inherited run of a substitution's
   first segment belongs to the command containing it. Keep a group count per level,
   `nest[level]`; walking a run's pieces in order, `(`/`{` increments it and `)`/`}`
   decrements it (never below 0). A piece's key is `(level, nest[level])` at that moment.
4. **Operands in `_judge`.** Keep a stack of open operands `(key, base)`. Before walking a
   segment's run, pop every entry whose level is greater than `segment.depth` (a
   substitution that has ended), doing `ok |= base` for each; the substitution's frame
   already carries its targets. Then walk the segment's run before computing `here`:
   - `||` at key *k*: if the top of the stack has key *k*, `base |= ok`; else push
     `(k, set(ok))`.
   - `&&`, `;`, `&` at key *k*, and a newline at key *k* **only when the run holds no other
     operator** (the rule `_join` already applies: `||` or `|` or `&&` followed by a newline
     continues the list): pop every entry whose key is *k* and do `ok |= base` for each.
   - `)`/`}` closing to nest *n* at a level: first pop every entry at that level whose group
     level is greater than *n* (`ok |= base` for each), then decrement.
   - `|` (and what `|&` governs to): nothing.
   Pieces at a deeper key than the top entry leave it alone. Then compute `here` exactly as
   today: an `&&` reads the widened `ok`.
5. **Play safe where the key is unsure.** If a run's pieces cannot be read cleanly (a close
   with nothing open, a level that jumps), widen rather than drop: an entry is only ever
   dropped by the rules above, and each drop does `ok |= base`. A stack left open at the
   end of the command needs nothing.
6. **`negating` by key.** Replace the boolean and the `groups` counter with a set of keys.
   A `!`/`coproc`-led segment adds its own key `(segment.depth, nest[segment.depth])`, taken
   after its run is walked. A key is cleared by a list-end operator (`_LIST_ENDS`) at exactly
   that key — a newline only under guide 4's rule — or by a close that takes that level's
   nest below the key's group level, or (as in guide 4) when a segment's depth drops below
   the key's level. Operators at a deeper level or group level leave it. The switch is
   unsure while the set is non-empty, so line 1671 reads `unsure = bool(negating) or
   _leads_uncertainly(...)`; line 1672 is unchanged.
7. **Docs.** Rewrite the comment at 1603–1605 (`ok` after an `||` operand is the union of
   both sides; only a switch inside an operand is trusted inside it). Update the module
   docstring's trust paragraph and STRUCTURE.md's guard section to say a switch on the right
   of `||` is trusted by what follows only together with what the left side trusted, and
   that the `!`/`coproc` scope ends at its own level. Add the round 4 paragraph to the tests
   entry.

### Test intents

| # | Must prove | Covers |
|---|---|---|
| T1 | `git status \|\| git checkout -b x && git commit -m x` on `main` refused with the commit reason: red before, green after | A1 |
| T2 | Every A2 form refused on `main` (the named switch from `feat/y`), each checked against bash with `git` shadowed: later pipeline stage via `\|` and `\|&`; `time`, `sudo`, `x=1`, `2>/dev/null`, `!`-free reserved word before the switch; `"$(echo)"` on the switch; chained `\|\|`; `\|\|` after an `&&` chain; `coproc true \|\|`; a heredoc on the switch; `&&` ending a line; `\|\| git checkout -b x && true && git commit`; the commit inside `"$(...)"` and unquoted `$(...)`; the whole inside `{ }`, `$( )` and an `if` condition; the push of `HEAD`; `git checkout main \|\| git checkout feat/x && git commit -m x` from `feat/y`; a subshell glued either side, `true \|\| (git checkout -b x)&&git commit -m x` and `true \|\|(git checkout -b x) && git commit -m x`; `true \|\| ` newline with a trailing space before the newline | A2 |
| T3 | The `negating` leak closed: `! true \| git checkout -b feat/x "$(true && true)" && git commit -m x`, the `"$(true; true)"` and backtick variants, the `coproc` equivalent, `true \|\| git checkout -b x "$(true && true)" && git commit -m x`, a nested `!` inside the substitution (`! true \| git checkout -b x "$(true; ! true; true)" && git commit -m x`) and `! true \| ` newline with a trailing space then the switch, all refused on `main` | A3 |
| T4 | Stay allowed on `main`: create-or-switch with `checkout` and with `switch -c`/`switch`; `git fetch \|\| true && git checkout -b x && git commit -m x`; `true \|\| false && git checkout -b x && git commit -m x`; `true \|\| { git checkout -b x && git commit -m x; }`; the round 3 staged-commit chain; a `!` scope still ended by `;` at its own level; and an ended substitution leaving no state: `echo "$(! true)"; git checkout -b x && git commit -m x` and `echo "$(true \|\| git checkout -b y)"; git checkout -b x && echo "$(true && git commit -m x)"` | A4 |
| T5 | The run parameter: `_segments(command)` output unchanged with and without `runs`; runs pinned for `\|\| {`, `; } &&`, `)&&`, `\|\|(`, `);`, `()`, `))`, a substitution's inherited run and an empty group's restored run (a private-helper test, kept small) | A2, A5 |
| T6 | See below. | A5 |

T6 in full. The existing suite passes unmodified, and rounds 1–3's criteria are re-checked.
The differential runs at step 6:
- **Baseline.** `git show 43eeea3:.claude/hooks/guard_git.py`, loaded from the scratchpad
  with `.claude/hooks` on `sys.path` and registered in `sys.modules`.
- **Corpus.** Every `(command, branch)` the suite passes to `violation`, captured with a
  scratch `-p` plugin.
- **Variants.** Prefixes `true || `, `false || `, `git status || `, `! true | ` and
  `coproc `, and the suffix ` "$(true && true)"` on the first switch where there is one;
  branches `main` and `feat/x`.
- **What goes to bash.** Only differing rows. Bash runs with `git()` keeping HEAD in a file,
  `PATH=/usr/bin:/bin`, `sudo`, `doas`, `nohup` and `env` shadowed, stdin closed, a timeout,
  no hostile nesting. **Before trusting it, the oracle must show `git commit -m x` alone on
  `main` printing `COMMIT on main`** (round 2's oracle ran with an empty `PATH` and could not
  register a commit). PowerShell-only inputs are skipped and listed.
- **Pass condition.** Every difference involves `||` or a `!`/`coproc` scope, the oracle
  agrees or the new refusal is play-safe, and zero rows where the guard allows a commit or
  push that bash lands on `main`.

### Risks

- **A run loses an operator.** Guide 2 splits raw operators so it should not; if a test shows
  an A2 or A3 form allowed or an A4 form refused because a run is wrong, fixing the split is
  inside the build; if it needs a different `_segments` shape than guide 2, halt.
- **Round 3 tests move.** The `negating` re-keying should only narrow when it clears. If an
  existing round 3 test changes outcome, halt — unless it is a refusal that becomes a
  refusal for the same reason (no change in outcome).
- **The cause is elsewhere.** If the build finds an A1–A3 form that the operand union and
  the re-keyed `negating` cannot close, halt.
- **Over-widening.** Union only ever adds branches, so an error in the key errs toward
  refusing. Any new refusal of an A4 form is a bug to fix, not a cost to pin.
  *Corrected in step 5:* the union applies only when an operator reaches the operand's own
  key, so a key that is wrong can also miss it. Three such errors turned up: a group opened
  inside a substitution raised the outer count, state at a depth outlived its substitution
  into a sibling, and `;;` ended no list. The first is fixed (section 3); the last two were
  over-refusals and are fixed. The one left, a word that only looks like an operator, is
  listed in section 5 and the module docstring as a known miss.

### Coverage

- **Every criterion has a Public API entry:** A1–A5 through `violation`.
- **Every criterion has a test intent:** A1→T1, A2→T2 (and T5), A3→T3, A4→T4, A5→T5 and T6.
- **Nothing in the Public API lacks a criterion.** No new public surface.

Re-checked after the critique: the Public API is unchanged; T2–T5 gained cases, all still
under A2–A5.

### Critique

`plan-critic` verdict: accept with changes. Every finding applied:

1. **Runs built from `pending` lose `(` and `)` glued to an operator (`)&&`, `||(`, `);`), so
   `true || (git checkout -b x)&&git commit` stayed allowed.** Applied: guide 2 keeps a raw
   operator list beside `pending`, saved and restored with it; T2 and T5 gained the glued
   forms; Risks updated.
2. **Walking pieces one at a time made a newline after `||`, `|` or `&&` a list end, which
   `_join` never did — a new hole for `||` and a regression for round 3's `!`.** Applied:
   guides 4 and 6 count a newline as a list end only when the run holds no other operator;
   T2 and T3 gained trailing-space newline cases.
3. **The `negating` key's level and what happens when a substitution ends were undecided;
   one reading opens an A3-class hole, the other over-refuses.** Applied: guide 6 makes
   `negating` a set of keys at the segment's own depth; guide 4 drops operand entries and
   keys deeper than the current segment before walking its run; T3 and T4 gained the nested
   and ended-substitution cases.
4. **Leftover template text in Builds on.** Applied: removed.

---

## 3. Implementation notes

> Written in step 3. Only deviations from the plan above, each with its reason. "Built as
> planned" is a complete and good entry. On a fix round, also the reproduction test's red
> run, pasted here before the fix was written — step 6 cites it.

**Reproduction, red before the fix** (`pytest tests/test_guard_git.py -k after_an_or_switch`):

```
>       assert violation(command, PROTECTED).startswith(COMMIT_REASON)
E       AssertionError: assert False
E        +  where '' = violation('git status || git checkout -b x && git commit -m x', 'main')
FAILED tests/test_guard_git.py::test_violation_refuses_a_commit_after_an_or_switch_on_main
====================== 1 failed, 951 deselected in 0.59s =======================
```

It fails as the Defect block's Observed row says: `violation` returns `""`.

**Deviations from the plan.** Built as planned, with these private choices: `_walk_run` is the
helper that reads one segment's run (guides 3, 4 and 6), and `_OPERATORS` and the `_Key` alias
sit beside `_LIST_ENDS`. A list end or close matches keys exactly, as the plan says. After the
fix the reproduction is green and the suite is 1043 passed with no existing test touched.

**Step 5 production changes** (all in `.claude/hooks/guard_git.py`; the three below were found
by the step 5 readers, checked against bash and against 43eeea3, and each had a red test first):

- **A run carries the depth each operator was written at** (a deviation from guides 2-3).
  `runs` is now `list[tuple[tuple[int, str], ...]]` (`_Run`): `(depth, operator)` pairs instead
  of bare operators, and `_walk_run` takes each pair's own level instead of
  `min(depth, previous depth)`. Reason: a substitution's first segment inherits the outer run
  and then collects what is written inside the substitution, and one level for both let a
  `$( (true) )` raise the outer group count, after which the `&&` missed its `||` operand
  (`true || git checkout -b x "$( (true) )" && git commit -m x` allowed; bash commits on `main`).
  Also removed: the `previous_depth` bookkeeping in `_judge`.
- **A substitution's close is a marker.** `_segments` leaves `(depth, "$)")` (`_CLOSED`) at the
  front of the run of whatever follows a closed substitution; `_walk_run` ends every `||` operand,
  `!`/`coproc` scope and group count at that depth or deeper. Reason: state at a depth ended only
  when the depth fell, so two sibling substitutions shared it (`echo "$(true || git checkout -b
  y)" "$(git checkout -b x && git commit -m x)"` refused; bash commits on `x`; the `$(! true)`
  form was refused at 43eeea3 too, an older over-refusal now fixed).
- **`;;`, `;&` and `;;&` are in `_LIST_ENDS`.** A `case` clause's terminator ends the clause's last
  list, so `case $v in a) true || git checkout -b y ;; b) git checkout -b x && git commit -m x ;;
  esac` is allowed (the step 4 code refused it, both the `||` and the `!` form; 43eeea3 allowed the `!` form).
- **Docs**: the `_walk_run` newline rule, the `_LIST_ENDS` comment, the `_segments` docstring on
  a substitution's first run, the `_judge` comment, the module docstring and STRUCTURE.md (the
  `&&`-replaces sentence now names the `||` exception; the `!` scope names the `case`
  terminators; both list the new known miss) and the Defect row's line numbers.

---

## 4. Verification log

> Written in step 4: the static half. Command output, not a summary of it.

| Check | Result |
|---|---|
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `41 files already formatted` |
| `mypy` | `Success: no issues found in 11 source files` |
| `pytest -q` | `1043 passed` |
| Plan completeness | every signature in the Public API table exists as written: `violation(command: str, branch: str) -> str` unchanged; no public name added (`_walk_run`, `_OPERATORS`, `_Key`, `_segments(runs=)` are private) |
| `STRUCTURE.md` | in sync (see auditor) |
| `python -m <package>.<module>` | no new module; `PYTHONPATH=src python -m template_repo.hello_world` prints `Hello, World!` (package not pip-installed in this venv) |

**structure-auditor** (run before this step): one finding, the `!`/`coproc` scope prose
(STRUCTURE.md and the module docstring) said `||` ends the scope but `_walk_run` tested `||`
before `_LIST_ENDS` and never cleared `negating`. Classified as a code deviation from plan
guide 6 (authoritative: a `negating` key is cleared by any `_LIST_ENDS` operator at its key,
`||` included). Fixed in `_walk_run`: an `||` now does `negating.discard(key)` at exactly its
key, and still opens or extends the operand. The `_walk_run` docstring says so; the module
docstring and STRUCTURE.md already read that way and are unchanged. Checked on `main`:
`! git diff --quiet || { git checkout -b feat/x && git commit -m x; }` allowed;
`! git diff --quiet || git checkout -b x && git commit -m x` refused (operand rule). All
other round 4 and round 3 tests unchanged and green. Everything else the auditor checked
(tables, `||` trust paragraph, round 4 tests paragraph) was accurate.

---

## 5. Test log

> Written in step 5: the dynamic half.

Two test-designers (`input-space`, `contract`) read the code and the plan; their cases were merged,
each bash claim run through an oracle (`git` shadowed by a function keeping HEAD in a file,
`PATH=/usr/bin:/bin`, stdin closed, a timeout), and every refused form was shown landing on `main`
and every allowed one not. The oracle first showed a plain `git commit -m x` printing
`COMMIT on main`. 118 tests added (1043 to 1161 passed); the existing tests are unchanged.

| Intent | Test names | Result |
|---|---|---|
| T1 | `test_violation_refuses_a_commit_after_an_or_switch_on_main` (step 3, unchanged: red then green) | pass |
| T2 | `test_violation_refuses_a_commit_after_every_or_operand_form` (27 forms), `..._a_push_of_head_after_an_or_switch_on_main`, `..._a_named_or_switch_that_may_not_have_run_from_a_branch`, `..._an_or_switch_after_a_switch_to_main_from_a_branch` (2), `..._a_push_of_head_after_a_switch_to_main_from_a_branch`, `..._an_or_switch_across_line_forms` (4), `..._an_or_whose_left_switch_may_have_failed` (2), `..._refuses_an_or_switch_in_a_deep_chain_quickly` | pass |
| T3 | `test_violation_keeps_a_negation_through_the_substitutions_inside_it` (9: `&&`, `;`, backticks, `coproc`, `\|\|`, nested `!`, an `\|\|` inside, a newline), `test_violation_ends_a_negation_at_an_or_of_its_own` | pass |
| T4 | `test_violation_still_allows_a_switch_that_certainly_ran` (8), `test_violation_unions_both_sides_of_an_or_for_the_and_after_it` (5), `..._closes_an_or_operand_when_its_substitution_ends`, `..._at_a_list_end` (2), `..._when_its_group_closes`, `..._keeps_an_or_operand_in_a_heredoc_body_as_data`, `..._ends_a_negation_at_a_list_end_of_its_own` (2), `..._leaves_the_or_rule_alone_off_main` (2), `..._allows_a_dangling_or` (3), `..._refuses_a_leading_or_that_names_a_commit` | pass |
| T5 | `test_segments_hands_out_each_run_as_written` (18), `test_segments_gives_the_same_segments_with_and_without_runs` (11) | pass |
| Fixed in step 5 (a) | `test_violation_reads_a_group_opened_inside_a_substitution_as_its_own` (5) | red on step 4's code (4 of 5), green after |
| Fixed in step 5 (b) | `test_violation_does_not_carry_state_into_a_sibling_substitution` (2) | red on step 4's code, green after |
| Fixed in step 5 (c) | `test_violation_ends_a_scope_at_a_case_clause_terminator` (6: `\|\|` and `!` times `;;`, `;&`, `;;&`) | red on step 4's code, green after |
| Pinned | `test_violation_pins_a_group_after_a_negation_ended_by_a_newline_as_refused` | pass (refused, as at 43eeea3) |
| T6 | the differential and the allowed-rows run, both in section 6 | pass (step 6) |

Red run of the three groups on step 4's code (commit c37bb2e): `12 failed, 1029 passed`.
After the fixes: `1161 passed`. Against 43eeea3 over every allowed and refused form above, the only
differences are the intended ones: the `||` and `!` leak forms newly refused, the `$(! true)`
sibling and (unchanged) the `!`/`;;` forms allowed; no row where the guard allows what bash lands
on `main`, except the ones under the next heading.

Reader cases applied or rebutted:

| Reader case | What was done |
|---|---|
| input-space 1, 2 (quoted separator word, literal brace/paren word) | Rebutted as this round's fault, not a defect of its code: a different root cause, pre-existing since round 1, listed below. No test asserts the current allow. |
| input-space 3 (substitution opening with a group) | Confirmed in bash; fixed (production change 1); test written red first. |
| input-space 4, contract 4 (union of both sides) | `test_violation_unions_both_sides_of_an_or_for_the_and_after_it` and `..._an_or_whose_left_switch_may_have_failed`; the refused cases use `feat/x`, which exists, so bash reaches the right side. |
| input-space 5, contract 9 (line forms) | Written (4 forms); the `\r\n` form was dropped: bash reads `\r` as a word, the switch runs and no commit reaches `main`, so the refusal is a harmless over-refusal not worth pinning. |
| input-space 6, contract 12 (substitution/group ending) | Written. |
| input-space 7 (heredoc body substitution) | Written in `OR_OPERAND_FORMS`; verified in bash. |
| input-space 8 | Checked against 43eeea3: refused there too, bash commits on `x`. Pinned as an accepted over-refusal. |
| input-space 9 (degenerate `\|\|`) | Written; `\|\| git commit -m x` is a bash syntax error and is refused as it was, pinned as such. |
| input-space 10 (deep chains) | Written, limit 5 s (measured 0.2 s). |
| input-space 11, contract 8, 10, 11 | Written (`OR_OPERAND_FORMS`, branch-origin tests, the heredoc data case). |
| input-space 12 | Written (`leaves_the_or_rule_alone_off_main`); the detached `""` case included. |
| input-space `_segments` 1-3 | Written (T5). `_segments` 4 (quoted separator word run) not written: it would document the wrong reading. |
| contract 1 | Same as input-space 1, 2: different root cause. |
| contract 2 (`;;` etc.) | Confirmed; fixed (production change 3). The step 4 code refused the `!` form too, a regression against 43eeea3 that is now closed. |
| contract 3 (sibling state) | Confirmed; fixed (production change 2). The `!` form was refused at 43eeea3: an older over-refusal, now fixed. |
| contract 5, 6, 7 | Written. |
| Contradictions 1-3 (Risks claim, `_segments` docstring, `_judge` comment) | Docstrings and comments corrected; the Risks line is corrected in section 2 (the key can err toward allowing; three such errors fixed, one left). |
| Contradictions 4, 5 (`_walk_run` newline, `_LIST_ENDS`) | Docstring and comment rewritten. |
| Contradiction 5/contract (STRUCTURE.md line 354) | Sentence now names the `||` exception. |
| Contradiction 6/contract (stale line numbers) | Updated in the Defect row, with the 43eeea3 lines noted. |
| Contradiction 7 | STRUCTURE.md's round 4 tests paragraph extended. |

### Different root cause — for the user

Not fixed and not tested: `shlex` removes quoting, so the tokenizer takes a quoted separator word
and a literal brace or paren word for a real operator. This is older than round 4 (`segments('echo
";" x')` splits into two segments since round 1, and 43eeea3 allows every row below), and it moves
the key `_walk_run` reads, so an `||` operand or a `!` scope ends or opens a group early. Each row
below prints `COMMIT on main` in bash (the oracle as above) and the guard allows it, at 43eeea3 and
now:

| Form | Bash |
|---|---|
| `true \|\| echo ";" \| git checkout -b x && git commit -m x` | `COMMIT on main` |
| `true \|\| echo "&&" \| git checkout -b x && git commit -m x` | `COMMIT on main` |
| `true \|\| echo '&' \| git checkout -b x && git commit -m x` | `COMMIT on main` |
| `true \|\| find . -maxdepth 0 -exec true \; \| git checkout -b x && git commit -m x` | `COMMIT on main` |
| `true \|\| echo { \| git checkout -b x && git commit -m x` | `COMMIT on main` |
| `true \|\| echo '(' \| git checkout -b x && git commit -m x` | `COMMIT on main` |
| `{ true \|\| echo } \| git checkout -b x && git commit -m x; }` | `COMMIT on main` |
| `{ true \|\| echo ')' \| git checkout -b x && git commit -m x; }` | `COMMIT on main` |
| `! true \| echo ";" \| git checkout -b feat/x && git commit -m x` | `COMMIT on main` |

A fix reads the token stream with quoting kept (or marks each token as quoted) so a quoted word is
never an operator; it touches `_lex`, `_is_separator` and every consumer of `segments`, which is a
round of its own. The module docstring and STRUCTURE.md now list it as a known miss.

Edge cases considered and deliberately skipped, with reasons:

- A `\r` after the `||` (bash reads it as a word; harmless over-refusal).
- PowerShell `-or` and `&&`/`||`: the same strings, and `-or` is an expression operator.
- Purity and idempotency: `violation` takes strings and keeps no state; the existing tests cover it.
- A `_segments` pin for a quoted separator word: it would document the wrong reading above.
- Nesting past the guard's limit with `||`: round 2's limit tests cover the pre-pass, which the
  runs sit behind.

---

## 6. Concept check

> Written in step 6, against section 1 — not against section 2. The question is whether
> the thing built is the thing agreed, not whether it matches the plan.

| # | Criterion | Met | Evidence |
|---|---|---|---|
| A1 | `git status \|\| git checkout -b x && git commit -m x` on `main` is refused with the commit reason | met | Red: section 3's run of `test_violation_refuses_a_commit_after_an_or_switch_on_main` against the step 2 code, `assert False ... where '' = violation('git status \|\| git checkout -b x && git commit -m x', 'main')`, 1 failed. Green: the same test in the 1161-passed run now, and `violation(...)` returns the commit reason (`r4c/crit.py`); the module at 43eeea3 returns `""` for it. In bash with `git` shadowed the command prints a commit on `main`. |
| A2 | Every other `\|\|`-operand form in the Class row refused on `main` (the named switch from `feat/y`) | met | `r4c/crit.py` runs 30 forms from A1-A3 (later stage `\|` and `\|&`; `time`, `sudo`, `x=1`, a redirection before the switch; a substitution on the switch; chained `\|\|`; `\|\|` after an `&&` chain; `coproc true \|\|`; a heredoc; `&&` ending a line; further `&&` segments; the commit inside `$( )`; the whole inside `{ }`, `$( )` and `if`; a push of `HEAD`; glued subshells; a trailing-space newline; the named switch from `feat/y`): 30 of 30 refused; 28 of them were allowed by the 43eeea3 module (the other two, `true \|\| if git checkout -b x; then :; fi && git commit -m x` and `true \|\|(git checkout -b x) && git commit -m x`, were already refused by `_join`, as the Class row says). Tests `test_violation_refuses_a_commit_after_every_or_operand_form` (27 forms) and the A2 tests listed in section 5. |
| A3 | The `negating` depth leak closed: `! true \| git checkout -b feat/x "$(true && true)" && git commit -m x`, its `"$(true; true)"` and backtick forms, and `true \|\| git checkout -b x "$(true && true)" && git commit -m x` refused on `main` | met | `r4c/crit.py`: the four named forms refused, all allowed at 43eeea3. `test_violation_keeps_a_negation_through_the_substitutions_inside_it` (9 forms). The oracle (shadow below) shows the `!` form landing on `main` when the switch fails. |
| A4 | The five named forms stay allowed on `main` | met | `r4c/crit.py`: 5 of 5 allowed. `test_violation_still_allows_a_switch_that_certainly_ran` (8) and `test_violation_unions_both_sides_of_an_or_for_the_and_after_it` (5). Any new refusal of an A4 form would be a bug: none found in the differential's 683 + 255 new refusals (every one carries an `\|\|`, `!` or `coproc`). |
| A5 | Nothing else changed: the existing tests pass unmodified; rounds 1-3 still hold; differential against 43eeea3 with zero rows where the guard allows what bash lands on `main` | met | `git diff 43eeea3 -- tests/` removes no line (393 added, 118 tests; 1043 to 1161 passed). Differential below: 0 bypass rows. Rounds 1-3 below. |

**T6 differential** (`r4c/diff.py`, `r4c/allowed.py`; module at 43eeea3 as `base`, loaded from the scratchpad with `.claude/hooks` on `sys.path` and registered in `sys.modules`).

- **Oracle, shown live first.** `git commit -m x` alone with `START=main` returns `(True, 'ok')`: the shadow prints `COMMIT@main`. Bash 5.2, `PATH=/usr/bin:/bin`, `sudo`/`doas`/`nohup`/`env` shadowed, stdin `/dev/null`, 10 s timeout, a new session per run (no `pkill -f`), no deeply nested input. One correction to the step 5 shadow: it left HEAD alone when a `git checkout`/`switch` argument was an empty string (a `"$(true && true)"` expands to one), so a plain `git checkout -b feat/x "$(true && true)" && git commit` landed on `main` in it for the wrong reason. Real git fails on an empty argument, so the shadow now returns 1 for one (`r4c/diff.py` line 10). With it, the plain form no longer lands and the `!` form does (the checkout failed, the negation made that a success).
- **Corpus.** Every `(command, branch)` the suite passes to `violation`, captured with a scratch `-p` plugin: 1,048 pairs, 835 distinct commands. Thirteen variants (plain; `if`, `while`, `for` wrappers; `!`, `coproc`, `true \|\| `, `false \|\| `, `git status \|\| `, `! true \| ` prefixes; the ` "$(true && true)"` suffix on the first switch alone and after `true \|\| ` and `! true \| `), branches `main` and `feat/x`: **18,260 rows**.
- **Differing: 1,003.** Oracle-run: 977 (plus 2 `do {` rows run by hand, below). Skipped: 22 for length or nesting (a 300-character cap and counts of `$(`, `(` and backticks, against fork-bombs) and 2 more that are a nest of braces; no PowerShell-only row remained once the filter stopped reading `` `true `` as a PowerShell escape (the 4 rows it first caught are the nests above and the two `for`/`while ... do { true \|\| ... }` loops, which are bash and were run: bash lands on `main`, the new guard refuses).
- **Result of the 977.**

| Direction | Bash lands on `main` | Bash does not | Syntax error in bash |
|---|---|---|---|
| New refuses, 43eeea3 allowed | 683 | 255 (play-safe: a switch that may have run, but did not here, or a left side that succeeded) | 28 (`! true \| ! cmd`, `coproc ! ...`, a line starting `&&`; harmless over-refusal) |
| New allows, 43eeea3 refused | 0 | 11 | 0 |

- **Every difference involves `||`, `!` or `coproc`** (the check script flags any other; none flagged). The 11 rows the new guard allows and 43eeea3 refused, all of which bash does not land on `main`: nine are the `$(! true)` sibling step 5 recorded (`echo "$(! true)" "$(git checkout -b x && git commit -m x)"` and its `if`, `while`, `for`, `!`, `coproc`, `true \|\|`, `false \|\|` and `git status \|\|` wrappers) and two are `! ( true \|\| git checkout -b y ); git checkout -b x && git commit -m x` and its `coproc ( ... )` twin, where the `;` after the group now ends the negation (the same scope rule: bash commits on `x`). No `case` terminator row appears: the corpus holds none that differ.
- **Bypass rows: 0.** No row in which the new guard allows a commit or push that bash lands on `main` and 43eeea3 refused.
- **Tokenizer-attributed rows: 0 in the corpus; the 9 recorded ones re-run.** The nine forms of section 5's "Different root cause" table: all nine are allowed by the new guard and by 43eeea3, and bash lands on `main` for eight of them, each carrying a quoted separator word (`";"`, `"&&"`, `'&'`, `\;`, `'('`, `')'`) or a literal `{` or `}` word, which `shlex` hands over as an operator. The ninth, `! true \| echo ";" \| git checkout -b feat/x && git commit -m x`, does not land under this oracle: the negated pipeline succeeds, so the `&&` skips the commit; it would land with a failing checkout. Section 5's table row for it overstates that case; the guard's allow is the same either way. No change.
- **The allowed-rows run.** Every row the new guard allows, from the 18,260: 8,355, of which 8,046 went to bash (309 skipped as hostile or PowerShell). 7,178 do not land on `main`, 827 are syntax errors in bash, 5 time out (`while true; do true ||\nbreak; done`, a loop in my wrapper that never breaks, with no git in it), and **36 land on `main`**. Each of the 36 is allowed by 43eeea3 too and none is a round 4 bypass:

| Rows | Form | Attribution |
|---|---|---|
| 16 | `echo "${x:-'$(git commit -m x)'}"`, `echo "${x:-'}" "$(git commit -m x)" "'}"` | recorded miss: a single quote inside a quoted `${ }` (round 2, module docstring) |
| 18 | `echo $'it\'s'; git co""mmit -m x # '` and `git $'\x63ommit' -m x` | recorded misses: split quotes and a hex escape in the subcommand (round 1, module docstring) |
| 1 | `coproc for i in 1 2; do git commit -m x; done; git checkout main` from `feat/x` | out of scope in section 1: a `coproc` loop racing a foreground switch |
| 1 | `git checkout -b feat/y "$(true && true)"&&\r\ngit commit -m "$(date)"\r\n` | not recorded as a miss: a carriage return after `&&` is read as whitespace, so the guard joins the lines, while bash reads `\r` as a word and the next line runs on its own. The switch fails in the shadow (empty argument), so the commit lands on `main`. Neither `\|\|` nor `!`; the same lexing family as the tokenizer flaw (a literal read as syntax). Listed for round 5. |

(16 + 18 + 1 + 1 = 36: the same few base forms repeated across the wrapper and prefix variants.)

**Plan and Class row read against the diff.** The Root cause row names `ok = here | {target} if unsure else {target}` in `_judge` and the any-depth clear of `negating`. The diff leaves line 1672's replacement in place for commands inside an operand and takes what leaves the operand as the union (`_walk_run` returning `widened`, added to `ok` before an `&&` reads it), and re-keys `negating` by `(depth, group)`: the cause, not the site. The Class row's two parts each have tests; "Already refused, by `_join`" forms are pinned as still refused. Scope `the class`, plus the negating leak: three extra defects found at step 5 (a group inside a substitution, a sibling substitution, `case` terminators) were inside the same mechanism (`_walk_run`'s keys), each with a red test first; they fix the new code's own over- and under-reach, and none widened the promise.

Drift found, and what was done about it:

- **None to the criteria.** No criterion is unmet and none is wrong; no halt.
- **Structure auditor** (six prose items, each checked against `_walk_run` and `_LIST_ENDS`): applied in `STRUCTURE.md` and the module docstring: the operand's extent (adds `&`, `case` terminators, the newline rule, the closing group or substitution; module docstring too), the `!`/`coproc` scope sentence (closing group or substitution; module docstring too), the round 4 tests entry (private names removed, the `!`/`coproc` bullet, the union-and-closing bullet) and the shell-lexing intro (round 4 named).
- **The tokenizer flaw** is out of scope by the user's decision: **round 5 after this round.** It is recorded in section 5 under "Different root cause — for the user", in the module docstring and in STRUCTURE.md. The carriage-return row above belongs in round 5's list.
- **Oracle correction** (empty argument) recorded above; it changes no verdict, only the reason a few forms land.

### Earlier rounds still hold

> Later rounds only. Re-check every acceptance criterion from every earlier round in this
> folder: this round changed code they depend on, and their tests passing is necessary but
> not sufficient — a criterion can be satisfied by tests that no longer describe what the
> feature does.

Re-run directly against the code as it stands: round 1's `r6/r1.py` (0 fails), round 2's `r6/a.py` (49 of 49) and `r6/a2am.py` (0 fails), the round 3 rows in `r4c/r3.py` (28 of 28; the five compound-command forms of its A6 all still refused on `main`, as at 43eeea3), and the 1161 tests.

| Round | # | Criterion | Still met | Evidence |
|---|---|---|---|---|
| 1 | A1 | The reported `python3 - <<'EOF'` with a stray quote is allowed on `main` | yes | `r6/r1.py`, 0 fails |
| 1 | A2 | Heredoc bodies read as bash reads them; body substitutions judged; `commit -F -` | yes | `r6/r1.py`; heredoc tests unmodified |
| 1 | A3 | `#` read as bash reads it | yes | `r6/r1.py` A3 rows |
| 1 | A4 | Backslash-newline joins | yes | `r6/r1.py` A4 rows |
| 1 | A5 | Unmodelled forms play safe on `main` only | yes | `r6/r1.py`; `UNMODELLED_OPENERS` untouched |
| 1 | A6 | Changes nothing else; accepted `&&` plus `$'...'` cost | yes | `r6/r1.py` "A6 cost &&+$'" refused; no test line removed since 43eeea3 |
| 2 | A1 | `echo "$(git commit -m x)"` refused on `main` | yes | `r6/a.py`, 49 of 49 |
| 2 | A2 | `$( )` in every position; heredoc closed by the substitution's `)` | yes | `r6/a.py`, `r6/a2am.py`, 0 fails |
| 2 | A3 | Backticks in every position | yes | `r6/a.py` |
| 2 | A4 | Process substitution | yes | `r6/a.py` |
| 2 | A5 | A substitution runs before its command; `&&` trust carries in | yes | `r6/a.py`; the sibling and group-in-substitution fixes touch only the `\|\|`/`!` state |
| 2 | A6 | `main` as any branch it could land on | yes | `r6/a.py`; the differential's 18,260 rows agree with bash |
| 2 | A7 | Funsub plays safe | yes | `r6/a.py` |
| 2 | A8 | Harmless substitutions allowed; the pipeline's commit form | yes | `r6/a.py` A8 rows; the pipeline form with a switch before it is allowed on `main` in the allowed-rows run |
| 2 | A9 | Changes nothing else | yes | its six test edits untouched; no line removed |
| 3 | A1 | `if git commit -m x; then echo ok; fi` refused | yes | `r4c/r3.py` |
| 3 | A2 | Git seen after every reserved word | yes | `r4c/r3.py`, 12 forms plus the push from a branch |
| 3 | A3 | A switch after a reserved word counted | yes | `r4c/r3.py`, 3 forms |
| 3 | A4 | Play safe on trust; `&&` chain stays allowed | yes | `r4c/r3.py`, 4 refused and `git checkout -b feat/x && git commit -m x` allowed; `! git diff ... \|\| { ... }` allowed |
| 3 | A5 | A switch anywhere in a loop counts for the whole loop | yes | `r4c/r3.py`; the loop variants in the differential |
| 3 | A6 | Words that are not commands stay words; compound commands keep their outcome | yes | `r4c/r3.py`: `echo if git commit` and `for git in ...` allowed on `main`, `git commit -m then` and the `-C` switch allowed from a branch; the five compound forms refused as before |
| 3 | A7 | Changes nothing else; differential matches bash | yes | the 13-variant differential here includes the reserved-word prefixes: 0 bypass rows |

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
