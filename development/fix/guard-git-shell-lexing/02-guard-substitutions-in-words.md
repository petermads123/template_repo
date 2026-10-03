# The git guard judges command substitutions inside a word

<!-- claude-plan step=2 status=active -->

| Field | Value |
|---|---|
| Feature | `fix/guard-git-shell-lexing` |
| Round | `2` |
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
| 1 | `01-guard-git-shell-lexing.md` | A private pass (`_prepare`) in front of `shlex` in `.claude/hooks/guard_git.py`: word-start `#` comments, backslash-newline continuations and heredoc bodies read as bash reads them, with context tracking for `$( )`, `${ }`, backticks, double quotes and arithmetic; the `$( )` and backtick substitutions of an unquoted heredoc body judged as commands of their own (Halt 1); `UNMODELLED_OPENERS` and the play-safe refusal on `main`. 409 guard tests. |

This round came from recommendation `R1` of round 1, which read:

> **Judge command substitutions that sit inside a word as commands of their own — `"$( )"`, an assignment's `$( )` or backticks, backticks after the command name, and `<( )`/`>( )` process substitution — reusing the extraction this round built for unquoted heredoc bodies, each emitted after a newline so it can only add refusals.** — A live, silent commit-to-`main` bypass of the rule `CLAUDE.md` backs with this hook, from this round's own root cause (a construct the lexer does not model). Verified in bash on `main`: `echo "$(git commit -m x)"`, ``echo `git commit -m x` ``, `out="$(git push origin main 2>&1)"` and `diff <(git commit -m x) /dev/null` all run git and are all allowed — by the guard on `origin/main` too, so not introduced here. Section 1 never decided it; the build pinned `echo "$(git commit -m x)"` as allowed (test_guard_git.py, "recorded miss"), which should have been a halt. Also inconsistent with Halt 1: the same substitution inside an unquoted heredoc body is refused.

What is already on the branch that this round must not break: every acceptance criterion
A1–A6 of round 1 (step 6 re-checks them as a regression pass), the 409 guard tests, and in
particular the `_body_substitutions` extraction this round is expected to reuse. Round 1's
recommendation R2 (reserved words before `git`) is the next round after this one and is not
in this round's scope.

---

## 1. Concept

### Defect

