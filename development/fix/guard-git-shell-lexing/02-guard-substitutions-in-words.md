# The git guard judges command substitutions inside a word

<!-- claude-plan step=6 status=active -->

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
| 2 | Plan | `/plan` | with the user | done |
| 3 | Implement | `/implement` | in `/build` | done |
| 4 | Verify | `/verify` | in `/build` | done |
| 5 | Test | `/test` | in `/build` | done |
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
| A7 | Plays safe on bash 5.3 funsub: `echo ${ git commit -m x; }`, `echo ${\| git commit -m x; }` and `echo "${ git commit -m x; }"` *(added at step 2)* are refused on `main` with the unmodelled-syntax reason, allowed from a branch, and allowed on `main` when they name neither commit nor push. |
| A8 | Leaves harmless substitutions alone: `echo "$(git status)"`, `v="$(git rev-parse HEAD)"`, ``echo `date` `` and `echo "$(git log -1 --format=%s)" \| grep commit` are allowed on `main`; the pipeline's `git commit -m "$(cat <<'EOF' … EOF\n)"` is refused on `main` and allowed on a branch. |
| A9 | Changes nothing else: round 1's A1–A6 still hold; every existing test passes, except five round 1 tests that pin the old behaviour, which are rewritten to the new one — `test_violation_does_not_look_inside_quotes_within_a_body_substitution` (pins the miss), and `test_segments_puts_a_body_substitution_on_its_own_line_after_the_command`, `test_segments_orders_dollar_paren_and_backtick_substitutions_as_written` and `test_segments_unescapes_a_nested_backtick_pair_for_the_inner_command` (pin where an extracted command sits in `segments`' output), and `test_violation_does_not_carry_an_unresolvable_switch_across_a_weak_join` (pins `git checkout - ; git commit` as allowed from a branch, which A6's rule now refuses) *(widened from two named tests at step 2; accepted with the plan)*; and a differential against the guard as round 1 left it (commit `f8775d0`) over every command the existing suite passes to the guard plus generated variations agrees, except where the input contains a command substitution, a funsub opener or an untrusted switch to `main` or an unresolvable target — and there the new decision matches bash with `git` shadowed, or is the play-safe refusal on `main`. |

### Open questions

None.

---

## 2. Plan

### Approach

**Chosen: extract every substitution in `_prepare`, in execution order, and track the set of
possible branches in `violation`.**

Round 1 already pulls the `$( )` and backtick substitutions out of an unquoted heredoc body
and runs each through `_prepare` again. This round does the same for every command
substitution `_prepare` meets in ordinary text:
- `$( )`, quoted or unquoted;
- backticks;
- `<( )` and `>( )`.

Each substitution's prepared commands are placed **before** the simple command that contains
it. They go into a slot reserved at that command's start and are wrapped in two private
sentinel characters, `_OPEN` (`\x1d`) and `_CLOSE` (`\x1e`). Both characters are added to
`PUNCTUATION_CHARS` and `SEPARATOR_CHARS`. `segments()` reads the sentinels as a nesting
`depth` on each `Segment`:
- the first command in a group inherits the separator of the command that contains it, so
  `&&` trust passes into it;
- the containing command, which comes after the group, gets the new separator `SUBSTITUTED`.

Round 1's heredoc-body extraction uses the same slot.

`violation()` replaces its single `effective` branch with two sets:
- `ok`: the branches possible if every command in the current `&&` chain succeeded;
- `any`: every branch possible at this point.

A segment joined by `&&` runs in `ok`; any other separator runs in `any`. A switch to `T`
sets `ok = {T}` and adds `T` to `any`. A substitution group runs in the context of the command
that contains it. That command then runs in the same context, widened by every switch target
inside the group. A commit is refused when `main` is in the context. A push is refused when it
targets `main` from any branch in the context.

This removes both causes in the Root cause row:
- substitution text is no longer passed through unseen;
- after a separator that guarantees nothing, the guard assumes "every branch it could be",
  not "the branch it started on".

**Rejected:**
- **A nested parse tree from `segments`.** It would model the shell most cleanly, but it
  changes the public return type and breaks every caller and test.
- **Searching every token for a git command.** It refuses `echo git commit`, which the module
  treats as the worse failure.
- **Appending extracted commands after their command,** as round 1 does. A switch inside a
  substitution would then be judged after the commit it precedes (A5).
- **Inserting extracted commands as plain newline-separated lines.** The containing command
  would lose its `&&` trust. `git checkout -b x && git commit -m "$(date)"` would then be
  refused on `main`, the A8 regression.

### Modules

| Path | New or changed | Purpose |
|---|---|---|
| `.claude/hooks/guard_git.py` | changed | `_prepare` reads substitutions with its own walk, extracts them into the command's slot and keeps PowerShell-safe text where a backtick sits in double quotes. Funsub openers (also inside double quotes) join `UNMODELLED_OPENERS`. Sentinels join `PUNCTUATION_CHARS` and `SEPARATOR_CHARS`. `Segment` gains `depth`. `segments()` reads the sentinels piece by piece. `violation()` tracks `ok`/`any` and a frame stack. The unmodelled reason names funsub. Docstrings updated. |
| `tests/test_guard_git.py` | changed | New tests for A1–A8. The five round-1 tests named in A9 are rewritten; nothing else is touched. |
| `STRUCTURE.md` | changed | Guard section: substitutions extracted in execution order, the set-of-branches rule, `Segment.depth`, `SUBSTITUTED`, the funsub openers. Test entry updated. |

### Public API

| Signature | Module | Purpose | Covers |
|---|---|---|---|
| `Segment`: frozen dataclass with `tokens: tuple[str, ...]`, `separator: str`, `depth: int = 0` | `guard_git.py` | `depth` counts the command substitutions the invocation sits inside. A substitution's invocations come immediately before the invocation that contains it. Construction with two arguments still compares equal at depth 0. | A2–A5 |
| `SUBSTITUTED: str = "$("` | `guard_git.py` | The separator of an invocation whose substitutions ran immediately before it. | A5 |
| `segments(command: str) -> list[Segment] \| None` | `guard_git.py` | Signature unchanged. Every substitution becomes invocations of its own, placed before the invocation that contains it, one depth deeper. | A1–A5, A8 |
| `violation(command: str, branch: str) -> str` | `guard_git.py` | Signature unchanged. Judges every invocation, substitutions included, against every branch it could run on. | A1–A9 |
| `UNMODELLED_OPENERS: tuple[str, ...] = ("$'", "@'", '@"', "<#", "`'", '`"', "${ ", "${\t", "${\n", "${\|")` | `guard_git.py` | Adds bash 5.3's funsub openers. Each opener is now matched as a prefix at the scan position. | A7 |

`PUNCTUATION_CHARS` and `SEPARATOR_CHARS` keep their names and gain `\x1d` and `\x1e`.
Private, so not listed: `_OPEN`, `_CLOSE`, and any helpers `_prepare` needs.

### Implementation guide

1. **Reproduction first (fix round).**
   - Add `test_violation_refuses_a_commit_in_a_double_quoted_substitution_on_main`. It
     asserts that `echo "$(git commit -m x)"` is refused on `main` with the commit reason.
   - Run it red and paste the run into section 3.
   - Commit before changing any production code.
   - If it is already green, halt.

2. **Sentinels.**
   - Add `_OPEN = "\x1d"` and `_CLOSE = "\x1e"` to `PUNCTUATION_CHARS` and `SEPARATOR_CHARS`.
   - At the top of `_prepare`, replace any `\x1d` or `\x1e` already in the command with a
     space, so input can never forge a group.
   - Add `depth: int = 0` to `Segment`, and add `SUBSTITUTED = "$("`.
   - In `segments()`, a separator token may carry sentinels glued to other punctuation
     (`&&\x1d`, `)\x1e`, `\x1e;`, `\x1e\x1d`). Split it at the sentinels and handle the
     pieces left to right:
     - **A piece of separator characters** goes into `pending` through `_governs`, as today.
       A piece that is empty, or made only of sentinels, adds nothing.
     - **`_OPEN`** adds one to depth and keeps `pending`, so the group's first invocation
       inherits the containing command's separator.
     - **`_CLOSE`** ends the current invocation, subtracts one from depth and clears
       `pending`.
     - **The next invocation's separator** is `SUBSTITUTED` if no separator piece follows the
       last `_CLOSE`. Otherwise it is `_join` of the pieces that do.
     - **A first invocation** that starts with `_OPEN` keeps separator `""`.
   - The existing suite must still be green after this step. That proves the change makes no
     difference to commands without substitutions.

3. **The slot.**
   - **What it is.** At the start of each simple command, `_prepare` appends an empty slot
     to `out` and keeps a reference to it. The slot is a mutable chunk, such as a one-item
     list joined at the end.
   - **When a new command starts.** After any unquoted `;`, `&`, `|`, newline, `(` or `)`
     that is not inside a `brace` frame or a quote. Also after a `{` or `}` that stands as a
     word of its own. Never inside `${ }`.
   - **Unmatched `)`.** A `)` with nothing open, such as a `case` pattern, must not pop an
     empty frame stack. Keep the existing guard at :805.
   - **Why a slot.** Groups are filled into the slot, so nothing in `out` shifts. A heredoc
     records its opener command's slot.

4. **Extract substitutions.** This applies when `_prepare` meets a substitution unquoted or
   inside double quotes, never inside single quotes or `$'…'`. The kinds are:
   - `$(` that is not arithmetic;
   - a backtick;
   - `<(` or `>(` where the `<` or `>` starts a word.

   - **Finding the end.** Use `_prepare`'s own walk, not `_close_paren`. For example, a
     recursive `_prepare` call returns the index of the `)` or backtick that closes its
     frame. That way heredocs, comments, quotes and arithmetic inside the substitution are
     read as round 1 reads them. The pipeline's form `"$(cat <<'EOF'\nit's 1) done\nEOF\n)"`
     must close at the right `)`.
   - **If it never closes.** Leave the text in place and keep walking it, as round 1 does
     for ordinary text. Do not drop it. The "never closes, so nothing runs" rule stays only
     inside heredoc bodies.
   - **If it closes.**
     - Prepare its inner text recursively, carrying the unmodelled flag. For backticks,
       first unescape `` \` ``, `\$` and `\\`, as round 1 does.
     - If `_lex` cannot read the result, drop the group. That is round 1's rule, and bash
       cannot run such a substitution either.
     - Otherwise add `_OPEN + inner + _CLOSE` to the command's slot. Groups go in the order
       their substitutions appear, each after the one before.
   - **What stays in the word.** The substitution is replaced by the placeholder word `_`.
     - For `<( )` and `>( )`, the whole construct is replaced, the `<` or `>` included, so
       `cat <(x)` becomes `cat _`.
     - A word made only of a substitution keeps its shape: `-b "$(echo y)"` becomes `-b _`,
       which is still a switch away from `main`.
     - `boundary` stays `False` after the placeholder, so the `#` in `$(true)#` remains part
       of the word.
   - **Backtick inside double quotes.** PowerShell uses the backtick as its escape
     character. So add the group to the slot, but **leave the original text in place**
     rather than replacing it with `_`. The guard then refuses if either reading refuses.
     This applies only to backticks inside double quotes. Everywhere else the substitution
     is replaced.

