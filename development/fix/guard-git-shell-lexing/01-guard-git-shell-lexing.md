# The git guard reads commands the way the shell does

<!-- claude-plan step=2 status=active -->

| Field | Value |
|---|---|
| Feature | `fix/guard-git-shell-lexing` |
| Round | `1` |
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

Nothing — this is the first round.

---

## 1. Concept

### Defect

| Field | Value |
|---|---|
| Observed | On `main`, a Bash command running an inline Python heredoc (`python3 - <<'EOF' ... EOF`) whose body held `'''` strings, an apostrophe (`` `main`'s ``) and the words commit/push was refused: "this command could not be read — an unbalanced quote, most likely — and it names `commit` or `push` while `main` is checked out". `bash -n` accepts it and it runs no git. The same mechanism also **allows** real commits and pushes to `main`. |
| Expected | The module docstring: the guard "reads the command the way a shell does" and refuses a commit or push that would land on `main`. A harmless heredoc is allowed; a real commit on `main` is refused. |
| Reproduction | `guard_git.violation(cmd, "main")`; "runs" means bash with `git` shadowed by an echo function. False refusals: `python3 - <<'EOF'\nx = '''main's push'''\nEOF` → refused (unreadable); `cat <<'EOF' > notes.txt\ngit commit -m x\nEOF` → refused (body read as a commit); `cat <<-EOF\n\tdon't push\n\tEOF` → refused. Bypasses (guard allows, bash runs git on `main`): `# it's fine\ngit commit -m x\n# that's it`; `git \\\ncommit -m x`; `git \\\npush origin main`; `cat <<EOF >/dev/null\nit's\nEOF\ngit commit -m x # '`; `echo $'it\'s'; git commit -m x # '`; PowerShell `$m = @'\nit's\n'@\ngit commit -m x # '`, `<# it's #>\ngit commit -m x # '`, `$x = "say ``"hi"; git commit -m x # "`. |
| Root cause | `.claude/hooks/guard_git.py:327-336` — `segments()` hands the raw command to Python's `shlex` as if `shlex` were the shell. `shlex` does not model: `#` starting a comment only at the start of a word and running to end of line (commenters are disabled at :332 on purpose, to keep `echo ok#1` intact); heredoc bodies (`<<`, `<<-`, quoted or unquoted delimiter) being literal data; backslash-newline being a line continuation; `$'...'` escapes; PowerShell backtick escapes, `<# #>` block comments and `@'`/`@"` here-strings. Each gap either makes a valid command look unbalanced (→ `None` → refused on `main` when the raw text names commit/push anywhere, body included) or pairs quotes across commands / glues a newline onto a word, hiding a real git invocation (→ allowed). |
| Introduced by | `009f6e3` (2026-09-21, "Rebuild guard_git.py's parsing"), which introduced the `shlex` lexer. |
| Class | The constructs listed under Root cause. Handled correctly today, for contrast: `echo "it's"; git commit` refused; `echo ok # git commit -m x` allowed; PowerShell `'it''s'` refused; bash `<<<` here-strings fine. Same shape elsewhere: no other hook parses shell text. |
| Blast radius | `violation()` is called only from `guard_git.main()`. Nothing depends on the wrong behaviour. Constraining tests: `tests/test_guard_git.py:440-452` (`#` inside a word is not a comment) and the PowerShell here-string commit test near :486. No existing heredoc tests. The module docstring and the guard's `STRUCTURE.md` section describe the lexing and change with it. |
| Scope | `the class` — the user's decision: the bypasses are the real harm, and a heredoc-only fix would pass its reproduction while `# it's fine\ngit commit -m x` still commits to `main`. Approach also the user's: read the common bash forms exactly, play safe on the rare ones (Option 1 of three). |

Critique — the `diagnosis-critic`'s findings (verdict: cause confirmed, class incomplete) and what was done with each:

1. The comment-quote bypass needs no heredoc — applied: the cause was widened from "heredoc bodies" to "shell lexing rules `shlex` does not model", and the comment case is its own criterion (A3).
2. Backslash-newline is not removed as a continuation — applied and verified in bash (A4).
3. `$'...'` quoting — applied to the class (A5).
4. PowerShell backtick escapes and `<# #>` block comments — applied to the class (A5); verified only through `violation()`, since `pwsh` is not installed here.
5. The `RISKY_PATTERN` fallback only ever errs towards refusing and is not the bypass source — applied: the fallback stays as it is.

### What this is

The guard stops reading the contents of three common bash constructs as commands and reads
them the way bash does: a heredoc body is data up to its closing delimiter line, a `#` at
the start of a word comments out the rest of its line, and a backslash at the end of a line
joins it to the next. For the rarer constructs it does not learn — `$'...'` strings and
PowerShell's backtick escapes, `<# #>` comments and here-strings — it plays safe: a command
containing one is treated as unreadable, so it is refused on `main` when it names commit or
push and allowed everywhere else, which is how unreadable input is already treated. Every
bypass in the reproduction is closed, and the reported heredoc is allowed.

### Why it is worth building

See the Defect block.

### Inputs and outputs

Unchanged: `violation(command, branch)` takes the command text and the checked-out branch and
returns a refusal reason or `""`; `segments(command)` returns the invocations or `None` when
the command cannot be read. Only which commands land in which outcome changes.

### How it connects to the rest of the repo

Changes `.claude/hooks/guard_git.py` (the lexing that feeds `segments()`), its tests in
`tests/test_guard_git.py`, its module docstring and its section of `STRUCTURE.md`. The hook is
registered for both the Bash and PowerShell tools in `.claude/settings.json`, which does not
change. No other hook parses shell text.

### Explicitly out of scope

- A git invocation inside another program's text argument — `bash -c "git commit"`, `eval`,
  `sh -c`, shell aliases and functions. A different cause: the guard does not look inside
  string arguments at all. For step 8.
- The documented `sudo -u me git push` miss and wrappers not on the list — deliberate
  trade-offs recorded in the module docstring.
- Reading `$'...'` and the PowerShell-only forms exactly (Option 2). They play safe instead.
- Choosing a dialect from the payload's tool name. One reading serves both shells, as today.

### Acceptance criteria

All judged by the guard's decision with `main` checked out unless stated otherwise.

| # | The finished feature... |
|---|---|
| A1 | Given the reported command — `python3 - <<'EOF'`, a body holding `x = '''main's push'''`, then `EOF` — allows it on `main`, where today it refuses it as unreadable. |
| A2 | Never reads a heredoc body as commands: `cat <<'EOF' > notes.txt\ngit commit -m x\nEOF` is allowed; a `<<-` heredoc with a tab-indented closing delimiter and a stray apostrophe in the body is allowed; bodies after `<<EOF`, `<<'EOF'` and `<<"EOF"` all count as data. A command after the heredoc is still judged: `cat <<EOF > f\nhello\nEOF\ngit commit -m x` is refused. A commit taking its message from a heredoc — `git commit -F - <<'EOF'\nfix main's guard\nEOF` — is refused as a commit to `main`, not as unreadable, and is allowed on `feat/x`. |
| A3 | Reads `#` as bash does: `# it's fine\ngit commit -m x\n# that's it` is refused; `echo ok # git commit -m x` is allowed; `echo ok#1 && git commit -m m` is still refused. |
| A4 | Joins a backslash-newline: `git \\\ncommit -m x` is refused; `git \\\npush origin main` is refused from `main` and from `feat/x`. |
| A5 | Plays safe on the rare forms: every remaining bypass from the reproduction — `echo $'it\'s'; git commit -m x # '`, the PowerShell here-string, `<# it's #>` and backtick-quote cases, and `cat <<EOF >/dev/null\nit's\nEOF\ngit commit -m x # '` — is refused on `main`. A command using one of these forms that names neither commit nor push is allowed on `main`, and all of them are allowed on `feat/x`. |
| A6 | Changes nothing else: every existing test in `tests/test_guard_git.py` passes unmodified, and a differential over a corpus — every command string in the existing tests plus generated variations — gives the same allow/refuse decision as the guard on `main`, except for the inputs named in A1–A5. |

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
