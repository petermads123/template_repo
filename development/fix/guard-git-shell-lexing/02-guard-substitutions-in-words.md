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
| A9 | Changes nothing else: round 1's A1–A6 still hold; every existing test passes, except `tests/test_guard_git.py:1620-1627` and `test_segments_puts_a_body_substitution_on_its_own_line_after_the_command`, which are rewritten to the new behaviour; and a differential against the guard as round 1 left it (commit `f8775d0`) over every command the existing suite passes to the guard plus generated variations agrees, except where the input contains a command substitution, a funsub opener or an untrusted switch to `main` or an unresolvable target — and there the new decision matches bash with `git` shadowed, or is the play-safe refusal on `main`. |

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