5. **Round 1's heredoc bodies.** Each extracted body substitution goes into the slot of the
   command that opened the heredoc, not after the opener line. `_body_substitutions` stays
   as it is.

6. **Funsub.**
   - Add `"${ "`, `"${\t"`, `"${\n"` and `"${|"` to `UNMODELLED_OPENERS`.
   - Change the opener check to match each opener as a prefix at the scan position.
   - A `${` followed by a blank or `|` is a funsub opener **both outside and inside double
     quotes**. Flag it and do not push the `brace` frame for it.
   - Add "a bash 5.3 `${ cmd; }`" to the unmodelled reason after `$'...'`. The reason's
     opening words stay the same.

7. **Sets in `violation()`.**
   - Replace `effective` with `ok = {branch}`, `any_ = {branch}` and a stack of
     `(context, targets)` frames.
   - **Context for each segment.**
     - Start from `ok` if the separator is `&&` and `any_` otherwise.
     - While `seg.depth` is above the stack height, push `(context, set())`.
     - While it is below, pop. With several levels popped at once, the context is the
       outermost popped frame's context together with every popped frame's targets. Popped
       targets also flow into the next frame out.
     - A `SUBSTITUTED` segment that popped takes that context.
     - A `SUBSTITUTED` segment with nothing to pop, because the next group follows at the
       same depth, runs in the top frame's context together with that frame's targets.
   - **Refusal order.**
     - `main` in the context and a `commit`: refuse with the commit reason.
     - A `push` for which `push_targets_main(args, b)` holds for any named `b` in the
       context: refuse with the push reason.
     - `UNRESOLVED` in the context and a risky subcommand: refuse with the unresolved reason.
   - **After a switch.** A switch to `T` that is not redirected sets `ok = {T}`, and adds
     `T` to `any_` and to every open frame's targets. Otherwise set `ok` to the context.

8. **Docs.**
   - **Module docstring.** Remove the substitution "known miss". Describe extraction in
     execution order and the set rule. Change the subshell sentence: a switch inside a
     subshell now counts as possibly having happened.
   - **Recorded misses.** Record `"${x:-'$(cmd)'}"`: inside double quotes the single quotes
     are literal, and the `brace` frame reads them as quoting.
   - **`STRUCTURE.md`.** Update the guard section and its table (`Segment.depth`,
     `SUBSTITUTED`, `UNMODELLED_OPENERS`) and the test entry.

### Test intents

| # | Must prove | Covers |
|---|---|---|
| T1 | `echo "$(git commit -m x)"` is refused on `main`. Red before the fix, green after. | A1 |
| T2 | Every double-quoted `$( )` form in A2 is refused on `main`, and the push form from a branch too. Same for `for x in "$(…)"`, `case "$(…)" in`, `a=("$(…)")`, `printf -v v "$(…)"` and `$[ $(…) ]`. `segments` puts each extracted command before the command containing it, at depth 1, with `SUBSTITUTED` on the containing command. A first invocation that opens with a group keeps separator `""`. | A2 |
| T3 | Every backtick form in A3 is refused on `main`, and the push form from a branch. A backtick at command position is still refused. PowerShell escapes are not misread: from a branch, `` git commit -m "a`nb"; git push origin main; git log --format="%h`t%s" `` and `` git commit -m "a`nb"; git push origin main `` are refused with the push reason, and `` git commit -m "Title`n`nBody" `` is allowed. | A3 |
| T4 | `diff <(git commit -m x) /dev/null`, `tee >(git commit -m x) </dev/null` and `cat <(git commit -m x)` are refused on `main`. `diff <(git push origin main) f` and `diff <(a) <(git push origin main)` are refused from a branch. The command containing them reads with `_` in place of the whole construct. | A4 |
| T5 | All three forms of `git commit -m "$(git checkout -q main)x"` are refused from a branch. These are allowed on `main`: `git checkout -b feat/y && out="$(git commit -m y)"`, `git checkout -b feat/y && git commit -m "$(date)"`, `git checkout -b feat/y && echo "$(date)$(git commit -m y)"` (two groups) and `git checkout -b "$(echo feat/y)" && git commit -m x` (placeholder keeps the switch). `echo "$($(git checkout main))" && git commit -m x` (two levels closing) and `if ($?) { git commit -m "$(git checkout main)" }` are refused from a branch. Groups keep execution order. | A5 |
| T6 | Every untrusted switch to `main` in A6 is refused from a branch. A switch to another branch after `;` is allowed. `git checkout -b feat/x; git commit` is still refused on `main` with the commit reason. `git checkout -; git commit` is refused from a branch with the unresolved reason, and on `main` with the commit reason. | A6 |
| T7 | `echo ${ git commit -m x; }`, `echo ${\| git commit -m x; }` and `echo "${ git commit -m x; }"` are refused on `main` with the unmodelled reason, which now names funsub. They are allowed from a branch, and allowed on `main` without commit or push. `UNMODELLED_OPENERS` is pinned to its new value. | A7 |
| T8 | Every harmless form in A8 is allowed on `main`. The pipeline's commit form is refused on `main` and allowed on a branch, both alone and after `git checkout -b x &&`. The same holds with an apostrophe and a `)` in the message: `git commit -m "$(cat <<'EOF'\nit's 1) done\nEOF\n)"`. | A8 |
| T9 | Every existing test passes except the five named in A9, which are rewritten. Round 1's A1–A6 are re-checked. The differential runs in step 6, as follows. | A9 |

