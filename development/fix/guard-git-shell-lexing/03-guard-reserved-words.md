# The git guard steps over shell reserved words

<!-- claude-plan step=2 status=active -->

| Field | Value |
|---|---|
| Feature | `fix/guard-git-shell-lexing` |
| Round | `3` |
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
| 2 | `02-guard-substitutions-in-words.md` | Every command substitution (`$( )` in any position, backticks, `<( )`/`>( )`, inside arithmetic and heredoc bodies) extracted and judged before the command that contains it, `Segment.depth` and `SUBSTITUTED`; a commit or push refused when `main` is any branch it could land on; heredocs inside a substitution closing on `EOF)` as in bash; funsub plays safe; the guard never crashes open. 853 tests. |

This round came from recommendation `R2` of round 1, which read:

> **Make `_command_index` step over the shell's reserved words — `if`, `then`, `else`, `elif`, `do`, `while`, `until`, `!` — as it steps over assignments and redirections.** — A live commit-to-`main` bypass in ordinary shell grammar. Verified in bash on `main`: `if git commit -m x; then echo ok; fi`, `if git diff --quiet; then :; else git commit -am x; fi`, `for b in a; do git push origin main; done` and `! git commit -m x` all run git and are all allowed, before and after this round. A different cause from R1 (grammar, not lexing), and close to the bar; the reader ranks it below R1.

Round 2's `defect-class` reader added a starting point: `_scan` already knows where a command
starts after `then`, `do`, `else`, `elif`, `!` and `time` (`_COMMAND_LEADERS`, used to place
`case`), while `_command_index`, which finds the git command, does not. One shared set, extended
with `if`, `while`, `until` and `{`, avoids two diverging lists.

What is already on the branch that this round must not break: every acceptance criterion of
rounds 1 and 2 (step 6 re-checks them), the 853 guard tests, and in particular `&&` trust, the
set-of-branches rule and substitution extraction.

---

## 1. Concept

### Defect