| Field | Value |
|---|---|
| Observed | Bash runs a git command that sits in a command substitution inside a word, but `guard_git.violation` allows it on `main` — on the guard at `origin/main` and as round 1 left it. Separately (folded in at the user's choice), after a separator that does not guarantee success the guard forgets a switch **to** `main`, so a commit that lands on `main` is allowed from a feature branch. |
| Expected | `CLAUDE.md` and the module docstring: the guard refuses a commit or push that would land on `main`, "including inside a compound command". |
| Reproduction | Scratch `r2_repro.py` and `dc_probe.py`; bash with `git` shadowed by an echo function. Allowed on `main` while bash runs git: `echo "$(git commit -m x)"`, `echo "result: $(git commit -m x)"`, `out="$(git push origin main 2>&1)"`, ``echo `git commit -m x` ``, ``x=`git commit -m x` ``, `diff <(git commit -m x) /dev/null`, `tee >(git commit -m x) </dev/null`, `echo "${x:-$(git commit -m x)}"`. Order: from `feat/x`, `git commit -m "$(git checkout -q main)x"` commits to `main` (verified in a throwaway repo) and is allowed in its double-quoted, unquoted and unquoted-heredoc-body forms. Untrusted switch: from `feat/x`, `git checkout main; git commit -m x`, `git checkout main\ngit commit -m x`, `git switch main \|\| true; git push`, `(git checkout main) && git commit -m x`, `x=$(git checkout main) && git commit -m x` are allowed. Already refused (unquoted `$( )` only by accident of `(` being a separator): `echo $(git commit -m x)`, `` `git commit -m x` `` at command position. |
| Root cause | (1) `.claude/hooks/guard_git.py:722-747` (`$(`, backtick) and `:794-803` (`(` after `<`/`>`): `_prepare` recognises where a command substitution opens and pushes a `cmd`/`bt` frame but copies its text through unchanged, so `shlex` keeps `"…$(…)…"` and backticks inside one word and `<(` arrives as one token `_is_separator` rejects; the inner command never becomes a segment, and `violation` (:982) judges only command-name positions. Round 1's heredoc extraction (:786-793) appends body substitutions *after* the opener line, though bash runs them first. (2) `violation` :1021-1022: on any separator but `&&`, `effective = branch` falls back to the starting branch, which is only safe when the starting branch is `main`. |
| Introduced by | (1) Double-quoted substitution unjudged since the `shlex` rebuild `009f6e3` (2026-09-21); backtick handling (`5b01090`, 2026-09-21) covers only the command-name token; round 1 pinned `echo "$(git commit -m x)"` as an allowed "known miss" (`tests/test_guard_git.py:1620-1627`). (2) The distrust rule, also from the 2026-09-21 rebuild. |
| Class | `$( )` inside double quotes, in any position (`${…}`, `$[ ]`, here-strings `<<<"$(…)"`, `[[ ]]`/`[ ]`/`test`, array/`declare`/`export`/`local` assignments, `case`/`for` words, redirection targets, `printf -v`); backticks anywhere but command position (arguments, assignments, inside `${ }`, here-strings, redirections); process substitution `<( )`/`>( )`; nested mixes; substitutions with their own separators, wrappers and subshells; a branch switch inside a substitution, which runs before the enclosing command; bash 5.3 funsub `${ cmd; }`/`${\| cmd; }` (unverified — bash 5.2 here rejects it); an untrusted switch to `main` (or to a target only the shell can resolve) after `;`, newline, `\|\|`, `\|`, `&` or a subshell. Same shape elsewhere: PowerShell's `"$( … )"` subexpression. |
| Blast radius | `violation` is called only from `guard_git.main()`. Tests that move: `tests/test_guard_git.py:1620-1627` (pins the miss as allowed) and round 1's `test_segments_puts_a_body_substitution_on_its_own_line_after_the_command` (pins the after-order). Decided here: both are rewritten to the new behaviour. The module docstring's "known misses" sentence and `STRUCTURE.md`'s guard section change with it. Nothing depends on the bug. |
| Scope | `the class` — the user's decision, including the order fix to round 1's heredoc extraction; the funsub syntax plays safe (the user's choice); and the untrusted-switch-to-`main` defect folded into this round at the user's choice, although it is a different cause. |

Critique — the `diagnosis-critic`'s findings (verdict: cause confirmed, class incomplete) and what was done with each:

1. A substitution runs before the command around it, so a branch switch inside one decides where the enclosing commit lands; round 1's heredoc extraction has the order wrong too — applied: in the class, A5, and the round 1 order test moves.
2. Many more positions within the class, so extracted text must go through the full segment rules (separators, `&&` trust, wrappers, subshells, recursion) — applied: A2–A4.
3. bash 5.3 funsub `${ cmd; }` is a separate, unverified miss — applied as a scope decision: play safe (A7).
4. An untrusted switch to `main` falls back to the starting branch — confirmed in this session; a different cause, folded into this round at the user's choice (A6).

### What this is

Wherever bash runs a command inside a word — `$( … )` inside double quotes, backticks in any
position, `<( … )` and `>( … )` — the guard pulls that command out and judges it as a command
of its own, with every rule a plain command gets, and as running *before* the command that
contains it, on the branch in effect for that command. A branch switch inside a substitution
therefore counts for the enclosing command, and round 1's unquoted-heredoc extraction takes the
same order. Second, when the guard cannot be sure an earlier branch switch took effect, it no
longer assumes the starting branch: a commit or push is refused when `main` is **any** branch
it could land on. bash 5.3's `${ cmd; }` joins the unmodelled syntax that plays safe on `main`.

### Why it is worth building

See the Defect block.

### Inputs and outputs

Unchanged: `violation(command, branch)` returns a refusal reason or `""`; `segments(command)`
returns the invocations or `None`. Which commands land in which outcome changes, and
`segments` gains the extracted commands as invocations of their own.

### How it connects to the rest of the repo

Changes `.claude/hooks/guard_git.py` (the `_prepare` pass, `segments`, `violation`, and
`UNMODELLED_OPENERS` for funsub), `tests/test_guard_git.py`, the module docstring and
`STRUCTURE.md`'s guard section. Builds on round 1's `_body_substitutions` extraction. No other
hook parses shell text.

### Explicitly out of scope

- A git command inside a program's string argument — `bash -c "…"`, `sh -c`, `eval`, aliases
  and functions. A different cause.
- Wrappers not in `WRAPPERS` (`xargs`, `timeout`, `nice`, `command`, `exec`).
- Shell reserved words before `git` (`if git commit …`, `do git push …`, `! git commit`) —
  round 1's recommendation R2, the next round.
- Subcommands spelled with hex escapes or split quotes (`git co""mmit`).
- Running bash 5.3 to verify funsub: it plays safe instead.

### Acceptance criteria

All judged with `main` checked out unless stated; "a branch" is `feat/x`.

| # | The finished feature... |
|---|---|
| A1 | Refuses `echo "$(git commit -m x)"` on `main`, which today it allows. |
| A2 | Judges `$( )` inside double quotes in every position: `out="$(git push origin main 2>&1)"` is refused on `main` and from a branch; `echo "${x:-$(git commit -m x)}"`, `[[ -n "$(git commit -m x)" ]]`, `declare x="$(git commit -m x)"`, `cat <<<"$(git commit -m x)"`, `echo > "$(git commit -m x)"`, `echo $(echo "$(git commit -m x)")`, `echo "$(cd /tmp; git commit -m x)"`, `echo "$(sudo git commit -m x)"` and `echo "$( (git commit -m x) )"` are refused on `main`. |
| A3 | Judges backticks in every position: ``echo `git commit -m x` ``, ``x=`git commit -m x` ``, ``echo ${x:-`git commit -m x`}`` and ``echo 2>`git commit -m x` `` are refused on `main`; ``echo `git push origin main` `` is refused from a branch. |
| A4 | Judges process substitution: `diff <(git commit -m x) /dev/null` and `tee >(git commit -m x) </dev/null` are refused on `main`; `diff <(git push origin main) f` is refused from a branch. |
| A5 | Judges a substitution as running before its enclosing command: `git commit -m "$(git checkout -q main)x"`, `git commit -m $(git checkout -q main)x` and `git commit -F - <<EOF\n$(git checkout -q main)\nEOF` are refused from a branch; a `&&` switch before the enclosing command carries into its substitutions, so `git checkout -b feat/y && out="$(git commit -m y)"` is allowed on `main`. |
| A6 | Refuses a commit or push when `main` is any branch it could land on: from a branch, `git checkout main; git commit -m x`, `git checkout main\ngit commit -m x`, `git switch main \|\| true; git push`, `(git checkout main) && git commit -m x` and `x=$(git checkout main) && git commit -m x` are refused; `git checkout feat/y; git commit -m x` is allowed from a branch; `git checkout -b feat/x; git commit -m x` is still refused on `main`. |
| A7 | Plays safe on bash 5.3 funsub: `echo ${ git commit -m x; }` and `echo ${\| git commit -m x; }` are refused on `main` with the unmodelled-syntax reason, allowed from a branch, and allowed on `main` when they name neither commit nor push. |
| A8 | Leaves harmless substitutions alone: `echo "$(git status)"`, `v="$(git rev-parse HEAD)"`, ``echo `date` `` and `echo "$(git log -1 --format=%s)" \| grep commit` are allowed on `main`; the pipeline's `git commit -m "$(cat <<'EOF' … EOF\n)"` is refused on `main` and allowed on a branch. |
| A9 | Changes nothing else: round 1's A1–A6 still hold; every existing test passes, except four round 1 tests that pin the old behaviour, which are rewritten to the new one — `test_violation_does_not_look_inside_quotes_within_a_body_substitution` (pins the miss), and `test_segments_puts_a_body_substitution_on_its_own_line_after_the_command`, `test_segments_orders_dollar_paren_and_backtick_substitutions_as_written` and `test_segments_unescapes_a_nested_backtick_pair_for_the_inner_command` (pin where an extracted command sits in `segments`' output) *(widened from two named tests at step 2, pending the user's acceptance of the plan)*; and a differential against the guard as round 1 left it (commit `f8775d0`) over every command the existing suite passes to the guard plus generated variations agrees, except where the input contains a command substitution, a funsub opener or an untrusted switch to `main` or an unresolvable target — and there the new decision matches bash with `git` shadowed, or is the play-safe refusal on `main`. |

### Open questions

None.

---

## 2. Plan

### Approach

**Chosen — extract every substitution in `_prepare`, in execution order, and track a set of
possible branches in `violation`.** Round 1 already extracts the `$( )` and backtick
substitutions of an unquoted heredoc body and runs each through `_prepare` recursively. This
round does the same for every command substitution `_prepare` meets in ordinary text: `$( )`
quoted or unquoted, backticks in any position, and `<( )`/`>( )`. Each substitution's text
is removed from the word it sat in. Its prepared commands are inserted **before** the simple
command that contains it, wrapped in two private sentinel characters: `_OPEN` (`\x1d`) and
`_CLOSE` (`\x1e`). Both are added to `PUNCTUATION_CHARS` and `SEPARATOR_CHARS`. `segments()`
turns the sentinels into a nesting `depth` on each `Segment`:
- the first command of a group keeps the enclosing command's own separator, so `&&` trust
  passes into it;
- the enclosing command, which follows the group, gets the new separator `SUBSTITUTED`.
- Round 1's heredoc-body extraction moves to the same insertion point.

`violation()` replaces its single `effective` branch with two sets:
- `ok`: the branches possible if every command in the current `&&` chain succeeded;
- `any`: every branch possible at this point.

A segment joined by `&&` runs in `ok`; any other separator runs in `any`. A switch to `T`
sets `ok = {T}` and adds `T` to `any`. A substitution group runs in its enclosing command's
context. The enclosing command then runs in that context widened by every switch target
inside the group. A commit is refused when `main` is in the context, and a push when it
targets `main` from any branch in it. This removes both causes in the Root cause row:
- substitution text is no longer passed through unseen;
- the fallback after an untrusted separator is "every branch it could be", not "the branch
  it started on".

**Rejected:**
- **A nested parse tree from `segments`** (lists of lists). The cleanest model of the shell,
  but it breaks the public return type and every caller and test of `segments`.
- **Searching every token for a git command.** Refuses `echo git commit`, the failure the
  module treats as worse.
- **Appending extracted commands after the enclosing command,** as round 1 did. That is
  simpler, but it gets A5 wrong: a switch inside a substitution would be judged after the
  commit it precedes.
- **Inserting extracted commands as plain newline-separated lines.** The enclosing command
  would lose its `&&` trust, so `git checkout -b x && git commit -m "$(date)"` would be
  refused on `main`. That is a regression in the pipeline's own commit form, an A8 failure.

### Modules

| Path | New or changed | Purpose |
|---|---|---|
| `.claude/hooks/guard_git.py` | changed | `_prepare` extracts and inserts substitution groups (and moves round 1's body substitutions to the same point); funsub openers join `UNMODELLED_OPENERS`; sentinels join `PUNCTUATION_CHARS`/`SEPARATOR_CHARS`; `Segment` gains `depth`; `segments()` reads the sentinels; `violation()` tracks `ok`/`any` and the group stack; docstrings |
| `tests/test_guard_git.py` | changed | New tests for A1–A8; the four round 1 tests named in A9 rewritten; nothing else touched |
| `STRUCTURE.md` | changed | Guard section: substitutions extracted in execution order, the set-of-branches rule, `Segment.depth`, `SUBSTITUTED`, the new funsub openers; test entry |

### Public API

| Signature | Module | Purpose | Covers |
|---|---|---|---|
| `Segment` — frozen dataclass `tokens: tuple[str, ...]`, `separator: str`, `depth: int = 0` | `guard_git.py` | `depth` is the number of command substitutions the invocation sits inside; a substitution's invocations come immediately before the invocation that contains it. Existing two-argument construction still compares equal at depth 0. | A2–A5 |
| `SUBSTITUTED: str = "$("` | `guard_git.py` | The separator of an invocation whose substitutions ran immediately before it. | A5 |
| `segments(command: str) -> list[Segment] \| None` | `guard_git.py` | Unchanged signature. Substitutions anywhere become invocations of their own, before the invocation that contains them, at one depth more. | A1–A5, A8 |
| `violation(command: str, branch: str) -> str` | `guard_git.py` | Unchanged signature. Judges every invocation, substitutions included, against every branch it could run on. | A1–A9 |
| `UNMODELLED_OPENERS: tuple[str, ...] = ("$'", "@'", '@"', "<#", "`'", '`"', "${ ", "${\t", "${\n", "${\|")` | `guard_git.py` | Gains bash 5.3's funsub openers; matched as prefixes at the scan position rather than as two-character pairs. | A7 |

`PUNCTUATION_CHARS` and `SEPARATOR_CHARS` keep their names and gain `\x1d` and `\x1e`.
Private and not listed: `_OPEN`, `_CLOSE`, and whatever helpers `_prepare` needs.

### Implementation guide

1. **Reproduction first (fix round).** Add
   `test_violation_refuses_a_commit_in_a_double_quoted_substitution_on_main`, asserting that
   `echo "$(git commit -m x)"` is refused on `main` with the commit reason. Run it red and
   paste the run into section 3, then commit before any production change. If it is already
   green, halt.
2. **Sentinels.**
   - Add `_OPEN = "\x1d"` and `_CLOSE = "\x1e"` to `PUNCTUATION_CHARS` and `SEPARATOR_CHARS`.
   - At the top of `_prepare`, replace any `\x1d`/`\x1e` already in the command with a space,
     so input can never forge a group.
   - Add `depth: int = 0` to `Segment` and `SUBSTITUTED = "$("`.
   - In `segments()`, a separator token may now carry sentinels:
     - strip them before `_governs`;
     - each `_OPEN` raises the depth for the next invocation;
     - each `_CLOSE` lowers it;
     - if the token after a `_CLOSE` carries no other separator character, the next
       invocation's separator is `SUBSTITUTED`.

   The existing suite must stay green at this point, which proves the change is an identity
   for commands without substitutions.
3. **Insertion point.** In `_prepare`, keep the index in `out` where the current simple
   command starts:
   - per grouping level (`(`/`{` frames push one, their closers pop it);
   - reset after every unquoted separator character (`;&|` and newline) at that level.
4. **Extract substitutions.** When `_prepare` meets a substitution (unquoted or inside double
   quotes, never inside single quotes or `$'…'`):
   - `$(` that is not arithmetic, read with `_close_paren`;
   - a backtick, read with `_quoted_end`, unescaping `` \` ``, `\$` and `\\` as round 1 does;
   - `<(`/`>(` after a blank or at word start.

   For each one:
   - **Text.** Take its inner text and run it through `_prepare` recursively, keeping the
     unmodelled flag.
   - **Unreadable.** If `_lex` cannot read the result, drop it. That is round 1's rule, and
     bash cannot run it either.
   - **Insert.** Otherwise insert `_OPEN + inner + _CLOSE` at the insertion point.
   - **Remove.** Delete the substitution from `out`. A `$( )`/backtick leaves nothing in the
     word. A `<( )`/`>( )` leaves the placeholder word `_` so the enclosing command keeps its
     shape.

   Several substitutions in one command are inserted in the order they appear, each group
   before the enclosing command. Nested substitutions come out nested through the recursion.
5. **Round 1's heredoc bodies.**
   - When `<<` queues a heredoc, record the insertion point of the command that opened it.
   - At the body, insert each extracted substitution group there, not after the opener line.
   - Keep `_body_substitutions` as it is.
6. **Funsub.**
   - Add `"${ "`, `"${\t"`, `"${\n"` and `"${|"` to `UNMODELLED_OPENERS`.
   - Change the opener check to test each opener as a prefix at the scan position.
   - Outside double quotes, a `${` followed by a blank or `|` is an opener. Do not push the
     `brace` frame for it; leave the text as it is.
7. **Sets in `violation()`.**
   - Replace `effective` with `ok = {branch}`, `any_ = {branch}` and a stack of
     `(context, targets)` frames.
   - **Per segment.**
     - Compute `context` as `ok` for `&&` and `any_` otherwise.
     - While `seg.depth` exceeds the stack height, push `(context, set())`.
     - While it is below, pop. If the segment's separator is `SUBSTITUTED`, its context is
       the popped context together with the popped targets. Popped targets also go into the
       next frame out.
   - **Refusal order.**
     - `main` in the context and a `commit`: refuse with the commit reason.
     - A `push` for which `push_targets_main(args, b)` holds for some named `b` in the
       context: refuse with the push reason.
     - `UNRESOLVED` in the context and a risky subcommand: refuse with the unresolved reason.
   - **Switch.** A switch to `T` that is not redirected sets `ok = {T}`, adds `T` to `any_`
     and to every open frame's targets. Otherwise `ok = context`.
8. **Docs.**
   - Module docstring:
     - remove the substitution "known miss";
     - describe extraction in execution order and the set rule;
     - update the subshell sentence: a switch inside a subshell still counts as possibly
       having happened.
   - `STRUCTURE.md`: the guard section and its table (`Segment.depth`, `SUBSTITUTED`,
     `UNMODELLED_OPENERS`), and the test entry.

### Test intents

| # | Must prove | Covers |
|---|---|---|
| T1 | `echo "$(git commit -m x)"` is refused on `main`: red before the fix, green after | A1 |
| T2 | Every double-quoted `$( )` form in A2 is refused on `main`, and the push form from a branch too; `segments` puts each extracted command before its enclosing command, at depth 1, with `SUBSTITUTED` on the enclosing one | A2 |
| T3 | Every backtick form in A3 is refused on `main`, and the push form from a branch; a backtick at command position still is | A3 |
| T4 | Both process-substitution forms are refused on `main`, and the push form from a branch; the enclosing command still reads with `_` in place | A4 |
| T5 | The three forms of `git commit -m "$(git checkout -q main)x"` are refused from a branch; `git checkout -b feat/y && out="$(git commit -m y)"` and `git checkout -b feat/y && git commit -m "$(date)"` are allowed on `main`; nested and multiple substitutions keep execution order | A5 |
| T6 | Every untrusted switch to `main` in A6 is refused from a branch; a switch to another branch after `;` is allowed; `git checkout -b feat/x; git commit` is still refused on `main` with the commit reason; an unresolvable switch after `;` refuses on a branch | A6 |
| T7 | Both funsub forms are refused on `main` with the unmodelled reason, allowed from a branch, and allowed on `main` without commit or push; `UNMODELLED_OPENERS` is pinned to its new value | A7 |
| T8 | Every harmless form in A8 is allowed on `main`; the pipeline's commit form is refused on `main` and allowed on a branch, alone and after `git checkout -b x &&` | A8 |
| T9 | Every existing test passes except the four named in A9, which are rewritten to the new order. Round 1's A1–A6 are re-checked. The differential against the guard at `f8775d0` is run in step 6 as section 1 specifies: corpus recorded from the suite, plus variants with the command wrapped in `"$( )"`, in backticks and in `<( )`, and prefixed by `git checkout main;` and `git checkout -;`; branches `main` and `feat/x`. Every difference must sit in A9's exception set and match bash with `git` shadowed, or be the play-safe refusal | A9 |

### Risks

- **The insertion point lands in the wrong place.** Plain commands would then lex
  differently. Guide step 2 proves identity for commands without substitutions, and step 3
  is the first place it can break. The build fixes this without asking.
- **An existing test outside the four named in A9 fails** because of the set rule or the
  extraction. Halt: A9 says it must not.
- **Messages.** The refusal order (`main` first, then unresolved) keeps every message the old
  guard gave where it refused. A changed message on a refusal that already existed is a bug
  the build fixes, not a halt.
- **Dropping an unreadable substitution** mirrors round 1. Bash cannot run a substitution it
  cannot parse either, so this is not a new miss.
- **funsub cannot be run here.** Evidence is `violation()` only. Not a halt.
- **PowerShell's `"$( … )"` subexpression** is extracted the same way. It runs in PowerShell
  too, so a refusal there is correct. Not a halt.
- **The cause is elsewhere.** If the build finds a bypass in A1–A6 that extraction and the
  set rule cannot close because its cause is not in what `_prepare` passes to `shlex` or in
  the fallback at `violation` :1021-1022, it halts.

### Coverage

- Every criterion has a Public API entry. A1–A5 and A8 go through
  `segments`/`violation`/`Segment.depth`/`SUBSTITUTED`. A6 and A9 go through `violation`.
  A7 goes through `UNMODELLED_OPENERS`.
- Every criterion has a test intent: A1→T1 … A9→T9.
- Nothing in the Public API lacks a criterion. `depth` and `SUBSTITUTED` exist for A2–A5,
  and the new `UNMODELLED_OPENERS` value exists for A7.

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