The T9 differential:
- **Baseline.** `git show f8775d0:.claude/hooks/guard_git.py`, saved into the scratch
  directory and imported with `.claude/hooks` on `sys.path`, registered in `sys.modules`
  before it runs.
- **Corpus.** Every `(command, branch)` the existing suite passes to `violation`, captured
  in one pytest run by a scratch plugin loaded with `-p`. Add variants that wrap each
  command in `"$( )"`, in backticks and in `<( )`, and variants that prefix it with
  `git checkout main;` and with `git checkout -;`. Run every input on `main` and on `feat/x`.
- **Oracle.** A bash `git()` function that keeps a `HEAD` variable. It handles `checkout` and
  `switch` (including `-b`, `-c`, and `-` through a `PREV` variable) and prints
  `COMMIT@$HEAD` or `PUSH@$HEAD <args>`. The oracle says "refuse" when it prints
  `COMMIT@main`, or a push that `push_targets_main` reads as reaching `main`.
- **Exempt inputs.** PowerShell-only inputs, listed by name.
- **What passes.** Every difference must fall in A9's exception set and agree with the
  oracle, or be the play-safe refusal. The table of differences goes into section 6.

### Risks

- **The slot or the separator rules are wrong.** Commands without substitutions would then
  lex differently. Guide step 2 proves they do not. Steps 3 and 4 are where it can break.
  The build fixes this without asking.
- **An existing test outside the five named in A9 fails.** Halt: A9 says it must not.
- **A refusal message changes.** The refusal order (main first, then unresolved) keeps every
  message the old guard gave where it already refused. A changed message on an existing
  refusal is a bug the build fixes, not a halt.
- **PowerShell backticks.** Keeping the text in place where a backtick sits in double
  quotes means a backtick pair that bash would run *and* PowerShell would read as escapes
  is judged both ways. That direction is safe. Not a halt.
- **Funsub cannot be run here.** The only evidence is `violation()`. Not a halt.
- **`"${x:-'$(cmd)'}"` stays missed.** Recorded in the docstring and section 5, for step 8.
- **The cause is elsewhere.** If the build finds an A1–A6 bypass that extraction and the set
  rule cannot close, because its cause is neither in what `_prepare` hands to `shlex` nor in
  the fallback at `violation` :1021-1022, it halts.

### Coverage

- **Every criterion has a Public API entry.**
  - A1–A5 and A8: `segments`, `violation`, `Segment.depth` and `SUBSTITUTED`.
  - A6 and A9: `violation`.
  - A7: `UNMODELLED_OPENERS` and `violation`.
- **Every criterion has a test intent:** A1→T1 through A9→T9.
- **Nothing in the Public API lacks a criterion.** `depth` and `SUBSTITUTED` serve A2–A5,
  and the new `UNMODELLED_OPENERS` value serves A7.

### Critique

`plan-critic` verdict: accept with changes. Every finding was applied.

1. **`_close_paren` cannot find the end of a `$( )` that contains a heredoc** (the pipeline's
   own commit form with an apostrophe), and an unclosed extraction was left undecided.
   Applied: the end is found with `_prepare`'s own walk, an unclosed substitution in
   ordinary text is left in place, and T8 covers it (guide step 4).
2. **A fifth existing test flips:** `test_violation_does_not_carry_an_unresolvable_switch_across_a_weak_join`.
   Applied: added to A9's rewrite list (section 1, put to the user with the plan), and T6
   pins the new behaviour.
3. **The sentinel-to-depth rule was incomplete,** and two substitutions in one command were
   not handled. Applied: guide step 2 now splits tokens piece by piece, step 7 covers a
   `SUBSTITUTED` segment with nothing to pop and a pop of several levels, groups are
   ordered, and T5 covers both forms.
4. **Extracting backticks inside double quotes breaks PowerShell escapes** and can hide a
   push. Applied: the text is kept in place there, so both readings are judged (guide step
   4, T3).
5. **Removing a substitution so that nothing is left changes a switch target.** Applied:
   the placeholder `_` is used everywhere (guide step 4, T5).
6. **The insertion point relied on frames `_prepare` does not have,** and could go stale.
   Applied: a slot reserved per simple command replaces the stack (guide step 3, T5's
   `if ($?) { }`).
7. **Funsub inside double quotes was missed,** and the reason did not name it. Applied:
   detected inside double quotes too, the reason names it, A7 and T7 extended.
8. **T9 had no oracle that could judge the A5 and A6 differences.** Applied: a bash `git()`
   that tracks `HEAD`, with the procedure spelled out under T9.
9. **(a)** `<( )` replaced whole: applied (T4). **(b)** `"${x:-'$(cmd)'}"`: recorded as a
   known miss, not fixed in this round. **(c)** The extra class inputs: added to T2.
   **(d)** `boundary` stays `False` after a placeholder: stated in guide step 4.

---

## 3. Implementation notes

> Written in step 3. Only deviations from the plan above, each with its reason. "Built as
> planned" is a complete and good entry. On a fix round, also the reproduction test's red
> run, pasted here before the fix was written — step 6 cites it.

**Reproduction, red** (`test_violation_refuses_a_commit_in_a_double_quoted_substitution_on_main`, run before any production change):

```
$ pytest tests/test_guard_git.py -k test_violation_refuses_a_commit_in_a_double_quoted_substitution_on_main
tests/test_guard_git.py::test_violation_refuses_a_commit_in_a_double_quoted_substitution_on_main FAILED
>       assert violation('echo "$(git commit -m x)"', PROTECTED).startswith(COMMIT_REASON)
E       assert False
E        +  where False = <built-in method startswith of str object at 0x...>('Refused: this would commit to `main`')
E        +      where '' = violation('echo "$(git commit -m x)"', 'main')
====================== 1 failed, 409 deselected in 0.21s =======================
```

The command is allowed (empty reason) while bash runs git: the shape the Defect block's Observed row describes.

**Built as planned, with these deviations and additions:**