| Field | Value |
|---|---|
| Observed | Bash runs a git command that follows a shell reserved word, but `guard_git.violation` allows it on `main`. A branch switch after a reserved word is equally invisible, so a later commit outside the compound command is judged on the starting branch. |
| Expected | `CLAUDE.md` and the module docstring: the guard refuses a commit or push that would land on `main`, "including inside a compound command". |
| Reproduction | Scratch `r3_repro.py` and `dc_r3.py`; bash with `git` shadowed and HEAD kept in a file. On `main`, bash commits or pushes on `main` and the guard allows: `if git commit -m x; then echo ok; fi`; `if git diff --quiet; then :; else git commit -am x; fi`; `for b in a; do git push origin main; done`; `! git commit -m x`; `while git commit -m x; do break; done`; `until git commit -m x; do :; done`; `if true; then git commit -m x; fi`; `if false; then :; elif git commit -m x; then :; fi`; `coproc git commit -m x`; `until git checkout fail; do git commit -m x; break; done`; `for ((i=0;i<1;i++)); do git commit -m x; done`; `true && if true; then git commit -m x; fi`; a reserved word after `\|`; `x=$(if true; then git commit -m x; fi)`; `if ! git checkout -b feat/x; then git commit -m x; fi`; `! ! git commit -m x`. From `feat/y`, bash commits on `main` and the guard allows: `if true; then git checkout main; fi; git commit -m x`, `for i in 1; do git checkout main; done && git commit -m x`, `! git checkout main; git commit -m x`, and the loop back-edge `for i in 1 2; do git commit -m x; git checkout main; done`. Already refused: `{ … }`, `time git commit`, `case a in a) git commit;; esac`, functions, `[[ ]] && git commit`, `(( 1 )) && git commit`, `coproc C { git commit; }`. Allowed today only because the guard sees no git at all, while bash commits on `feat/x`: `if git checkout -b feat/x; then git commit -m x; fi`, `while git checkout -b feat/x; do git commit -m x; break; done`, `if true; git checkout -b feat/x; then git commit -m x; fi`. |
| Root cause | The guard models shell reserved words as ordinary words. (1) `.claude/hooks/guard_git.py:363`, `_command_index`, steps over assignments, redirections, file descriptors and `WRAPPERS` but never reserved words, so the command name it reads is `if`/`then`/`do`/`!`/`coproc`, and `git_subcommand` (:1237), and through it `switch_target`, never sees git. (2) `_judge` (:1428-1430) decides trust only from `segment.separator` (`ok` for `&&`, every possible branch otherwise), so what a reserved word does to trust (bash: `then` and `while … do` run only if the condition list's last command succeeded, `else` and `until … do` when it failed, `!` inverts) is not expressed anywhere. Round 2's `_COMMAND_LEADERS` (:750) is a second, diverging list of command-position words, used only to place `case`. |
| Introduced by | Older than every round: the original guard (`41b4f32`) read `tokens[0]`; `5b01090` (2026-09-21) kept the miss. |
| Class | Reserved words that take a command next — `if`, `then`, `else`, `elif`, `while`, `until`, `do`, `!`, `coproc` (`time` is already a wrapper, `{` already a separator) — chained (`if !`, `! !`, `time !`), after any separator, inside substitutions; hidden branch switches as well as hidden commits and pushes; loop back-edges, where a switch late in a loop body governs the next iteration. Not to be stepped over: `for`, `select`, `case`, `function`, `in` (the next word is a name). Same shape, different cause: a function body judged where it is defined, not where it is called; `command`/`exec`/`builtin`/`eval` before git (the deliberately incomplete `WRAPPERS`). |
| Blast radius | `_command_index` feeds `git_subcommand` and `_redirected` (:420 — a `then git -C other checkout main` must stay ignored); `switch_target` is reached through `git_subcommand`; trust lives in `_judge`; `_COMMAND_LEADERS` becomes the one shared set. Tests: only `tests/test_guard_git.py:2681` mentions `if`, expects a refusal and survives. Decided here: the three forms allowed today only by accident become refusals on `main` (A4's accepted cost). |
| Scope | `the class` — the user's decision — with the trust model played safe (every reserved-word join uncertain, `!` breaking trust: the user's choice over modelling bash exactly), and loops widened so any switch inside a loop counts for the whole loop (the user's choice). Functions called after a switch stay out (the user's choice), recorded only in this file — the user asked that nothing beyond its introduction be kept in `DEVELOPMENT.md`, this being a template repository. |

Critique — the `diagnosis-critic`'s findings (verdict: cause confirmed, class incomplete) and what was done with each:

1. A fix only in `_command_index` cannot express trust, which the separator carries — applied: the root cause names both sites.
2. A reserved word hides a branch switch too, which bites from a branch — applied: A3.
3. Loop back-edges survive a naive fix; functions are judged where defined — applied: loops are A5, functions out of scope by name.
4. `!`, `if !` and `! !` must break trust, and chained words must loop — applied: A2 and A4.
5. `for`/`select`/`case`/`function`/`in` must not be stepped over; `command`/`exec`/`builtin`/`eval` belong to `WRAPPERS` — applied: A6 and out of scope.
6. History: the miss dates from `41b4f32`, not `5b01090` — applied.

### What this is

The guard learns where a command starts in shell grammar. It steps over the reserved words that
take a command next — `if`, `then`, `else`, `elif`, `while`, `until`, `do`, `!`, `coproc`, chained
— from one shared list that replaces round 2's separate one, so a git commit, push or branch
switch after any of them is judged like any other command. It plays safe on trust: a join made by
a reserved word counts as uncertain, so the branches in play are every branch possible at that
point, and `!` breaks the `&&` trust of what it negates. A branch switch anywhere inside a loop
body counts for the whole loop. The two causes removed are at `_command_index` (:363) and at the
trust decision in `_judge` (:1428).

### Why it is worth building

See the Defect block.

### Inputs and outputs

Unchanged: `violation(command, branch)` returns a refusal reason or `""`; `segments(command)`
returns the invocations or `None`. Which commands land in which outcome changes.

### How it connects to the rest of the repo

Changes `.claude/hooks/guard_git.py` (command-position words, trust in `_judge`, loops), its
tests, the module docstring and `STRUCTURE.md`'s guard section. Builds on round 2's
set-of-branches rule and substitution extraction. Cleans `DEVELOPMENT.md` back to its
introduction at the user's request.

### Explicitly out of scope

- A function called after a branch switch (`f() { git commit -m x; }; git checkout main; f`
  from a branch): its body is judged where it is defined. A different cause. Recorded here only.
- `command`, `exec`, `builtin`, `eval` before `git`: the deliberately incomplete `WRAPPERS`.
- Modelling bash's exact `if`/`else`/`while`/`until`/`!` logic: the user chose to play safe.
- The items rounds 1 and 2 recorded for later (a push destination made by a substitution,
  spelled-out subcommands, nesting past the limit off `main`, `merge`/`cherry-pick` on `main`).

### Acceptance criteria

All judged with `main` checked out unless stated; "a branch" is `feat/y`.

| # | The finished feature... |
|---|---|
| A1 | Refuses `if git commit -m x; then echo ok; fi`, which today it allows. |
| A2 | Sees git after every reserved word that takes a command: refuses `if git diff --quiet; then :; else git commit -am x; fi`, `if false; then :; elif git commit -m x; then :; fi`, `if true; then git commit -m x; fi`, `while git commit -m x; do break; done`, `until git commit -m x; do :; done`, `! git commit -m x`, `! ! git commit -m x`, `coproc git commit -m x`, `for ((i=0;i<1;i++)); do git commit -m x; done`, `true && if true; then git commit -m x; fi`, `ls \| if true; then git commit -m x; fi` and `x=$(if true; then git commit -m x; fi)`; and refuses `for b in a; do git push origin main; done` from a branch too. |
| A3 | Counts a branch switch after a reserved word: from a branch, refuses `if true; then git checkout main; fi; git commit -m x`, `for i in 1; do git checkout main; done && git commit -m x` and `! git checkout main; git commit -m x`. |
| A4 | Plays safe on trust: refuses `! git checkout -b feat/x && git commit -m x` and `if ! git checkout -b feat/x; then git commit -m x; fi`. Accepted cost: `if git checkout -b feat/x; then git commit -m x; fi` and `while git checkout -b feat/x; do git commit -m x; break; done`, allowed today only because the guard sees no git, are refused on `main`; the same with `&&` (`git checkout -b feat/x && git commit -m x`) stays allowed. |
| A5 | Counts a switch anywhere in a loop for the whole loop: from a branch, refuses `for i in 1 2; do git commit -m x; git checkout main; done` and `while true; do git commit -m x; git checkout main; break; done`. |
| A6 | Keeps words that are not commands as words: allows `echo if git commit` and `for git in commit; do :; done` on `main`, and `git commit -m then` from a branch; `{ git commit -m x; }`, `time git commit -m x`, `case a in a) git commit -m x;; esac` and both function forms keep today's outcome; a switch aimed at another repository after `then` (`if true; then git -C ../o checkout main; fi; git commit -m x` from a branch) is still ignored. |
| A7 | Changes nothing else: rounds 1 and 2 still meet their criteria; every existing test passes; and a differential against the guard at round 2's head (`8c5c2b9`) over every command the existing suite passes to the guard, plus variants that prefix it with each reserved word, agrees except where a reserved word sits at a command position — and there the new decision matches bash with `git` shadowed and HEAD in a file, or is the play-safe refusal. |

### Open questions

None.

---

## 2. Plan

### Approach

**Chosen: one shared set of command-position words, read in two places.** Round 2's private
`_COMMAND_LEADERS` becomes the single list of reserved words that take a command next: `if`,
`then`, `else`, `elif`, `while`, `until`, `do`, `!`, `coproc`, plus the `time` it already
holds. It is read in two places.

1. **`_command_index` steps over the words.** It steps over any run of them at the start of
   an invocation, before the assignments, redirections and wrappers it already skips. That
   way `git_subcommand`, `switch_target` and `_redirected` all see the git that follows.
2. **`_judge` treats a led invocation as uncertain.** The judge asks a new private helper
   which of the words led the invocation. It then plays safe:
   - An invocation led by any of the words runs on every branch possible at that point,
     even after an `&&`.
   - An invocation led by `!` does not let its own switch replace `ok`. The switch only
     widens it, because the `&&` after a negated command runs exactly when that command
     failed.
   - An invocation led by a closing word (`fi`, `done`, `esac`) also counts as uncertain.

**Loops.** Before judging, a pre-pass over the segments finds each loop. A loop runs from an
invocation whose command word is `for`, `while`, `until` or `select` to its matching `done`,
with `do` and `done` counted at invocation starts. Every branch switch inside the loop is
added to `possible` at the loop's start, so it counts for the whole loop, back-edge included.

**What this removes.** Both causes in the Root cause row: the reserved word read as the
command name, and trust decided from the separator alone.

**Rejected:**
- **Model bash's `if`/`else`/`while`/`until`/`!` logic exactly.** The user chose to play safe.
- **Have `segments()` split on reserved words as it does on `{`.** It would leave `if` as an
  empty segment rather than a leader. The `!` and trust information would then have to travel
  through the separator, which is a public `Segment` field. It also changes `segments`'
  output for every test that pins tokens.
- **A loop rule that unrolls the body twice.** It is exact for one back-edge, but fragile with
  nesting and substitutions. Widening at the loop start is simpler and safe.

### Modules

| Path | New or changed | Purpose |
|---|---|---|
| `.claude/hooks/guard_git.py` | changed | `_COMMAND_LEADERS` widened and shared; `_command_index` steps over it; new private leader and loop helpers; `_judge` plays safe on leaders, `!` and loops; module docstring |
| `tests/test_guard_git.py` | changed | New tests for A1–A6; existing tests untouched |
| `STRUCTURE.md` | changed | Guard section prose (reserved words, trust, loops) and the tests entry |

### Public API

No public signature or public constant changes. `segments`, `git_subcommand`,
`switch_target`, `push_targets_main` and `violation` keep their signatures. Their behaviour
changes as section 1 says.

| Signature | Module | Purpose | Covers |
|---|---|---|---|
| `git_subcommand(tokens: tuple[str, ...]) -> tuple[str, tuple[str, ...]]` | `guard_git.py` | Unchanged signature. Finds git after a run of leading reserved words. | A1–A3, A6 |
| `violation(command: str, branch: str) -> str` | `guard_git.py` | Unchanged signature. Judges invocations led by reserved words as uncertain, a `!`-negated switch as not trusted, and a switch inside a loop as possible across the whole loop. | A1–A7 |

Private and not listed: `_COMMAND_LEADERS` (widened), a helper that reports which leaders an
invocation starts with, and the loop pre-pass.

### Implementation guide

1. **Reproduction first (fix round).** Add
   `test_violation_refuses_a_commit_after_if_on_main`, asserting that
   `if git commit -m x; then echo ok; fi` is refused on `main` with the commit reason. Run it
   red, paste the run into section 3, and commit before any production change. If it is
   already green, halt.
2. **One list.** Widen `_COMMAND_LEADERS` to `if then else elif while until do ! coproc time`
   and check that `_scan` still places `case` correctly; the existing `case` tests must stay
   green. Add private `_CLOSERS = frozenset({"fi", "done", "esac"})`.
3. **`_command_index`.** At the top of its loop, step over a token that is exactly one of
   `_COMMAND_LEADERS`. Chains such as `if ! git`, `! ! git` and `time ! git` work because the
   loop continues. `for`, `select`, `case`, `function` and `in` are not stepped over.
4. **Leader helper.** Add a private helper that returns, for an invocation's tokens, whether
   a leader or a closer started it and whether a `!` was among the leaders.
5. **`_judge` trust.**
   - For an invocation a leader or closer started, `here` is `possible`, whatever the
     separator, except that the `SUBSTITUTED` and frame rules from round 2 still apply.
   - For a switch in an invocation that a `!` led, set `ok = here | {target}`, not `{target}`,
     and still add the target to `possible` and to every open frame.
6. **Loop pre-pass.**
   - Before the main walk, scan the segments and pair loop starts with their `done`. A loop
     start is an invocation whose first token after any leaders is `for`, `while`, `until`
     or `select`. `while` and `until` are also leaders, so check them before stepping.
     Nested loops are paired with a stack.
   - For each loop, collect the switch targets of the invocations inside it, nested loops
     and substitution depths included, ignoring redirected switches.
   - In the main walk, when the walk reaches a loop's first invocation, add those targets to
     `possible` and to `ok` before judging it.
   - An unmatched loop start runs to the end of the command. A stray `done` is ignored.
7. **Docs.** Update the module docstring (reserved words, trust, loops; functions as a known
   miss) and `STRUCTURE.md`'s guard section and tests entry.

### Test intents

| # | Must prove | Covers |
|---|---|---|
| T1 | `if git commit -m x; then echo ok; fi` is refused on `main`: red before, green after | A1 |
| T2 | Every A2 form is refused on `main` with the commit reason. The push form is refused from a branch with the push reason. Chained leaders (`if !`, `! !`, `time !`) and a leader after `&&`, `\|\|`, `\|`, `;` and a newline are covered, and so are leaders inside a substitution. | A2 |
| T3 | The three A3 hidden switches are refused from a branch. `then git checkout feat/z; fi; git commit` from a branch is allowed. | A3 |
| T4 | The two `!` forms are refused on `main`. The accepted-cost pair is refused on `main` and pinned as deliberate. `git checkout -b feat/x && git commit -m x` is still allowed on `main`. | A4 |
| T5 | Both A5 loops are refused from a branch. A loop that switches to another branch only, with a commit, is allowed from a branch. Nested loops, a loop inside a substitution and an unmatched `do` are handled without error. | A5 |
| T6 | Every A6 form keeps its stated outcome. `for`/`select`/`case`/`function`/`in` are not stepped over (`for git in commit` is allowed). The redirected switch after `then` is ignored. | A6 |
| T7 | The existing suite passes unmodified, and rounds 1 and 2's criteria are re-checked. The differential runs in step 6: baseline `git show 8c5c2b9:.claude/hooks/guard_git.py`, loaded from the scratchpad with `.claude/hooks` on `sys.path` and registered in `sys.modules`. The corpus is every `(command, branch)` the suite passes to `violation`, captured by a scratch plugin with `-p`. Variants prefix each command with `if true; then `, `while true; do `, `! `, `for i in 1; do ` (closing with `; fi`/`; break; done`/`; done` as needed) and `coproc `. Branches are `main` and `feat/x`. The oracle is bash with a `git()` that keeps HEAD in a file, with stdin closed and a timeout, and no hostile nesting sent to bash. Every difference must hold a reserved word at a command position and match the oracle or be the play-safe refusal. | A7 |

### Risks

- **A word that only looks like a leader.** `then` or `do` appearing as a command name only
  happens in shell grammar, and the guard steps over them only at an invocation's start, so
  `echo if git commit` is unaffected. If any existing test changes outcome, halt: A7 says it
  must not.
- **PowerShell.** `if ($?) { … }`, `while (…) { … }` and `do { … } while (…)` put `(` or `{`
  right after the word, and both are separators. The word becomes a one-token invocation and
  the command after `{` is a fresh segment, as today. The existing PowerShell tests must stay
  green; if not, halt.
- **Loops inside substitutions,** or a substitution inside a loop: the pre-pass works on the
  flat segment list across depths, which may widen more than needed. That direction is safe.
- **Over-refusal beyond A4's named cost.** For example, `git checkout -b feat/x && if true;
  then git commit -m x; fi` on `main` is refused. That is the play-safe model the user chose.
  Record it in section 5 and pin one example. Not a halt.
- **The cause is elsewhere.** If the build finds an A1–A5 form that stepping over leaders and
  the trust and loop rules cannot close, halt.

### Coverage

- Every criterion has a Public API entry: A1–A3 and A6 through `git_subcommand`, and all of
  them through `violation`.
- Every criterion has a test intent: A1→T1 through A7→T7.
- Nothing in the Public API lacks a criterion. No new public surface is added.

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
