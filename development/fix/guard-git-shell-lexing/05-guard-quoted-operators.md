# The git guard never takes a quoted word for an operator

<!-- claude-plan step=2 status=active -->

| Field | Value |
|---|---|
| Feature | `fix/guard-git-shell-lexing` |
| Round | `5` |
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
| 3 | `03-guard-reserved-words.md` | Shell reserved words stepped over to find git; a `!`/`coproc`-led switch only widens `&&` trust; a switch anywhere in a loop counts for the whole loop; leaders read as arguments open no `case`. |
| 4 | `04-guard-trust-after-or.md` | After an `\|\|` operand, `&&` trusts the union of what both sides trusted (create-or-switch stays allowed); the `!`/`coproc` scope keyed by substitution depth and group level, ended by `\|\|` and `case` terminators at its own key; `_segments` hands out raw operator runs with their depth and a substitution-close marker. 1161 tests, 0 bypass rows in an 18,260-row differential against bash. |

This round came from recommendation `R1` of round 4, which read:

> **Read quoting and command position in the tokenizer, so a quoted separator word (`echo ";"`, `echo "&&"`, `'&'`, `\;`), a literal brace or paren word (`echo {`, `echo '('`) and a carriage return after an operator are never taken for operators.** — Each lets a commit land on `main` while the guard allows it, checked in bash with `git` shadowed: `true || echo ";" | git checkout -b x && git commit -m x` and the eight rows in round 4's section 5, plus `git checkout -b x &&\r\ngit commit -m x` (round 4's section 6). Older than this branch (`segments('echo ";" x')` splits into two segments since round 1; 43eeea3 allows every row), and round 4 made the tokens load-bearing for the `||` operand and the `!` scope. Effort: large.

Round 4's step 8 reader also suggested a committed operator-pair matrix with an opt-in bash
oracle (round 4, section 8 notes) — a candidate for this round's plan, since this round rewrites
the tokenizer every rule reads.

What is already on the branch that this round must not break: every acceptance criterion of
rounds 1 to 4 (step 6 re-checks them), the 1161 guard tests, and in particular quoting inside
commit messages, heredoc and comment handling, substitution extraction, the `||` operand union and
the `!` scope.

---|---|---|

This round came from recommendation `<R#>` of round `<N>`, which read:

> <the recommendation, quoted from that round's section 8>

What is already on the branch that this round must not break:

---

## 1. Concept

### Defect