- **A test outside A9's five went red and was updated:** `test_unmodelled_openers_is_the_documented_set` pins the exact `UNMODELLED_OPENERS` value, which the plan itself changes (Public API table, A7, T7 "pinned to its new value"). It was updated to the new tuple. This is a mechanical consequence of the plan rather than a behaviour change, so it was not treated as the Risks-section halt; step 6 should confirm that reading.
- `test_segments_unescapes_a_nested_backtick_pair_for_the_inner_command` stayed green after the change but was rewritten as A9 lists it, to pin the new position (`git commit` at depth 2 before `echo _` at depth 1). The other four A9 tests (`..._quotes_within_a_body_substitution`, `..._after_the_command`, `..._as_written`, `..._weak_join`) went red and were rewritten to the new behaviour (the first and the weak-join test were renamed to say what they now prove).
- A standalone `}` does not open a new slot (guide step 3 lists it): a command cannot start right after `}` without a `;`, `&`, `|` or newline, which already do. A slot is also not opened after the `&` or `|` of a redirection (`>&`, `<&`, `&>`, `>|`), so a group never lands in the middle of a command.
- `segments()` also splits a token that holds a mark glued to punctuation that is no operator (`>&\x1d`, `<(\x1d`), appending the non-mark pieces to the current invocation. Without it a group after such a punctuation run would stay inside a word and never be judged.
- Guarded against runaway input beyond the plan: substitutions nested deeper than 30 are not followed and set the unmodelled flag; a `failed` set of positions stops a run of unclosed `$(` from being re-walked exponentially (400 unclosed openers: 0.19 s); a heredoc opened inside a substitution whose body follows the closing `)` sets the unmodelled flag.
- The refusal order in `violation` is main/commit, then push, then unresolved (guide step 7). Where both used to apply the old guard gave the unresolved message first; no existing test pins that.
- Oracle note for step 6: a bash `git()` that keeps `HEAD` in a shell variable is wrong across `$( )`/`<( )` subshells, where the change is lost. A file-backed `HEAD` is used instead (`scratchpad/oracle.py`); with it the guard never allowed what bash ran onto `main`, and refused extra only where it plays safe (a `;` after a switch, concurrent `<( )`).

**Bugs the step 5 readers and tests found, fixed in place (all inside section 1: A2, A5, A8, A9).** Each was confirmed in bash with `git` shadowed before the fix, and no public signature changed:

