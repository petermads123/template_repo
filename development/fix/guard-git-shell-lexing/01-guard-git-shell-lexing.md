# The git guard reads commands the way the shell does

<!-- claude-plan step=8 status=active -->

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
| 2 | Plan | `/plan` | with the user | done |
| 3 | Implement | `/implement` | in `/build` | done |
| 4 | Verify | `/verify` | in `/build` | done |
| 5 | Test | `/test` | in `/build` | done |
| 6 | Concept check | `/concept-check` | in `/build` | done |
| 7 | Ship | `/ship` | in `/build` | done |
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
| A2 | Reads a heredoc body as bash does: the text of a body is never read as commands — `cat <<'EOF' > notes.txt\ngit commit -m x\nEOF` is allowed, and a `<<-` heredoc with a tab-indented closing delimiter and a stray apostrophe in the body is allowed. A body after a quoted delimiter (`<<'EOF'`, `<<"EOF"`, `<<\EOF`) is pure data. In a body after an unquoted delimiter (`<<EOF`) bash runs `$( … )` and backtick command substitutions, so those are judged like any other command: `cat <<EOF > f\n$(git commit -m x)\nEOF` is refused on `main`, and `cat <<EOF > f\n`git push origin main`\nEOF` is refused from `main` and from `feat/x`. *(Amended at Halt 1 on the user's answer.)* A command after the heredoc is still judged: `cat <<EOF > f\nhello\nEOF\ngit commit -m x` is refused. A commit taking its message from a heredoc — `git commit -F - <<'EOF'\nfix main's guard\nEOF` — is refused as a commit to `main`, not as unreadable, and is allowed on `feat/x`. |
| A3 | Reads `#` as bash does: `# it's fine\ngit commit -m x\n# that's it` is refused; `echo ok # git commit -m x` is allowed; `echo ok#1 && git commit -m m` is still refused. |
| A4 | Joins a backslash-newline: `git \\\ncommit -m x` is refused; `git \\\npush origin main` is refused from `main` and from `feat/x`. |
| A5 | Plays safe on the rare forms: every remaining bypass from the reproduction — `echo $'it\'s'; git commit -m x # '`, the PowerShell here-string, `<# it's #>` and backtick-quote cases, and `cat <<EOF >/dev/null\nit's\nEOF\ngit commit -m x # '` — is refused on `main`. A command using one of these forms that names neither commit nor push is allowed on `main`, and all of them are allowed on `feat/x`. |
| A6 | Changes nothing else: every existing test in `tests/test_guard_git.py` passes unmodified, and a differential over a corpus — every command the existing suite passes to the guard, plus generated variations — gives the same allow/refuse decision as the guard on `main`, except where the input contains a word-start `#`, an unquoted `<<`, a backslash-newline or an unmodelled construct *and* the new decision matches how bash reads the command (or is the play-safe refusal on `main`). One accepted cost: a command that switches branch with `&&` and then commits with a `$'...'` message on `main` is now refused. |

### Open questions

None.

---

## 2. Plan

> Written in step 2, accepted by the user before step 3 starts. Concrete enough that
> step 3 is transcription, not invention.

### Approach

**Chosen — a pre-lexing pass in front of `shlex`.** A new private scanner, `_prepare`, walks
the command once, character by character, tracking quote state the way bash does (single
quotes literal, double quotes honouring `\"` and `\\`, a backslash outside quotes escaping
the next character). Outside quotes it removes what bash never executes and `shlex` cannot
read: a `#` that starts a word comments out the rest of its line (the newline stays); a
backslash-newline is deleted, joining the lines; and the body of each heredoc opened on a
line (`<<WORD`, `<<-WORD`, `<<'WORD'`, `<<"WORD"`, but not the `<<<` here-string) is dropped
from the next newline up to and including its delimiter line, while the `<<` operator and
its delimiter word stay so the invocation still reads as a redirection. The scanner also
reports whether it met a construct it does not model — `$'` outside quotes, `@'` or `@"`,
`<#`, or a backtick directly before a quote. `segments()` lexes the scanner's output with
`shlex` exactly as today, so a command with none of these constructs produces identical
tokens. `violation()` uses the flag to distrust an allow, not to stop reading: with `main`
checked out, a command carrying an unmodelled construct that names commit or push is
refused; otherwise the normal judgment runs on the parsed segments. This keeps every
refusal that holds today — including a push to `main` from another branch — and closes the
bypasses.

**Rejected.** *Make an unmodelled construct "unreadable"* (return `None` from `segments`):
simpler, but unreadable input is allowed off `main`, so `echo $'x'; git push origin main`
from `feat/x` — refused today — would become allowed; a new hole to close an old one, and an
A6 failure. *Replace `shlex` with a full hand-written bash lexer*: the cleanest long-term
shape, but it re-derives everything the 220 existing tests pin down, puts A6 at real risk,
and still could not model PowerShell. *Only distrust, never transform* (Option 3): fails A1,
and the user chose against it.

### Modules

| Path | New or changed | Purpose |
|---|---|---|
| `.claude/hooks/guard_git.py` | changed | Private `_prepare` scanner; `segments()` lexes its output; `violation()` refuses on `main` when an unmodelled construct names commit/push; new constant `UNMODELLED_OPENERS`; module docstring describes the three rules and the distrust |
| `tests/test_guard_git.py` | changed | New tests for A1–A5 appended; existing tests untouched |
| `STRUCTURE.md` | changed | The `guard_git.py` section describes the scanner's rules and the distrust; the `test_guard_git.py` section names the new cases |

### Public API

No public signature changes. Two public functions change behaviour, and one public constant
is added:

| Signature | Module | Purpose | Covers |
|---|---|---|---|
| `segments(command: str) -> list[Segment] \| None` | `guard_git.py` | Unchanged signature. Now lexes the command after heredoc bodies, word-start comments and backslash-newlines have been removed; `None` also for a heredoc whose delimiter never arrives. | A1, A2, A3, A4, A6 |
| `violation(command: str, branch: str) -> str` | `guard_git.py` | Unchanged signature. Refuses on `main` when the command carries an unmodelled construct and names commit or push, with the fixed reason in guide step 7; otherwise judges as before. | A1–A6 |
| `UNMODELLED_OPENERS: tuple[str, ...] = ("$'", "@'", '@"', "<#", "`'", '`"')` | `guard_git.py` | The character pairs that open a construct the scanner does not read: all of them outside quotes, and `` `" `` inside double quotes too, where PowerShell uses it. | A5 |

Private, for the build to write but not to list in `STRUCTURE.md`: `_prepare(command: str) ->
tuple[str | None, bool]` — the transformed text (or `None` for an unterminated heredoc) and
whether an unmodelled opener was seen.

### Implementation guide

1. **Reproduction first (fix round).** Add `test_violation_allows_a_heredoc_with_a_stray_quote_on_main`
   with the reported shape — `python3 - <<'EOF'`, body `x = '''main's push'''`, then `EOF` —
   asserting it is not refused on `main`. Run it and paste the red run into section 3. If it
   is already green, halt.
2. **Scanner skeleton.** Add `_prepare` that copies the command through unchanged while
   tracking quote state: outside, single, double; backslash escapes outside quotes and inside
   double quotes; nothing escapes inside single quotes. Return `(command, False)` for now.
   Wire `segments()` to lex `_prepare(command)[0]`, returning `None` when it is `None`.
   Existing suite must still be 220 green — this proves the pass is an identity.
3. **Backslash-newline.** Inside the scan, not as a regex pre-pass: outside single quotes, an
   *unescaped* `\` followed by `\n` is deleted with it; `\\` + newline is an escaped backslash
   and a real line break. (A `\` inside a comment is already gone with the comment, so
   `echo ok # path\` + newline + `git commit` keeps its two lines.)
4. **Comments.** Outside quotes, a `#` at the start of the string or after whitespace or one
   of `;&|()<>` and the newline starts a comment: skip to the next newline and keep that
   newline. `#` anywhere else (`ok#1`, `${#x}`, `$#`, `--grep=#12`) is an ordinary character;
   keep `lexer.commenters = ""`. The newline that ends a comment is processed as an ordinary
   unquoted newline, so heredocs queued earlier on that line start their bodies there
   (`cat <<EOF # note` + newline + body).
5. **Heredocs.** Outside quotes, `<<` not followed by a third `<` opens a heredoc: read an
   optional `-`, optional blanks, then the delimiter word with quotes and backslashes removed
   (bash's rule; `<<\EOF`, `<<'EOF'` and `<<"EOF"` all close on `EOF`). The word ends at the
   first blank or bash metacharacter (`;&|()<>` or newline); `<<` with no word after it makes
   the command unreadable (`None`). `<<<` is consumed as one unit and is not a heredoc. A `<<`
   inside quotes — including `"$(cat <<'EOF' ... EOF
)"`, the pipeline's own commit form — is
   ordinary quoted text, as today. Emit the operator and the word as written.
   *(Amended at Halt 1.)* A body after an unquoted delimiter is not simply dropped: its
   `$( … )` and backtick command substitutions are kept, each as a command of its own
   (separated by newlines, as if they stood on their own lines), and the rest of the body
   text is dropped. A body after a quoted delimiter is dropped whole. Queue the heredoc. At the next unquoted newline, for each queued heredoc
   in order, consume lines until one equals the delimiter (for `<<-`, after stripping leading
   tabs); drop them, keep one newline. If the input ends first, return `(None, flag)`.
6. **Unmodelled openers.** Outside quotes (and outside comments and heredoc bodies, which are
   skipped), set the flag on any pair in `UNMODELLED_OPENERS`; inside double quotes, set it on
   `` `" `` as well. Opener detection runs before the comment rule at the same position, so
   `<#` sets the flag even though `<` would put the `#` at word start. For `$'`, also consume
   the ANSI-C string honouring `\'` so quote tracking stays correct after it.
7. **Distrust in `violation()`.** Before the existing logic: if `branch == PROTECTED`, the
   flag is set and `RISKY_PATTERN` matches the raw command, return a refusal: "Refused: this
   command uses syntax this guard does not read — `$'...'`, a PowerShell here-string, block
   comment or backtick-escaped quote — and it names `commit` or `push` while `main` is
   checked out." plus the existing advice to branch first. Otherwise unchanged; the unreadable
   fallback keeps searching the raw command.
8. **Docs.** Rewrite the module docstring's lexing paragraph and the `STRUCTURE.md` guard
   section for the three rules and the distrust, and add the new tests to the
   `test_guard_git.py` section.

### Test intents

| # | Must prove | Covers |
|---|---|---|
| T1 | The reported heredoc command is allowed on `main` (red before the fix, green after) | A1 |
| T2 | A heredoc body is data in every delimiter form, including `<<-` with tab-indented close and a git-looking body line; a command after the heredoc is still judged; `git commit -F - <<'EOF'` with an apostrophe in the body is refused as a commit to `main` and allowed on `feat/x`; `<<<` is not a heredoc; `<<\EOF` closes on `EOF`; a heredoc on a line ending in a comment (`cat <<EOF # note`↵`it's`↵`EOF`↵`git commit -m x # '`) is refused on `main`; the `"$(cat <<'EOF' ... )"` commit form keeps today's outcome; `<<` with no word, and a heredoc whose delimiter never arrives, make `segments` return `None` | A2 |
| T3 | `#` at word start comments to end of line, so quotes in comments no longer pair across lines (the bypass is refused); `echo ok # git commit -m x` is allowed; `#` inside a word, `${#x}` and `--grep=#12` are untouched; a `#` inside quotes is untouched | A3 |
| T4 | Backslash-newline joins lines, so `git \`↵`commit` and `git \`↵`push origin main` are refused; a backslash-newline inside single quotes is kept; `\\` + newline is not a continuation | A4 |
| T5 | Each bypass from the reproduction that rests on an unmodelled construct is refused on `main` with the new reason — including the exact backtick-quote string `$x = "say `"hi"; git commit -m x # "`, a multi-line `<# a`↵`it's`↵`#>`↵`git commit -m x # '`, and both `@'` and `@"` here-strings; the same forms without commit/push are allowed on `main`; all of them are allowed on `feat/x`; a push to `main` with an unmodelled construct is still refused from `feat/x` when the push itself parses | A5 |
| T6 | Every existing test passes unmodified, and the differential agrees — run in step 6 as evidence from a scratch directory, not added to the suite, since after merge it would compare the guard with itself. **Baseline:** `git show origin/main:.claude/hooks/guard_git.py` saved as `guard_git_base.py`, imported with `.claude/hooks` on `sys.path` for `plan_state`. **Corpus:** every `(command, branch)` passed to `violation` and `segments` while the existing suite runs, recorded by a wrapper installed from a scratch conftest or plugin, plus variants of each: ` # '` appended, `# c`↵ prefixed, `\`↵ inserted between tokens, the command placed after a heredoc, and `echo $'x';` prefixed. **Branches:** `main` and `feat/x`. **Accepted difference:** as A6 states. Any other difference fails A6 | A6 |

### Risks

- **The pass is not an identity on plain commands.** Any change to tokens for a command with
  no `#`-at-word-start, backslash-newline or `<<` is a bug in the scanner. Step 2 of the guide
  checks it with the existing suite; the build fixes it without asking.
- **Arithmetic `<<`** (`$(( 1 << 2 ))`) is read as a heredoc whose delimiter never arrives, so
  `segments` returns `None`: refused on `main` only if the command names commit/push, allowed
  elsewhere. Accepted — the safe direction, and rare. Not a halt.
- **A push to `main` from another branch that is itself hidden by an unmodelled construct**
  (`echo $'it\'s'; git push origin main # '` from `feat/x`) stays allowed: the concept limits
  the distrust to `main` checked out, and the remote's protection still refuses the push. A
  step 8 item, not a halt.
- **Play-safe refusals the concept accepts.** On `main`, a command with an unmodelled
  construct that names commit or push is refused even when it would be allowed today — e.g.
  `git checkout -b feat/x && git commit -m $'a\nb'`. A6 names this cost. Not a halt.
- **PowerShell forms cannot run in a real `pwsh` here.** Evidence for them is
  `violation()`'s verdict only. Not a halt.
- **The cause is elsewhere.** If the build finds a bypass in A1–A5 that this pass cannot
  close because the cause is not in what reaches `shlex`, halt — that changes the Root cause
  row.
- **A criterion turns out wrong**, e.g. a listed bypass that bash does not actually execute:
  halt rather than drop it.

### Critique

`plan-critic` verdict: accept with changes. Every finding applied:

1. `` `" `` sits *inside* PowerShell double quotes, so an outside-quotes check missed the backtick bypass — applied: flagged inside double quotes too (`UNMODELLED_OPENERS` row, guide 6, T5).
2. A heredoc on a line ending in a comment could lose its body handling and open a bypass — applied: the comment's newline is an ordinary newline for the heredoc queue (guide 4, T2).
3. `<#` collides with the word-start comment rule — applied: opener detection runs first (guide 6, T5 multi-line form).
4. T6 underspecified and A6's exception set named inputs while the change is rules — applied: T6 specified concretely; A6 reworded to a rule-based exception set and the `$'...'` cost recorded (section 1, Risks). This is the one change to section 1, made before acceptance.
5. Missing intents — `"$(cat <<'EOF' ...)"`, `<<\EOF`, `<<<`, `\\`↵, delimiter end and missing word, `@"` — applied (guide 3 and 5, T2, T4, T5).
6. Refusal reason described two ways — applied: the fixed text in guide 7, referenced from the Public API row.

### Coverage

- Every criterion has a Public API entry: A1–A4 and A6 via `segments`/`violation`, A5 via
  `violation` and `UNMODELLED_OPENERS`.
- Every criterion has a test intent: A1→T1, A2→T2, A3→T3, A4→T4, A5→T5, A6→T6.
- Nothing in the Public API lacks a criterion: `UNMODELLED_OPENERS` exists only for A5.

---

## 3. Implementation notes

> Written in step 3. Only deviations from the plan above, each with its reason. "Built as
> planned" is a complete and good entry. On a fix round, also the reproduction test's red
> run, pasted here before the fix was written — step 6 cites it.

**Reproduction, red before the fix** (`pytest -q tests/test_guard_git.py -k stray_quote`):

```
FAILED tests/test_guard_git.py::test_violation_allows_a_heredoc_with_a_stray_quote_on_main
>       assert not refused(command, PROTECTED)
E       assert not True
E        +  where True = refused("python3 - <<'EOF'\nx = \'\'\'main's push\'\'\'\nEOF", 'main')
1 failed, 220 deselected
```

Refused on `main` as unreadable, as the Defect block's Observed row says.

Built as planned. Helpers beyond `_prepare`: `_skip_single`, `_skip_double`, `_skip_ansi`, `_heredoc_word`, `_heredoc_bodies`. A backslash-newline inside double quotes is also deleted (bash joins there too). `violation()` calls `_prepare` for the flag and `segments()` for the text. After the fix the reproduction is green and all 221 guard tests pass.

**Deviations from section 2, found in step 5** (each a case where step 3's scanner lost a refusal the step-2 guard gave, which A6 forbids unless the new decision matches bash; each checked against real bash 5.2 with `git` shadowed, probes in the build scratchpad). All fixed inside section 1:

- Section 2's Risks entry calling arithmetic `<<` "the safe direction" was wrong: off `main` an unreadable command is allowed, so `echo $((1<<2)); git push origin main` from a branch went from refused to allowed. `_prepare` now copies `$((...))` and `((...))` through untouched.
- A heredoc whose delimiter never arrives no longer makes `segments` return `None` (section 2's Public API row for `segments`): bash runs the commands before it and takes the rest as the body, so `_prepare` does too. A `<<` with no delimiter word is passed through to `shlex` as an operator, as before. `_prepare` is now `-> tuple[str, bool]`, never `None`.
- `_COMMENT_BOUNDARY` was too wide. `#` after the `)` of a `$( )`, inside `${ }`, and after `\r` is part of a word in bash; after a subshell's `)` it is a comment. `_prepare` now keeps a stack of what it is inside (`$( )`, `<( )`, subshell, `${ }`, backticks, double quotes) and `\r` is no boundary. A comment inside backticks ends at the closing backtick.
- Quotes nest in `"$( )"`, so a double-quoted string is walked by the same loop rather than skipped by `_skip_double`, which is removed. This also fixes `.replace("\\\n", "")` eating the second backslash of `"a\\<NL>"`.
- An unquoted heredoc delimiter joins backslash-newline on the closing line (`E\`+`OF` closes), a quoted one does not; and `\r` belongs to the delimiter word, so a CRLF script closes on `EOF\r` as bash does. (The input-space designer's claim that bash never closes it was wrong; the probe shows it does.)

---

## 4. Verification log

> Written in step 4: the static half. Command output, not a summary of it.

| Check | Result |
|---|---|
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `11 files already formatted` |
| `mypy` | `Success: no issues found in 11 source files` |
| `pytest` | `312 passed in 5.49s` |
| Plan completeness | `segments`, `violation` (signatures unchanged) and `UNMODELLED_OPENERS: tuple[str, ...] = ("$'", "@'", '@"', "<#", "`'", '`"')` exist as written; `_prepare(command: str) -> tuple[str | None, bool]` exists as planned. No missing, deviation or unplanned public surface. |
| `STRUCTURE.md` | in sync after the `structure-auditor` edits below |
| `python -m <package>.<module>` | not applicable: `guard_git.py` is an executable hook (its `main()` is the entry point, no showcase) and no library module was added; `template_repo` is not installed here |

`structure-auditor` findings: step 3 had already added the lexing prose (its edit 3) and a `UNMODELLED_OPENERS` row. Applied what was missing: the `violation` row's `main` refusal (1), the `segments` row's `None` cases (2), the full `UNMODELLED_OPENERS` description (4), and the `tests/test_guard_git.py` shell-lexing paragraph (5). No private names listed.

---

## 5. Test log

> Written in step 5: the dynamic half.

| Intent | Test names | Result |
|---|---|---|
| T1 | `test_violation_allows_a_heredoc_with_a_stray_quote_on_main` (step 3, unchanged) | green |
| T2 | *(after Halt 1, A2 amended)* `..._refuses_a_substitution_in_an_unquoted_body_on_main` (3), `..._refuses_a_push_to_main_in_an_unquoted_body_from_a_branch` (2), `..._names_the_commit_not_the_heredoc_for_a_body_substitution`, `..._leaves_a_quoted_delimiter_body_pure_data` (5 forms x 2 branches), `..._does_not_read_text_or_arithmetic_in_an_unquoted_body_as_a_command` (10: escaped `$(`/backticks, `$((1<<2))`, `${x}`, unclosed forms), `..._reads_an_escaped_backslash_before_a_substitution_as_live`, `..._refuses_every_body_substitution_form_bash_runs` (14: quotes as text, nesting, continuation, comment-like text, `${y:-$(..)}`, arithmetic), `..._allows_a_harmless_body_substitution_on_main` (5, `$(date)` among them), `..._still_judges_the_command_after_a_body_with_substitutions`, `..._keeps_quote_pairing_after_a_body_substitution_with_a_stray_quote`, `..._reads_a_backtick_pair_around_an_apostrophe_as_unrunnable`, `..._judges_a_substitution_in_the_second_of_two_heredocs`, `..._expands_the_rest_of_an_unterminated_unquoted_body`, `..._joins_a_continuation_before_reading_a_body_substitution`, `..._flags_unmodelled_syntax_inside_a_body_substitution`, `..._does_not_look_inside_quotes_within_a_body_substitution`, `segments` token tests for extracted commands (4); also `test_violation_reads_a_heredoc_body_as_data_in_every_delimiter_form` (6), `..._still_judges_a_command_after_a_heredoc` (8), `..._refuses_a_heredoc_fed_commit_as_a_commit_not_as_unreadable`, `..._keeps_the_pipelines_own_commit_form` (2), `..._closes_the_first_heredoc_on_the_first_delimiter`, `..._closes_a_heredoc_where_bash_does` (2), `..._gives_a_quoted_delimiter_no_line_joining`, `..._takes_the_rest_of_an_unterminated_heredoc_as_its_body`, `..._keeps_a_push_that_runs_before_an_unterminated_heredoc` (2), `..._reads_a_shift_as_arithmetic_not_as_a_heredoc` (5), `..._reads_nested_subshells_that_look_like_arithmetic`, `segments` heredoc tests (operator and word kept, five delimiter forms, `<<-` spaces, two on a line, lone `<<`, no word, never closes, unclosed quote, `<<<` twice) | green |
| T3 | `..._refuses_a_commit_hidden_by_quotes_in_comments`, `..._allows_a_word_start_comment_naming_a_commit`, `..._keeps_a_hash_inside_a_word_live`, `..._starts_a_comment_after_each_operator_and_blank` (6), `..._reads_a_hash_that_bash_keeps_in_a_word_as_text` (12), `..._comments_out_what_bash_does_after_a_closing_paren_or_redirect` (3), `..._ends_a_comment_inside_backticks_at_the_backtick`, `..._comments_inside_a_substitution_run_to_the_line_end`, `..._reads_a_hash_inside_quotes_as_text` (2), `..._distrusts_a_switch_whose_and_is_only_in_a_comment`, three `segments` comment tests, empty input (10) | green |
| T4 | `..._joins_a_backslash_newline` (4), `..._keeps_a_branch_switch_across_a_continuation`, `segments` continuation tests (single quotes, escaped backslash, in a comment, before `&&`), `..._keeps_an_escaped_backslash_before_a_newline_in_double_quotes` | green |
| T5 | `test_unmodelled_openers_is_the_documented_set`, refusal on `main` (6) and allowed off `main` (6) for every bypass, exact-branch limit (2), nothing-risky allowed (4), openers hidden by quotes, comments and bodies (5), backtick-quote in double quotes, no flag inside a body, the `&&` plus `$'` cost, pushes from a branch (3), reason text, and recorded misses (the unquoted-heredoc-body miss is gone, see Halt 1; a substitution nested in quotes inside a body substitution is pinned as the guard's existing limit instead) | green |
| T6 | Existing 220 tests unmodified and green; the differential is step 6's evidence, not a test | green (suite) |

Run: `pytest` 409 guard tests (221 before), 500 in the suite, all green; against the step-3 scanner 20 of the new tests fail, one per bug above. After Halt 1 (resolved: the user chose to read substitutions in unquoted bodies), 28 of the 57 added tests fail against the pre-halt scanner and all pass now; every behaviour was checked against real bash 5.2 with `git` shadowed, probes in the scratchpad.

Bug found after Halt 1, closed in `_heredoc_bodies`/`_prepare`: a `$( )` or backtick in an unquoted heredoc body was dropped with the body, hiding a commit or push that bash runs; `_body_substitutions` now extracts them as lines of their own.

Bugs the tests found, all fixed in `.claude/hooks/guard_git.py` (see section 3, deviations): arithmetic `<<` and an unterminated heredoc losing refusals, `#` after `$( )`/`${ }`/`\r` read as a comment, `#` inside backticks, quotes inside `"$( )"`, the escaped-backslash continuation replace, an unquoted delimiter not joining continuations, `\r` ending a delimiter word.

Edge cases considered and deliberately skipped, with reasons:

- *Resolved at Halt 1:* a substitution in an unquoted heredoc body is now judged (the first version of this list recorded it as a known miss). Remaining limits in the same area: a `case` pattern's bare `)` inside a body `$( )` ends the substitution early (the text after it is read as body, never as a command, so a miss in the safe-to-allow direction only for that contrived shape), and a substitution nested in quotes or backticks inside a body substitution is as unread as in a plain command.
- `git $'\x63ommit'` and `git co""mmit` behind an unmodelled construct: the raw-text search never sees the word `commit`. Adversarial rather than a slip; pinned as a recorded miss. **For step 8.**
- The distrust searches the raw command, comments and bodies included (plan's guide 7 chose this on purpose): the harmless `printf $'x'` beside a body that says "push" is refused on `main`. Only on `main`, only with an unmodelled construct, A6's accepted cost; pinned by a test. **For step 8** if it proves noisy.
- `((a)+(b))` as arithmetic, `case` patterns' unmatched `)` inside `$( )`, `<(` process substitution edge cases, PowerShell `` ` `` line continuations: contrived, and the failure is a conservative refusal or the unchanged old behaviour.
- A heredoc spanning a quoted newline on its opener line: rare; bash's own order is subtle.
- Numbers, `None`, wrong types, purity and idempotency: `str` in, immutable; `main()` filters non-strings; idempotency already covered.

---

## 6. Concept check

> Written in step 6, against section 1 — not against section 2. The question is whether
> the thing built is the thing agreed, not whether it matches the plan.

| # | Criterion | Met | Evidence |
|---|---|---|---|
| A1 | Reported heredoc allowed on `main` | yes | Section 3 red run (`pytest -k stray_quote` against the old module: `assert not True`, refused as unreadable); step 6 re-ran it against `origin/main`'s `guard_git.py` (fails, plus the body-substitution stray-quote test) and green against the branch: `test_violation_allows_a_heredoc_with_a_stray_quote_on_main`. Probe: allow. |
| A2 | Heredoc bodies read as bash does (as amended at Halt 1) | yes | Probed 10 shapes on the final guard, all as specified: quoted bodies (`'EOF'`, `"EOF"`, `\EOF`) allow; `<<-` tab close with apostrophe allow; unquoted `$(git commit)` refused on `main`, backtick push refused from `main` and `feat/x`; command after heredoc refused; `git commit -F - <<'EOF'` refused on `main`, allowed on `feat/x`. Suite: heredoc tests in section 5 (T2). |
| A3 | `#` read as bash does | yes | `# it's fine`/commit/`# that's it` refused; `echo ok # git commit -m x` allowed; `echo ok#1 && git commit -m m` refused. Tests: T3 group. |
| A4 | Backslash-newline joined | yes | `git \`NL`commit` refused; `git \`NL`push origin main` refused from `main` and `feat/x`. Tests: T4 group. |
| A5 | Rare forms play safe | yes | `$'...'`, `@'` here-string, `<# #>`, backtick-quote and unquoted-heredoc-body bypasses all refused on `main`; `echo $'x'; ls` allowed on `main`; the `$'` bypass allowed on `feat/x`. Tests: T5 group, `test_unmodelled_openers_is_the_documented_set`. PowerShell forms judged by `violation()` only (no `pwsh`). |
| A6 | Nothing else changes | yes | (1) `git diff origin/main -- tests/test_guard_git.py` has 804 insertions and no removed line, so the 220 original tests are untouched; the original file also passes 219/220 when run from a scratch dir (the one failure is a relative-path lookup of `settings.json`, an artefact of running from there), and the full suite is 500 green with ruff, format and mypy clean. (2) T6 differential below. |

**T6 differential** (scratchpad `diff/driver.py`; baseline `git show origin/main:.claude/hooks/guard_git.py` saved as `guard_git_base.py`, byte-identical to origin/main, loaded with `.claude/hooks` on `sys.path` and registered in `sys.modules` before exec). Corpus: 274 `(command, branch)` pairs recorded from the original 220-test suite by a scratch pytest plugin (`-p rec_plugin`, nothing in the tree), 139 distinct commands. Variants per command: ` # '` appended, `# c`NL prefixed, `\`NL after the first space and after every space, placed after `cat <<EOF >/dev/null`/`hello`/`EOF`, and `echo $'x'; ` prefixed. 962 distinct inputs, each on `main` and `feat/x`: 1924 decisions compared, 1649 identical, 275 differ. **Every unmodified corpus command (variant `orig`) has the same decision on both guards.** All 275 differences contain a word-start `#`, a backslash-newline, an unquoted `<<` or an unmodelled opener (none without). Directions: 178 old allow to new refuse on `main`, 72 old allow to new refuse on `feat/x`, 25 old refuse to new allow on `main`. Each was accepted by one of: bash with `git` shadowed (stubbed `PATH`, a function that logs the branch and follows `checkout -b`/`switch -c`) shows the new decision is what bash does (198); the new decision equals the old guard's on the same command with the construct stripped by hand (68; mostly PowerShell shapes or `GIT`/`/usr/bin/GIT` spellings that the bash oracle cannot run); or the `main` play-safe refusal for an unmodelled opener (9). **Unaccepted differences: 0.** The comparison of `segments` tokens differs on 652 of the variants, all containing a trigger, none without. The accepted `&&` plus `$'...'` cost is among the 9 play-safe refusals.

Drift found, and what was done about it: none. Out of scope held (`bash -c "git commit -m x"` is still allowed, as before; no dialect switch; `$'`/PowerShell forms play safe rather than being read). Surface: only `UNMODELLED_OPENERS` added, as planned and documented. Fix-round check: the Root cause row (raw text handed to `shlex`) is addressed at its cause, a pass in front of `shlex` for the constructs it does not model, not at the symptom site; the class listed in the Defect block has a test per member. `structure-auditor`'s report was against the stale session-start copy; STRUCTURE.md on disk already carries the lexing paragraph, the `UNMODELLED_OPENERS` row, updated `segments`/`violation` rows and the shell-lexing test bullets, so no edit was needed. Known misses recorded in section 5 stay for step 8 (hex-escaped or split-quote subcommand spellings behind an unmodelled opener, a push to `main` from another branch hidden by an unmodelled construct).

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
| Commits | `6be7fa6 Concept: the git guard reads commands the way the shell does`<br>`c193a1c Plan: the git guard reads commands the way the shell does`<br>`ff44a7e Plan: apply plan-critic findings`<br>`f7f9561 Plan accepted: open the build`<br>`daf507a WIP step 3: reproduction, red`<br>`81dfdf6 Read heredocs, comments and continuations in the git guard`<br>`d68874a Document the guard's shell-lexing pass`<br>`3e6fe08 Verify: The git guard reads commands the way the shell does`<br>`52fea83 WIP step 5: scanner tracks nesting, arithmetic shifts, CR, unterminated heredocs`<br>`58ced54 WIP step 5: shell-lexing edge-case suite`<br>`2780408 Test: The git guard reads commands the way the shell does`<br>`d161806 Halt at step 5: unquoted heredoc bodies run substitutions`<br>`ba32914 Halt at step 5: resume from step 5`<br>`a86adba Halt answered at step 5: judge substitutions in unquoted heredoc bodies`<br>`8cd15d2 WIP step 5: judge substitutions in unquoted heredoc bodies`<br>`ee64452 Test: The git guard reads commands the way the shell does`<br>`a6b8957 Concept check: The git guard reads commands the way the shell does`<br>(plus the `Ship:` commit closing the round) |
| Pushed to | `origin/fix/guard-git-shell-lexing`; origin/main already merged in, whole tree green (ruff, format, mypy clean; 500 passed); diff review found only the four expected files, no strays or debug output; every step 1-6 left a commit |

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

### Halt 1 — after step 5, raised by the orchestrator

**Step:** 5 finished (`STATUS: done`); the orchestrator halted before step 6 under halting
rule 1, a criterion that turns out to be wrong.

**Reason:** step 5 recorded as a known miss that "a `$(git commit)` in an unquoted heredoc
body is data to the guard, though bash runs it", judging it within A2. The orchestrator
checked it against the guard on `origin/main` and real bash (git shadowed by an echo
function):

| Command | Branch | Guard on `main` | New guard | Bash |
|---|---|---|---|---|
| `cat <<EOF > f` / `$(git commit -m x)` / `EOF` | `main` | refuse | **allow** | runs `git commit -m x` |
| `cat <<EOF > f` / `` `git push origin main` `` / `EOF` | `main` | refuse | **allow** | runs `git push origin main` |
| same | `feat/x` | refuse | **allow** | runs `git push origin main` |
| `cat <<'EOF' > f` / `$(git commit -m x)` / `EOF` | `main` | refuse | allow | runs nothing |

In a heredoc whose delimiter is unquoted, bash expands `$( )` and backtick command
substitutions in the body, so the body is not pure data. A2 says bodies after `<<EOF`,
`<<'EOF'` and `<<"EOF"` "all count as data", which is right only for a quoted delimiter. As
built, the fix opens a commit-to-`main` bypass the old guard refused, which also fails A6.

**Question for the user:** how should an unquoted heredoc body (`<<EOF`) be read?

**Answer (2026-10-03):** (a) — "If you think a is the best option and reliable please use this one." A2 is amended in section 1 to say so; section 2's guide step 5 follows below. The build resumes at step 5, which implements the change and its tests.

- **(a) Read the commands inside it** *(recommended)*: text in an unquoted body stays data,
  but any `$( … )` or backtick command inside it is judged like any other command, as bash
  runs it. A quoted body (`<<'EOF'`, `<<"EOF"`) stays pure data. A2 is amended to say so.
- **(b) Play safe**: an unquoted body containing `$(` or a backtick counts as unmodelled
  syntax, refused on `main` when the command names commit or push. Simpler, but a push to
  `main` hidden that way from another branch would stay allowed where today it is refused.