| Field | Value |
|---|---|
| Observed | `violation('true \|\| echo ";" \| git checkout -b x && git commit -m x', "main")` returns `""` (allowed). In bash 5.2 with `git` shadowed by a function keeping HEAD in a file (`PATH=/usr/bin:/bin`, the oracle shown live by a plain commit), it prints `COMMIT on main`. `segments('echo ";" x')` returns two invocations, `echo` and `x` with separator `;`. |
| Expected | Refused with the commit reason, and `echo ";" x` read as one invocation. STRUCTURE.md and the module docstring promise "`shlex` resolves quoting, so a `;` or `\|` inside a commit message stays part of the message"; round 4's criteria promise the `\|\|` operand and `!` scope end only at a real list end. |
| Reproduction | The call above. Also allowed, all `COMMIT on main` in bash: the same with `"&&"`, `'&'`, `\&`, `-exec true \;`, `echo {`, `echo '('`, `echo ";"";"`; `{ true \|\| echo } \| git checkout -b x && git commit -m x; }`; `! true \| echo ';' \| git checkout -b feat/x && git commit -m x` (feat/x exists, so the checkout fails); `git checkout -b feat/x &&\r\ngit commit -m x` on `main` with feat/x existing (bash reads `\r` as a failing command word after `&&`, then the newline ends the list), also `&&\r\n\r\n` and `&& \r\n`. |
| Root cause | (1) `.claude/hooks/guard_git.py:1242`, `_lex` runs posix `shlex`, which resolves quotes and escapes and keeps no record that `";"`, `'&&'`, `\;` or `\&` was quoted; `_is_separator` (`:329`, `set(token) <= SEPARATOR_CHARS`) is the site — by then a quoted `;` and a real one are the same string — and `_segments` (`:1329`/`:1333`) splits on it. Round 4's `_walk_run` keys on those false operators, so an `\|\|` operand or a `!` scope ends early or the group level shifts. A bare `{`/`}` word in argument position is read as a group the same way. (2) A separate cause of a different kind: `INLINE_WHITESPACE = " \t\r"` (`:197`) makes `\r` whitespace, deleting a word bash runs, so the `&&` before it is trusted; `_COMMENT_BOUNDARY` (`:293`) and `_DELIMITER_END` (`:297`) already exclude `\r`. |
| Introduced by | Older than this branch: `_lex` with `punctuation_chars`, `_is_separator` and `INLINE_WHITESPACE` are on `main` (009f6e3, "Rebuild guard_git.py's parsing"). Round 4 made the false operators load-bearing for the `\|\|` operand and the `!` scope. |
| Class | (1) A quoted or escaped token made only of operator characters: `;`, `&&`, `&`, `\|`, `\|\|`, `(`, `)`, `{`, `}`, a quoted newline, concatenations like `";"";"` and `a';'`. Several are refused today only by which operator they become (`')'`, `'}'`, `'\|'`, `\|\|`, `a';'`, `{}`, `{ }`, `-exec true {} +`), so the criterion holds on `segments` as well as on `violation`. (2) A bare `{`/`}` in argument position. (3) `\r` before a newline after an operator. (4) Over-refusals of the same family (bash runs no git): a quoted word at command position read as a leader, an assignment or a redirection — `'if' git commit -m x` (round 3 pinned it), `'!' git checkout -b x && git commit -m x`, `"X=1" git commit -m x`, `'>' x git commit -m x` — and `echo ";" git commit -m x`, `git checkout feat/y ";" git commit -m x`. **Shell constraint:** the guard runs for the PowerShell tool too and reads both shells the same way (module docstring, `main()` never reads `tool_name`). Single and double quotes make a string in both shells, so a quoted token is never an operator in either. But `\` is not an escape in PowerShell (`echo \; git commit` runs the commit there), a bare `{` after a command word is a scriptblock that runs (`ForEach-Object { git commit -m x }`, `Invoke-Command -ScriptBlock { … }`, `Start-Job { … }`, refused today only because `{` splits), and `\r` is a line terminator there (`&&\r\n` is a real `&&` in PowerShell 7). |
| Blast radius | `_lex`'s callers: `_segments` (`:1307`) and the pre-pass check (`:965`, which only tests for `None`). Tests that pin current behaviour: `tests/test_guard_git.py:2429` (`git checkout -b feat/y &&\r\ngit commit -m "$(date)"\r\n` allowed), the CR heredoc tests (`:971`, `:2056–2073`), and round 3's quoted-leader over-refusal pins. The module docstring's "reads both the same way" and STRUCTURE.md's matching text. Nothing depends on the wrong answer. |
| Scope | `the class`, played safe for both shells — the user's choice over "quotes only" and over a guard that reads which shell sent the command: quotes are text in both shells, and for the three shell-dependent tokens the guard only ever refuses more, in either shell, with no new dependency on the payload. |

Critique — the `diagnosis-critic`'s findings and what was done with each (verdict: cause confirmed, class incomplete):

1. **Two parts of the class are right for PowerShell, so fixing them by bash's rules opens PowerShell misses.** Applied: the shell constraint in the Class row and the both-shell-safe scope; bare `{`/`}`, `\` escapes and `\r` keep splitting and only lose their power to end a scope, shift a group level or carry `&&` trust (A3, A4).
2. **The `\r` case is a separate cause, a deleted word rather than an added separator.** Applied: Root cause (2) and its own criterion (A4).
3. **Escapes lose quoting too, and false separators that are harmless today still distort `segments`.** Applied: escapes in the Class row; A2 states the criterion on `segments`.
4. **Quoted words at command position read as leaders, assignments or redirections.** Applied: Class (4) and A5, with a quoted program name still counting.
5. **Docstring, the pre-pass check and Windows CRLF delivery.** Applied: Blast radius; CRLF delivery could not be established, so A4 plays safe instead of relying on it.

### What this is

A word written in single or double quotes is never an operator, a group delimiter, a reserved
word, an assignment or a redirection, in either shell: the fix keeps the record of quoting that
`_lex` (`:1242`) loses today, so `_is_separator` (`:329`) no longer sees a quoted `;` as a real one.
Three tokens mean different things in bash and PowerShell — a backslash-escaped operator
character (`\;`, `\&`), a bare `{` or `}` used as an argument, and a carriage return before a
line break — and for those the guard plays safe for both shells: they still split the command as
they do today, so PowerShell's `ForEach-Object { git commit }` stays refused, but they can no
longer end an `||` operand or a `!` scope or shift the group level, and an `&&` followed by a
carriage return is not trusted. A quoted program name still counts: `"git" commit -m x` runs git in
bash and stays refused.

### Why it is worth building

See the Defect block: a silent commit to `main` in ordinary shell, against the rule `CLAUDE.md`
sets and the guard exists to enforce.

### Inputs and outputs

Unchanged: `violation(command, branch)` takes the command line and the checked-out branch and
returns a refusal reason or `""`; `segments(command)` returns the invocations. Only which
commands are refused, and how a quoted operator word is split, change.

### How it connects to the rest of the repo

Changes the tokenizer (`_lex`, `_is_separator`, `_segments`) and the run walk (`_walk_run`,
`_judge`) in `.claude/hooks/guard_git.py`; `guard_git.main` (the `PreToolUse` hook) calls it
through `violation`. Tests in `tests/test_guard_git.py`; prose in the module docstring and
STRUCTURE.md's guard section. No other hook touches it.

### Explicitly out of scope

Recorded in the plan file, not in `DEVELOPMENT.md` (the user's instruction):

- reading the payload's `tool_name` to apply each shell's exact rules (the user chose
  both-shell-safe instead);
- `$'…'` ANSI-C strings, which `UNMODELLED_OPENERS` already plays safe on;
- the hex-escape and split-quote subcommand misses (round 1), the lone `'` in a quoted `${ }`
  (round 2);
- round 3's recorded misses (variable switch target, compound-command redirection order,
  PowerShell glued braces and `ForEach-Object` pipelines, the `coproc`/`&` loop race, unlisted
  wrappers, functions judged where defined);
- a committed bash oracle test (round 4's step 8 note), a candidate for this round's plan but not
  a criterion.

### Acceptance criteria

| # | The finished feature... |
|---|---|
| A1 | Given `true \|\| echo ";" \| git checkout -b x && git commit -m x` with `main` checked out, `violation` refuses with the commit reason rather than returning `""`. |
| A2 | A quoted token is never an operator: `segments('echo ";" x')` returns one invocation (`echo`, `;`, `x`), and the same holds for `"&&"`, `'&'`, `'\|'`, `'\|\|'`, `'('`, `')'`, `'{'`, `'}'`, a quoted newline, `";"";"` and `a';'`; every `\|\|`- and `!`-form built on one (the Reproduction row's quoted forms, `! true \| echo ';' \| …`) is refused on `main`. |
| A3 | The shell-dependent tokens play safe: the forms with `\;`, `\&`, `-exec true \;`, and a bare `{` or `}` argument (`true \|\| echo { \| …`, `{ true \|\| echo } \| …; }`) are refused on `main`, and `Get-Item . \| ForEach-Object { git commit -m x }`, `Invoke-Command -ScriptBlock { git commit -m x }` and `Start-Job { git push origin main }` stay refused on `main`. |
| A4 | `git checkout -b feat/x &&\r\ngit commit -m x`, `&&\r\n\r\n` and `&& \r\n` are refused on `main`; `tests/test_guard_git.py:2429` changes from allowed to refused (agreed with this concept); `git commit\r\n`, `git push\r\n` and `git push origin main\r\n` stay refused. |
| A5 | A quoted word at command position is not shell syntax: `'if' git commit -m x`, `'!' git checkout -b x && git commit -m x`, `"X=1" git commit -m x`, `'>' x git commit -m x` and `echo ";" git commit -m x` are allowed on `main` (round 3's quoted-leader pins change to allowed, agreed with this concept); `"git" commit -m x` stays refused. |
| A6 | Nothing else changed: the existing tests pass unmodified except the changes A4 and A5 name, and rounds 1–4's criteria still hold; a differential against the guard at 8972524 over the suite's commands with quoted, escaped, bare-brace and carriage-return variants sends every differing row to bash with `git` shadowed — the oracle first shown live by a plain commit landing on `main` — and every difference involves one of those tokens, with the oracle agreeing or the new refusal play-safe, and zero rows where the new guard allows a commit or push that bash lands on `main`. |

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