- **A `case` pattern's `)` ended a `$( )` early** (A2, A9; a regression against `f8775d0` for the unquoted form). `_scan` now tracks `case … esac` per frame depth, reading `case` and `esac` only as words at a command position, and a `)` at a open `case`'s own depth closes nothing. The end of a `$( )` inside an unquoted heredoc body is found by the same walk (`_body_substitutions` no longer uses a separate matcher, so `_close_paren` and the double-quote branch of `_quoted_end` are gone, and with them the unbounded recursion).
- **Substitutions inside `$(( ))` and `(( ))` were copied through unread** (A2). They are extracted like those of a heredoc body (`_body_substitutions` now serves both); the arithmetic text is replaced by the placeholder only when something was extracted from it.
- **An unpaired backtick inside double quotes** (PowerShell's escape) pushed a backtick frame, turned the string state off and let a following `#` comment out the rest, losing a later `git push origin main`, or misplaced the slot (A3, A5). It is now a plain character, and a kept-in-place pair that contains an odd number of quotes closes the string. The decision is no worse than `f8775d0` on every input tried and better on four.
- **A hostile or deeply nested command could crash or stall the hook** (A9: the hook exits 1 or times out, and both let the command run). Reading is budgeted (`20 * len + 50000` steps, shared by every walk, charged in `_scan`, `_arith_end` and `_body_substitutions`); past it `_prepare` returns the command unchanged and flagged, so `main` plays safe. `violation` now catches any exception and treats it as unreadable input (refused on `main` when it names `commit` or `push`, allowed elsewhere). Measured: 1500 nested `$(` in a heredoc body went from `RecursionError` to 0.35 s, 6000 unclosed openers 0.35 s.
- **An empty `$( )` or a pair of double backticks lost `&&` trust** (A8, A5). `segments` now leaves the separator exactly as it was when a group ran no invocation.
- **A switch target a substitution made** was read as a branch called `_` (the Class row's "target only the shell can resolve", A6). The placeholder is now `\x1f` inside the module and `segments` shows it as `_`, so `switch_target` can return `UNRESOLVED` for `git checkout "$(echo main)"`, `-B`/`-C` with a substituted name, and a name with a substitution in it; `-b`/`-c` still read as a switch away.
- Docstrings corrected: `_strip_substitution`, `_branch_name`, `Segment.separator`, `segments`, `switch_target`, and the module's "known misses" sentence.

**Send-back from step 6 (A2/A9), fixed.** `echo "$(cat <<EOF > f\n$(git push origin main)\nEOF)"` and its backtick-body twin were allowed from a branch while bash pushes `main`. Cause: the body substitution was extracted correctly, but the heredoc body ran to the end of the input and swallowed the closing `"`, so the prepared text had an unbalanced quote, `_lex` returned None and `violation` treated the command as unreadable (refused only on `main`). The unquoted form has no quote to lose, which is why only the double-quote path missed. Red run before the fix (`test_violation_judges_a_body_substitution_of_an_unclosed_quoted_substitution`, 3 of 4 parametrized cases failed: `violation(..., 'feat/topic') == ''`). Fix in `_scan`'s newline branch: when heredoc bodies reach the end of the input, one closing `"` is appended per open `dq` frame so `shlex` reads what is left; the extracted group was already in the slot. Verified in bash with `git` shadowed that the push runs. Suite: 702 passed (697 plus 4 new cases and 1 new data-form test).

---

## 4. Verification log

> Written in step 4: the static half. Command output, not a summary of it.

| Check | Result |
|---|---|
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `11 files already formatted` |
| `mypy` | `Success: no issues found in 11 source files` |
| `pytest` | `501 passed in 6.26s` |
| Plan completeness | every signature in the Public API table exists as written (table below) |
| `STRUCTURE.md` | in sync after two edits from the `structure-auditor` (private helper name `_prepare` removed from prose in two places); the `UNMODELLED_OPENERS` code comment, which still listed four constructs, now names funsub |
| `python -m <package>.<module>` | not applicable: the hooks are executable scripts (entry point `main()`, no showcase), and `template_repo` is not installed here |

Plan completeness, checked by importing the module and comparing literally:

| Entry | Result |
|---|---|
| `Segment(tokens: tuple[str, ...], separator: str, depth: int = 0)`, frozen | matches; `Segment(("a",), "") == Segment(("a",), "", 0)` |
| `SUBSTITUTED = "$("` | matches |
| `segments(command: str) -> list[Segment] \| None` | matches |
| `violation(command: str, branch: str) -> str` | matches |
| `UNMODELLED_OPENERS` | equals the ten-element tuple of the plan exactly |

Step 3 deviations (section 3), classified:

| Deviation | Class |
|---|---|
| `test_unmodelled_openers_is_the_documented_set` updated to the new tuple | Deviation, recorded; mechanical consequence of the plan's own change, no criterion touched |
| Fifth A9 test rewrites (one stayed green, rewritten to pin the new position) | Deviation, recorded; within A9 |
| Standalone `}` opens no slot; no slot after `&`/`|` of a redirection | Deviation, recorded; refines guide step 3 without changing behaviour a criterion pins |
| `segments()` splits a token with a mark glued to non-operator punctuation | Deviation, recorded; needed so a group is judged |
| Runaway-input guards (depth 30, `failed` set, heredoc-in-substitution flag) | Unplanned but private, justified in section 3 |
| Refusal order main, push, unresolved | Deviation, recorded; as guide step 7 |

None amends section 1.

### Re-verify after send-back (step 6, A2/A9; commit `9a98609`)

The change touched one branch of `_scan` (closing quotes appended when heredoc bodies reach the end of the input) and added tests; no reader report was run.

| Check | Result |
|---|---|
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `11 files already formatted` |
| `mypy` | `Success: no issues found in 11 source files` |
| `pytest` | `702 passed in 12.61s` |
| Public API | re-imported and compared literally: `Segment(tokens: tuple[str, ...], separator: str, depth: int = 0)` frozen, `SUBSTITUTED = "$("`, `segments(command: str) -> list[Segment] \| None`, `violation(command: str, branch: str) -> str`, `UNMODELLED_OPENERS` the ten-element tuple; all unchanged, no mismatch |
| `STRUCTURE.md` | in sync for this change: the diff touched only private `_scan` (not listed) and the `tests/test_guard_git.py` entry, which the commit already extended (unterminated body inside a double-quoted `$( )`); no edit needed |
| Showcase | not applicable (hook scripts) |

No deviation, no halt.

---|---|
| `ruff check .` | |
| `ruff format --check .` | |
| `mypy` | |
| Plan completeness | every signature in the Public API table exists as written |
| `STRUCTURE.md` | in sync |
| `python -m <package>.<module>` | |

---

## 5. Test log

> Written in step 5: the dynamic half.

Round 2 added 196 test cases to `tests/test_guard_git.py` (501 to 697 in the whole suite), beyond the reproduction test step 3 added, which is unchanged. Two readers worked it, `contract` and `input-space`; every "bash does X" claim in their reports was checked by running bash with `git` shadowed by a function that records `HEAD` in a file. PowerShell claims could not be run (`pwsh` is not installed) and rest on `violation()` alone.

| Intent | Test names | Result |
|---|---|---|
| T1 (A1) reproduction, red then green | `test_violation_refuses_a_commit_in_a_double_quoted_substitution_on_main` (step 3, unchanged); `test_violation_allows_a_commit_in_a_substitution_off_main` | pass |
| T2 (A2) every position, push from a branch, `segments` shape | `test_violation_refuses_a_commit_in_every_substitution_position` (22), `test_violation_refuses_a_push_in_a_quoted_assignment_on_main_and_from_a_branch`, `test_violation_refuses_a_push_to_main_inside_a_substitution_from_a_branch` (6), `test_segments_puts_a_quoted_substitution_before_the_command_around_it`, `test_segments_gives_the_first_group_the_separator_of_its_command`, `test_segments_marks_a_second_group_substituted_too`, `test_segments_closes_two_levels_one_after_the_other`, `test_segments_returns_to_an_operator_after_the_command_around_a_group`, `test_segments_keeps_a_newline_inside_a_group_out_of_the_outer_separator`, `test_segments_two_argument_construction_is_depth_zero`, `test_segments_blanks_group_marks_and_the_placeholder_it_was_given`, `test_violation_cannot_be_given_a_forged_group_to_hide_behind`, `test_segments_leaves_an_unclosed_substitution_in_the_text` | pass |
| T3 (A3) backticks, PowerShell escapes | `test_violation_refuses_a_commit_in_a_backtick_in_every_position` (7), `test_violation_refuses_a_push_to_main_in_a_backtick_from_a_branch`, `test_violation_still_sees_a_push_after_a_powershell_escape` (4), `test_violation_allows_a_powershell_message_with_escapes`, `test_segments_keeps_a_double_quoted_backtick_in_the_text`, `test_violation_reads_the_slot_right_after_an_unpaired_powershell_backtick`, `test_violation_is_no_worse_than_before_for_a_backtick_between_commands` | pass |
| T4 (A4) process substitution | `test_violation_refuses_a_commit_in_a_process_substitution` (4), `test_segments_replaces_a_whole_process_substitution_with_the_placeholder`; the push forms are in the T2 push test | pass |
| T5 (A5) order, trust | `test_violation_runs_a_substitution_before_the_command_around_it` (5), `test_violation_carries_and_trust_into_and_through_a_substitution` (10), `test_violation_does_not_trust_a_switch_a_substitution_may_not_have_made` (2), `test_violation_deliberately_over_refuses_a_switch_inside_a_substitution` (2, pinned), `test_violation_orders_groups_as_they_are_written`, `test_violation_does_not_follow_a_switch_aimed_at_another_repository`, `test_violation_cannot_resolve_a_switch_inside_a_substitution` | pass |
| T6 (A6) main as any branch | `test_violation_refuses_a_commit_when_main_is_any_branch_it_could_land_on` (8), `test_violation_refuses_a_push_after_a_switch_to_main_that_may_have_failed`, `test_violation_allows_a_commit_after_an_untrusted_switch_to_another_branch`, `test_violation_still_refuses_after_an_untrusted_switch_away_from_main`, `test_violation_gives_the_commit_reason_then_push_then_unresolved` (4), `test_violation_cannot_resolve_a_switch_target_a_substitution_made` (7), `test_violation_reads_a_new_branch_named_by_a_substitution_as_a_switch_away` (2), `test_switch_target_marks_a_placeholder_target_unresolved`, `test_violation_allows_a_harmless_command_after_a_substituted_switch_target`, `test_violation_judges_a_substitution_in_a_detached_head` | pass |
| T7 (A7) funsub | `test_violation_plays_safe_on_every_funsub_opener` (6), `test_violation_allows_a_funsub_off_main` (6), `test_violation_allows_a_funsub_on_main_that_names_neither_commit_nor_push`, `test_violation_does_not_mistake_a_parameter_expansion_for_a_funsub`; the opener pin is `test_unmodelled_openers_is_the_documented_set` | pass |
| T8 (A8) harmless, the pipeline's form | `test_violation_leaves_harmless_and_literal_substitutions_alone` (12), `test_violation_reads_the_pipelines_own_commit_form` (2), `test_violation_reads_a_quote_inside_a_double_quote_around_a_substitution`, `test_violation_flags_ansi_c_quoting_around_a_substitution_on_main_only` | pass |
| T9 (A9) the five rewritten round 1 tests and the rest of the suite | the 409 round 1 tests plus the five rewrites, all green; the differential is step 6's. A first look (not the step 6 table): over the 508 `(command, branch)` inputs the suite passes to `violation`, each run on `main` and on `feat/x` as well, the guard at `f8775d0` and this one differ on 155 and every difference is base-allow to new-refuse, and every one contains a substitution, a funsub opener or an untrusted switch to `main` or an unresolvable target, bar one: a forged group mark in the input (`\x1egit commit -m x`), which step 3 made the guard blank, so the old guard read `\x1egit` as a word and this one reads `git` | pass |
| Bugs found by the readers (not in T1 to T9) | `test_violation_refuses_a_commit_after_a_case_pattern_inside_a_substitution` (12), `test_violation_closes_a_substitution_at_its_own_paren_after_a_case`, `test_violation_reads_case_as_a_word_only_where_a_command_could_start`, `test_segments_keeps_a_case_pattern_paren_inside_the_group`, `test_violation_still_reads_a_case_statement_outside_any_substitution` (3), `test_violation_refuses_a_commit_inside_an_arithmetic_expansion` (9), `test_violation_refuses_a_push_inside_arithmetic_from_a_branch`, `test_segments_puts_an_arithmetic_substitution_before_its_command`, `test_violation_leaves_plain_arithmetic_alone` (3), `test_segments_extracts_nothing_from_plain_arithmetic`, `test_segments_gives_an_empty_group_no_say_in_the_separator`, `test_segments_ignores_a_group_that_ran_nothing` (4), `test_violation_survives_a_deeply_nested_heredoc_body_substitution`, `test_violation_stays_fast_with_thousands_of_unclosed_openers`, `test_violation_stays_fast_and_plays_safe_on_a_hostile_run_of_openers` (5), `test_violation_refuses_what_it_cannot_finish_reading_on_main`, `test_prepare_gives_up_in_time_and_says_so`, `test_violation_judges_a_push_up_to_the_nesting_limit` (2), `test_violation_refuses_on_main_when_the_guard_itself_fails`, `test_main_exits_2_when_the_guard_fails_on_main` | pass |
| Recorded misses, pinned | `test_violation_misses_a_substitution_after_a_quote_inside_a_quoted_parameter` (2), `test_violation_does_not_judge_substitutions_nested_past_the_limit_off_main` | pass |

Gates after the step: `ruff check .` clean, `ruff format --check .` clean, `mypy` clean, `pytest` 697 passed.

**Re-test after the step 6 send-back** (the `"` appended per open `dq` frame when heredoc bodies reach the end of the input). Probed in bash with `git` shadowed (script files, `stdin` closed, 5 s timeout) against `violation()`; the probe found no defect, so no production change. 22 cases added to `tests/test_guard_git.py` (702 to 724 passed):

| Probe | Test names | Result |
|---|---|---|
| Nested dq frames, backtick holder, single quotes around and inside, a dq opened after the heredoc operator, a PowerShell backtick before the substitution, two heredocs with one unterminated, two quoted substitutions | `test_violation_closes_every_open_quote_when_a_body_reaches_the_end` (14; push refused on `main` and from a branch) | pass |
| Commit in a nested body | `test_violation_judges_a_commit_in_a_body_of_nested_quoted_substitutions` | pass |
| Harmless and data counterparts | `test_violation_allows_an_unclosed_quoted_heredoc_that_runs_no_git` (6: `git status`, plain text, nested `date`, quoted delimiter, single-quoted whole, a push after a heredoc whose body swallows it) | pass |
| Genuinely unbalanced quote, no heredoc | `test_violation_keeps_an_unbalanced_quote_without_a_heredoc_unreadable` | pass |

Gates: `ruff check .`, `ruff format --check .`, `mypy` clean, `pytest` 724 passed. Skipped on purpose: `echo "$(cat <<A\nx\nA\n$(cat <<B\n$(git push origin main)\nB)"` is allowed and bash raises a syntax error (nothing runs), so it teaches nothing the others do not.

Edge cases considered and deliberately skipped, with reasons:

- **`x="$(git checkout main)" || git commit -m x` from a branch.** Bash does not commit (the assignment succeeds, so the `||` side is skipped); the guard refuses. A safe over-refusal of the `||` rule A6 sets; not pinned, because pinning an over-refusal for every separator would be noise. The two over-refusals that matter for the pipeline's own idioms are pinned (T5).
- **The commit-position `case` heuristics** (an assignment prefix or a wrapper before `case`, `case` after `!` or `time`, a `case` with no `esac`). `case` is read only as a word at a command position, which covers the forms written by hand; the others read as before and bash itself rejects the last.
- **Timing bounds in tests** are loose (5 s and 10 s against a measured 0.3 to 1.2 s), because a tight bound would flake on a slow runner; the quadratic behaviour they guard against took tens of seconds.
- **PowerShell semantics** (`` `n ``, `if ($?) { }`) are tested through `violation()` only. `pwsh` is not installed, so what PowerShell does with them is unverified here.

Recorded for step 8, not fixed or pinned as allowed (outside section 1 or a different question):

1. **A push remote or refspec made by a substitution** (`git push origin "$(git branch --show-current)"` on `main`) is read as naming a branch called `_`, and is allowed. Verified in bash: it pushes `main`. The same on `f8775d0`. A different question from a switch target (a push has no "unresolved" state to refuse on), and the common agent idiom, so worth a round.
2. **`"${x:-'}"` and `"${x:-'$(cmd)'}"`**: in bash the single quote inside double-quoted `${ }` is literal and a later `$(git commit)` runs; the `brace` frame reads it as quoting and hides the substitution. Verified in bash; the module docstring's recorded misses now name both shapes, and both are pinned.
3. **Substitutions nested past 30 off `main`** are not judged (`echo "$(` repeated 31 times then `git push origin main` from a branch is allowed); on `main` the command plays safe. Pinned as recorded behaviour.
4. **A substituted name given to `git checkout -b`** is read as a switch away although bash would create `main` if it did not exist yet. An unreachable edge in a repository that has a `main`.

## 6. Concept check

> Written in step 6, against section 1 — not against section 2. The question is whether
> the thing built is the thing agreed, not whether it matches the plan.

Second check, tree at `77cbebc` (the first check's send-back fixed at `9a98609`, plus re-test commits). The first check's record, in one line: A2 partially met and A9 unmet because `echo "$(cat <<EOF > f\n$(git push origin main)\nEOF)"` and its backtick twin were allowed from a branch; sent back to step 3, fixed. Every command below was run against the current tree with `main` or `feat/x` as the branch; the scripts are in the scratchpad (`r6/a.py`, `r6/r1.py`, `r6/diff6.py`).

| # | Criterion | Met | Evidence |
|---|---|---|---|
| A1 | Refuses `echo "$(git commit -m x)"` on `main` | yes | Reproduction test, red against `f8775d0` and green now (see below). |
| A2 | `$( )` inside double quotes in every position | **partially** (second check) | The listed forms hold: all ten refused on `main`, `out="$(git push origin main 2>&1)"` refused from `feat/x` (`r6/a.py`, 49 of 49 over A1-A8). The first check's shapes are fixed (`echo "$(cat <<EOF > f\n$(git push origin main)\nEOF)"` and the backtick twin are now refused from `feat/x`, `r6/p1.py`: `[True, True]` for all six unquoted-delimiter forms). **But the same family is still open, two ways, both verified in bash 5.2 with `git` shadowed (`r6/q7.py`, `r6/q9.py`, `r6/t9.sh`):** (a) a body substitution of an unclosed double-quoted substitution is allowed from `feat/x` when the outer text carries a single-quoted double quote: `echo "$(echo '"' "$(cat <<EOF\n$(git push origin main)\nEOF)")"` is `[refused, allowed]`, bash pushes `main` (oracle `True`); (b) the send-back fix made the text readable, so the command that **follows** such a heredoc is now judged against a model where the heredoc swallows the rest of the input, while bash ends the heredoc and the substitution at the glued `)` and runs what follows: `echo "$(cat <<EOF\nhi\nEOF)" ; git push origin main` is **allowed on `main` and from `feat/x`** and bash pushes `main`. The guard at `5cb09c5` (before the send-back fix) refused it on `main`, so (b) is a regression introduced by the fix. See "Drift" and Halted. |
| A3 | Backticks in every position | yes | The four forms refused on `main`, ``echo `git push origin main` `` refused from `feat/x` (`r6/a.py`); PowerShell escapes pinned by `test_violation_still_sees_a_push_after_a_powershell_escape` and `test_violation_allows_a_powershell_message_with_escapes` (pass). |
| A4 | Process substitution | yes | `diff <(git commit -m x) /dev/null`, `tee >(git commit -m x) </dev/null` refused on `main`; `diff <(git push origin main) f` refused from `feat/x` (`r6/a.py`). |
| A5 | Substitution runs before its command; `&&` trust carries in | yes | The three order forms refused from `feat/x`; `git checkout -b feat/y && out="$(git commit -m y)"` allowed on `main` (`r6/a.py`). Bash agrees on all of them (`scratchpad/oracle.py`, 18 cases x 2 branches: the guard never allows what bash lands on `main`; it over-refuses only where it plays safe). |
| A6 | `main` as any branch it could land on | yes | The five untrusted-switch forms refused from `feat/x`; `git checkout feat/y; git commit -m x` allowed from `feat/x`; `git checkout -b feat/x; git commit -m x` refused on `main` (`r6/a.py`). |
| A7 | Funsub plays safe | yes | The three forms refused on `main`, allowed from `feat/x`, and `echo ${ ls; }`, `echo ${| ls; }`, `echo "${ ls; }"` allowed on `main` (`r6/a.py`). `UNMODELLED_OPENERS` equals the ten-element tuple (`test_unmodelled_openers_is_the_documented_set`). |
| A8 | Harmless substitutions left alone; the pipeline's commit form | yes | The four harmless commands allowed on `main`; the pipeline's `git commit -m "$(cat <<'EOF' ... EOF\n)"` and the apostrophe-and-`)` form refused on `main`, allowed on `feat/x`, and allowed on `main` after `git checkout -b x &&` (`r6/a.py`, 49 of 49 across A1-A8). |
| A9 | Changes nothing else | **no** (second check) | Suite, tests clause and round 1: fine (724 passed; the five rewrites; the sixth changed test and the forged-mark input are for the user, below). The differential, recaptured over the 724-test suite (469 distinct commands, 564 pairs), has **11 rows where the new guard allows what bash lands on `main`** (table below), against A9's rule that the new decision must match bash or be the play-safe refusal on `main`; 5 of them are on `main` itself and are base-refuse to new-allow regressions. Everything else in the table is inside A9's exception set. **Note for the user (1):** a sixth round 1 test changed, `test_unmodelled_openers_is_the_documented_set`, because the constant's value is what the plan changes; A9's text says five. **Note for the user (2):** the forged-mark input `'\x1egit commit -m x'` is refused by the new guard and was allowed by the baseline (plan step 2 blanks `\x1d`/`\x1e` in the input), the single difference outside A9's literal exception set. |

### Fix-round evidence

**Reproduction criterion.** Red run: section 3 holds step 3's paste, run before any production change. Step 6 re-ran it: the test body copied unchanged into a scratch file and run against `git show f8775d0:.claude/hooks/guard_git.py` (scratchpad `r6/hooks`, never the tree):

```
E        +      where '' = violation('echo "$(git commit -m x)"', 'main')
FAILED tests/test_repro.py::test_violation_refuses_a_commit_in_a_double_quoted_substitution_on_main
1 failed
```

Green now, against the tree: `tests/test_guard_git.py::test_violation_refuses_a_commit_in_a_double_quoted_substitution_on_main PASSED`; whole suite `724 passed`, `ruff check .`, `ruff format --check .`, `mypy` clean.

**Root cause removed where the Defect block puts it, not at the symptom.** Row (1): `_prepare`/`_scan` (`guard_git.py:710`, `:749`) now extract each substitution into a group of invocations that `segments` (`:1087`) places before the invocation that contains it, so `violation` judges text it used to pass through unseen; the heredoc extraction takes the same slot (order fix). Row (2): `violation` (`:1323`, `_judge` `:1344`) holds the set of branches and no longer falls back to the starting branch after a separator that guarantees nothing. No other file in the hook set changed, and `echo "$(git commit -m x)"` is refused because the inner command is judged, not because the word `commit` is searched for in the text.

**Class (Scope: the class).** Every input the Class row lists has a test (Test log, section 5: T2 to T7 plus the readers' additions); funsub is the play-safe the user chose. The one bash 5.3 construct is unverified here by design.

**Out of scope held.** `bash -c`, `eval`, aliases: no code reads a program's string argument. `WRAPPERS`, `OPTIONS_WITH_VALUE`, `PUSH_OPTIONS_WITH_VALUE`, `GIT_NAMES` unchanged in the diff against `f8775d0`. No reserved-word handling (`if git commit`, `do git push`, `! git commit`) was added. Hex-escaped subcommands untouched. Nothing was built outside section 1; the runaway-input budget and fail-closed `violation` (section 3) are internal hardening that a new recursive pass needs, they add no behaviour a criterion does not already imply.

### A9: the differential (T9)

Second check, rerun exactly as the first (`r6/diff6.py`, output `r6/diff6_out2.txt`). Baseline `git show f8775d0:.claude/hooks/guard_git.py`, registered in `sys.modules` before `exec`. Corpus recaptured because the suite grew to 724 tests: the 564 `(command, branch)` pairs (469 distinct commands) that `tests/test_guard_git.py` passes to `violation`, captured by the scratch plugin `r2t/capplug.py` (`-p`). Variants: itself, `echo "$(C)"`, ``echo `C` ``, `cat <(C)`, `git checkout main;C`, `git checkout -;C`; each on `main` and `feat/x`. Oracle: bash with `git` shadowed, `HEAD` and the previous branch kept in files, `PATH` emptied, `stdin=/dev/null`, 10 s timeout in its own process group. Exempt, as before: the 13 hostile-nesting inputs longer than 300 characters (kept out of bash; they fork-bomb) and the inputs bash rejects as a syntax error (35 plain ones, PowerShell-only or deliberately unbalanced).

| Variant | Judged | Same as base | Base allow, new refuse | of which bash lands on `main` | of which play-safe (substitution, funsub or switch present) | Base refuse, new allow | New allows, bash lands on `main` | Unaccepted |
|---|---|---|---|---|---|---|---|---|
| plain | 868 | 741 | 120 | 27 | 92 | 3 | 2 | 1 |
| `"$( )"` | 784 | 486 | 270 | 90 | 180 | 28 | 3 | 0 |
| backticks | 814 | 588 | 196 | 43 | 153 | 30 | 2 | 0 |
| `<( )` | 794 | 567 | 202 | 51 | 151 | 25 | 0 | 0 |
| `git checkout main;` prefix | 842 | 541 | 298 | 27 | 271 | 3 | 2 | 0 |
| `git checkout -;` prefix | 842 | 537 | 302 | 27 | 275 | 3 | 2 | 0 |

4,944 judged inputs, 554 more that bash rejected as a syntax error (exempt), and 4 plain inputs the baseline overflowed the stack on. Reading it:

- **Base allow, new refuse** (1,388 rows): 265 land on `main` in bash, 1,122 carry a substitution, a funsub opener or a switch and are the play-safe refusal, and 1 is the forged group mark `'\x1egit commit -m x'` (accepted by the plan, above). No other unexplained difference.
- **Base refuse, new allow** (92 rows): 81 are inputs bash does not land on `main` for (the subshell and escaped-substitution rows of the first check, the `-b`/`-B`/`-c` switch-then-commit inside a substitution, quoted-delimiter heredoc bodies, which are data); the new decision matches bash, as A9 allows. The other 11 are the next bullet.
- **New allows, bash lands on `main`** (11 rows, 2 shapes, none play safe):
  1. `echo "$(cat <<EOF\nit's\nEOF)" ; git push origin main` and its wrappers (inside a second `"$( )"`, inside backticks, after `git checkout main;` and `git checkout -;`), on **both** `main` and `feat/x` (10 rows). Bash ends the heredoc and the substitution at `EOF)` and pushes; the guard treats the heredoc as swallowing the rest of the input. The baseline refused it on `main` (4 of the 5 `main` rows; the nested one was allowed there too) and the guard at `5cb09c5` refused it on `main`; the send-back fix lets it through.
  2. `echo "$(echo '"' "$(cat <<EOF\n$(git push origin main)\nEOF)")"` from `feat/x` (1 row): a body substitution of an unclosed double-quoted substitution, allowed while bash pushes `main`; refused on `main`.
  The same glued-closer follow-up is allowed with a quoted delimiter and with no double quote at all (`x=$(cat <<EOF\nhi\nEOF); git push origin main` is allowed on `main` by the baseline, round 1's guard and this one: a pre-existing miss in round 1's model of heredocs inside substitutions, listed in `r6/q8.py`).

**A9 test clause.** `git diff f8775d0..HEAD -- tests/test_guard_git.py`, removed or modified lines only:

| Changed test | In A9's five | Judgement |
|---|---|---|
| `test_violation_does_not_carry_an_unresolvable_switch_across_a_weak_join` (renamed `test_violation_refuses_after_an_unresolvable_switch_across_a_weak_join`) | yes | pins `git checkout - ; git commit` as allowed from a branch, which A6 refuses now |
| `test_violation_does_not_look_inside_quotes_within_a_body_substitution` (renamed `test_violation_looks_inside_quotes_within_a_body_substitution`) | yes | pinned the miss |
| `test_segments_puts_a_body_substitution_on_its_own_line_after_the_command` (renamed `..._before_the_command_that_opened_it`) | yes | pinned the after-order |
| `test_segments_orders_dollar_paren_and_backtick_substitutions_as_written` | yes | pinned positions in `segments` |
| `test_segments_unescapes_a_nested_backtick_pair_for_the_inner_command` | yes | dropped `parsed[1].tokens[0] == "echo"`, pinned a position |
| `test_unmodelled_openers_is_the_documented_set` | **no, a sixth** | the constant's value is what the plan changes (A7, T7, Public API), so the assertion had to follow; the orchestrator judged it mechanical and told the user. It leaves A9 met in substance: no behaviour the old assertion guarded is lost (the six old openers are still the first six, in order). The literal text of A9 says "five", so the user should see this row. |
| import list (`SUBSTITUTED` added) | n/a | |

All other 409 round 1 tests are byte-identical and pass. `ruff check .`, `ruff format --check .`, `mypy` clean; `pytest` 724 passed (re-run for this check).

### Drift found, and what was done about it

1. **First check (A2/A9), sent back and fixed.** `echo "$(cat <<EOF > f\n$(git push origin main)\nEOF)"` and its backtick twin allowed from a branch; fixed at `9a98609` by closing the open quotes when a heredoc body reaches the end of the input. Verified again now: `r6/p1.py` gives `[True, True]` on all six unquoted-delimiter forms, and the quoted `<<'EOF'` forms stay allowed (data).
2. **Second check, A2/A9 unmet again, same family: HALT.** The fix rests on a model of the construct that bash does not follow. In bash 5.2 (`r6/t7.sh`, `r6/t9.sh`, `git` shadowed) a heredoc inside `$( )` whose closing line is glued to the `)` (`EOF)`) ends there, and the `)` closes the substitution: `echo "$(cat <<EOF\nhi\nEOF)" ; git push origin main` prints `RAN git push origin main` (with the "delimited by end-of-file" warning). The guard keeps modelling "the heredoc swallows the rest of the input", which the send-back fix only made *readable* by appending quotes. Consequences, all verified against bash and against `5cb09c5` (`r6/q8.py`, `r6/q9.py`): (a) `echo "$(cat <<EOF\nhi\nEOF)" ; git push origin main` was refused on `main` before the fix and is allowed now on `main` and `feat/x` (a regression the fix introduced; the baseline also refused it on `main`, as it did with `\n` instead of ` ; ` and with a quoted `<<'EOF'`, which are allowed now), (b) the first check's own shape is still allowed from `feat/x` when a single-quoted double quote precedes the inner substitution: `echo "$(echo '"' "$(cat <<EOF\n$(git push origin main)\nEOF)")"`, (c) the same follow-up command after the plain unquoted `x=$(cat <<EOF\nhi\nEOF); git push origin main` has been allowed since the baseline. Not a code fix to guess at: either the heredoc-in-substitution model changes (a glued `)` closes both), which reaches round 1's heredoc handling and the unquoted form that section 1 did not name, or the guard plays safe on `main` for any heredoc that reaches the end of the input inside an open substitution (restoring what the baseline did on `main`, and still leaving `feat/x` open). Both decide the scope of A2/A9, and a third attempt would be a guess. See Halted.
3. **Forged `\x1d`/`\x1e` in the input** reads differently from the baseline (over-refusal, plan-mandated). Not a code defect; surfaced above for the user, no change made.
4. **`STRUCTURE.md`**, from the `structure-auditor` report of the first check: applied then; no change in this check (no production change since).

### Earlier rounds still hold

> Later rounds only. Re-check every acceptance criterion from every earlier round in this
> folder: this round changed code they depend on, and their tests passing is necessary but
> not sufficient — a criterion can be satisfied by tests that no longer describe what the
> feature does.

Re-run directly against the code as it stands (`r6/r1.py`, 25 commands, 0 failures, second check) in addition to the 409 unchanged tests passing.

| Round | # | Criterion | Still met | Evidence |
|---|---|---|---|---|
| 1 | A1 | The reported `python3 - <<'EOF'` with a stray quote is allowed on `main` | yes | allowed; `r6/r1.py` |
| 1 | A2 | Heredoc body is data (quoted delimiters, `<<-`); `$( )`/backtick of an unquoted body judged on `main` and from a branch; command after the heredoc judged; `git commit -F - <<'EOF'` refused on `main`, allowed on `feat/x` | yes | data forms allowed; `cat <<EOF > f\n$(git commit -m x)\nEOF` refused on `main`; the backtick push refused on `main` and `feat/x`; the trailing commit refused; `commit -F -` refused/allowed as stated (11 checks, `r6/r1.py`) |
| 1 | A3 | `#` read as bash reads it | yes | `# it's fine\ngit commit -m x\n# that's it` refused; `echo ok # git commit -m x` allowed; `echo ok#1 && git commit -m m` refused |
| 1 | A4 | Backslash-newline joins | yes | `git \\\ncommit -m x` refused; `git \\\npush origin main` refused from `main` and `feat/x` |
| 1 | A5 | Unmodelled forms play safe on `main` only | yes | `$'`, here-string, `<# #>`, backtick-quote and heredoc-plus-comment forms refused on `main` and allowed on `feat/x`; the same without commit or push allowed on `main` |
| 1 | A6 | Changes nothing else: existing tests unmodified, differential, accepted `&&` plus `$'...'` cost | yes, with this round's declared exceptions | the 409 tests pass, with the six edits tabled in A9 above; the accepted cost (`git checkout -b x && git commit -m $'a'` on `main`) is still refused |

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

