# The git guard judges command substitutions inside a word

<!-- claude-plan step=3 status=active -->

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