### Halt at step 6, round 2, second concept check

**Step:** 6 (Concept check), second run; the first run sent A2/A9 back to step 3 and that fix was verified.

**Reason:** A2 and A9 are unmet again for the same family: a heredoc inside a double-quoted `$( )` that bash closes at `EOF)`. Two verified failures (bash 5.2, `git` shadowed): `echo "$(echo '"' "$(cat <<EOF\n$(git push origin main)\nEOF)")"` is allowed from `feat/x` (a body substitution of an unclosed double-quoted substitution, the first check's reason), and `echo "$(cat <<EOF\nhi\nEOF)" ; git push origin main` is allowed on `main` and from `feat/x` although `5cb09c5` refused it on `main` (a regression the send-back fix introduced). The differential has 11 rows where the new guard allows what bash lands on `main`.

**Question for the user:** how far does A2/A9 go for a heredoc inside a substitution?
1. Model bash's rule (a closing line may carry the `)` that closes the substitution) for every `$( )` / backtick / `<( )`, quoted or not. Closes both failures and the baseline miss for `x=$(cat <<EOF\nhi\nEOF); git push origin main`, but it reaches round 1's heredoc handling.
2. Play safe: a heredoc that reaches the end of the input inside an open substitution sets the unmodelled flag, so `main` refuses (what the baseline did) and a branch is judged as parsed. Restores `main`, leaves `feat/x` open for these shapes, and A9's text would need to name that.
3. Amend A2/A9 to say which of these shapes are out of scope, with a recorded miss.

**State:** tree clean at `77cbebc` plus this section 6; no production change in this check; marker left at step 6.
