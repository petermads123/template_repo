# The git guard never takes a quoted word for an operator

<!-- claude-plan step=5 status=active -->

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
| 2 | Plan | `/plan` | with the user | done |
| 3 | Implement | `/implement` | in `/build` | done |
| 4 | Verify | `/verify` | in `/build` | done |
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
| Class | (1) A quoted or escaped token made only of operator characters: `;`, `&&`, `&`, `\|`, `\|\|`, `(`, `)`, `{`, `}`, a quoted newline, concatenations like `";"";"` and `a';'`. Several are refused today only by which operator they become (`')'`, `'}'`, `'\|'`, `\|\|`, `a';'`, `{}`, `{ }`, `-exec true {} +`), so the criterion holds on `segments` as well as on `violation`. (2) A bare `{`/`}` in argument position, and any token made only of braces (`}}`, `{}`). (2b) An operator character inside an unquoted `${…}` (`${x:-;}`), which both shells read as one word (added at step 2). (3) `\r` before a newline after an operator. (4) Over-refusals of the same family (bash runs no git): a quoted word at command position read as a leader, an assignment or a redirection — `'if' git commit -m x` (round 3 pinned it), `'!' git checkout -b x && git commit -m x`, `"X=1" git commit -m x`, `'>' x git commit -m x` — and `echo ";" git commit -m x`, `git checkout feat/y ";" git commit -m x`. **Shell constraint:** the guard runs for the PowerShell tool too and reads both shells the same way (module docstring, `main()` never reads `tool_name`). Single and double quotes make a string in both shells, so a quoted token is never an operator in either. But `\` is not an escape in PowerShell (`echo \; git commit` runs the commit there), a bare `{` after a command word is a scriptblock that runs (`ForEach-Object { git commit -m x }`, `Invoke-Command -ScriptBlock { … }`, `Start-Job { … }`, refused today only because `{` splits), and `\r` is a line terminator there (`&&\r\n` is a real `&&` in PowerShell 7). |
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
| A2 | A quoted token is never an operator: `segments('echo ";" x')` returns one invocation (`echo`, `;`, `x`), and the same holds for `"&&"`, `'&'`, `'\|'`, `'\|\|'`, `'('`, `')'`, `'{'`, `'}'`, a quoted newline, `";"";"` and `a';'`; every `\|\|`- and `!`-form built on one (the Reproduction row's quoted forms, `! true \| echo ';' \| …`) is refused on `main`. The same holds inside an unquoted `${…}`, which both shells read as one word: `true \|\| echo ${x:-;} \| git checkout -b x && git commit -m x` is refused on `main` (added at step 2, the user's choice). |
| A3 | The shell-dependent tokens play safe: the forms with `\;`, `\&`, `-exec true \;`, and a bare `{` or `}` argument (`true \|\| echo { \| …`, `{ true \|\| echo } \| …; }`) are refused on `main`, and `Get-Item . \| ForEach-Object { git commit -m x }`, `Invoke-Command -ScriptBlock { git commit -m x }` and `Start-Job { git push origin main }` stay refused on `main`. |
| A4 | `git checkout -b feat/x &&\r\ngit commit -m x`, `&&\r\n\r\n` and `&& \r\n` are refused on `main`; `tests/test_guard_git.py:2429` changes from allowed to refused (agreed with this concept); `git commit\r\n`, `git push\r\n` and `git push origin main\r\n` stay refused. |
| A5 | A quoted word at command position is not shell syntax: `'if' git commit -m x`, `'!' git commit -m x`, `"!" git commit -m x`, `"X=1" git commit -m x`, `'>' x git commit -m x` and `echo ";" git commit -m x` are allowed on `main` (round 3's quoted-leader pins for `'if'` and `"!"` change to allowed, agreed with this concept; its `\!`, `x=1 if`, `>/dev/null !` and `sudo -n !` pins stay refused); `'!' git checkout -b x && git commit -m x` stays refused, an over-refusal recorded on purpose (bash is safe there only because a command named `!` fails, which the guard does not model — changed at step 2, the user's choice); `"git" commit -m x` stays refused. |
| A6 | Nothing else changed: the existing tests pass unmodified except the changes A4 and A5 name, and rounds 1–4's criteria still hold; a differential against the guard at 8972524 over the suite's commands with quoted, escaped, bare-brace and carriage-return variants sends every differing row to bash with `git` shadowed — the oracle first shown live by a plain commit landing on `main` — and every difference involves one of those tokens, with the oracle agreeing or the new refusal play-safe, and zero rows where the new guard allows a commit or push that bash lands on `main`. |

### Open questions

None.

---

## 2. Plan

### Approach

**Chosen: the pre-pass, which already knows what is quoted, writes that knowledge into the
text it hands to `shlex`, using private stand-in characters; `_segments` reads them and maps
them back.**

`shlex` cannot be told what was quoted, but `_scan` (the pre-pass) already walks every quote,
escape and substitution frame. So `_scan` changes what it emits, in three ways:

1. **A quoted operator character becomes a word character.** Inside single or double quotes
   (the innermost frame is a quote, not a `$( )` inside one), each of `; & | ( ) { } < >` and
   newline is written as its own private stand-in (`_QUOTED`, a fixed map into the Unicode
   private-use area). `shlex` keeps it inside the word, `_is_separator` never sees an operator,
   and `_segments` maps each stand-in back to its character when it builds the tokens. So
   `echo ";" x` is one invocation `echo ; x`, and no quoted text ever reaches a run.
2. **A token that begins with a quote carries a marker.** `_scan` writes `_QUOTE_MARK` just
   before the opening quote of a word that starts with one. The marker survives into the
   tokens `_segments` returns to `_judge`, and it is what stops `'if'`, `'!'`, `"X=1"` and `'>'`
   from being read as a leader, an assignment or a redirection, because those checks compare
   the token as it is. Everything that reads a token's *text* — the command name, wrappers,
   the subcommand and its arguments, switch targets, refs — strips it first, so `"git" commit`
   is still git and `git checkout "main"` is still a switch to `main`.
3. **The three shell-dependent tokens become a soft separator.** An unquoted backslash
   before an operator character (`\;`, `\&`, `\|`, `\(`, `\{`…), and an unquoted carriage
   return, are each written as `_SOFT`, a private character added to `PUNCTUATION_CHARS` and
   `SEPARATOR_CHARS`. It still splits the command — bash would read a word there and
   PowerShell a separator, so splitting keeps PowerShell's reading — but `_governs` reads it
   as `;`, never `&&`, so nothing across it is trusted, and `_OPERATORS` does not match it,
   so it never ends an `||` operand or a `!` scope and never changes a group level. A token
   made only of braces is treated as `_SOFT` by `_segments` too, unless it is exactly `{` or `}`
   at command position — the invocation being built is empty or holds only unmarked
   `_COMMAND_LEADERS` words (so bash's `then {`, `do {`, `! {`, `coproc {`, `time {` and
   PowerShell's `do {` stay real groups). So `ForEach-Object { git commit -m x }` still splits
   and stays refused while `true || echo { | …` and `echo }}` no longer shift the group level.

This removes cause (1) at `_lex`/`_is_separator` — the knowledge `shlex` throws away is
written into the text before `shlex` runs — and cause (2) by making `\r` a separator that is
never trusted, instead of whitespace.

**Rejected:**
- **A hand-written tokenizer in place of `shlex`.** It would carry quoting cleanly, but
  replaces the lexing rounds 1–4 verified with new code that would itself need verifying,
  and still has to get the flags through the public `Segment`.
- **Reading the payload's `tool_name`** and applying each shell's exact rules. The user chose
  both-shell-safe.
- **A quoted flag on the public `Segment`.** Changes the public dataclass and every test that
  pins segment tuples.

### Modules

| Path | New or changed | Purpose |
|---|---|---|
| `.claude/hooks/guard_git.py` | changed | Private stand-ins and their blanking; `_scan` emits them; `PUNCTUATION_CHARS`, `SEPARATOR_CHARS`, `INLINE_WHITESPACE`, `_governs` and `_segments` read them; a private `_plain` that strips them for every text comparison; module docstring |
| `tests/test_guard_git.py` | changed | New tests for A1–A6 under a round 5 heading; the existing tests A4 and A5 name changed to their agreed outcome, nothing else touched |
| `STRUCTURE.md` | changed | Guard section prose (quoting kept, soft separators, the known-miss line for quoted operators removed); tests entry gains the round 5 paragraph |

### Public API

No public signature or constant changes. `PUNCTUATION_CHARS` and `SEPARATOR_CHARS` gain one
private character each but keep their names and types; `INLINE_WHITESPACE` loses `\r`.

| Signature | Module | Purpose | Covers |
|---|---|---|---|
| `segments(command: str) -> list[Segment] \| None` | `guard_git.py` | Unchanged signature. A quoted operator character stays in its word; a soft separator splits and shows as `;`; stand-ins and the quote marker never appear in its output. | A2, A6 |
| `git_subcommand(tokens: tuple[str, ...]) -> tuple[str, tuple[str, ...]]` | `guard_git.py` | Unchanged signature. A token carrying the quote marker is never a leader, assignment or redirection; the name, subcommand and arguments come back without it. | A5 |
| `violation(command: str, branch: str) -> str` | `guard_git.py` | Unchanged signature. Refuses the quoted, escaped, bare-brace and carriage-return forms; allows quoted words at command position. | A1–A6 |

### Implementation guide

1. **Reproduction first (fix round).** Add `test_violation_refuses_an_or_switch_after_a_quoted_separator_word`
   asserting `violation('true || echo ";" | git checkout -b x && git commit -m x', "main")`
   starts with the commit reason, under a new heading "round 5: quoted words are never
   operators" at the end of the file. Run it red, paste the run into section 3, commit before
   any production change. If it is already green, halt.
2. **Stand-ins.** Add, beside `_OPEN`/`_CLOSE`/`_PLACEHOLDER`: `_QUOTED` (a dict from each of
   `; & | ( ) { } < >` and `\n` to its own private-use character, e.g. U+E001–U+E00A), its
   inverse, `_QUOTE_MARK` (U+E000) and `_SOFT` (U+E00B). `_prepare` blanks every one of them
   in the input exactly as it blanks `_OPEN`, `_CLOSE` and `_PLACEHOLDER`, so a command cannot
   forge them. Add `_SOFT` to `PUNCTUATION_CHARS` and `SEPARATOR_CHARS`; remove `\r` from
   `INLINE_WHITESPACE`.
3. **`_scan` emits them.** Two copy sites carry quoted text and both map `_QUOTED` over what
   they copy: the single-quote slice (`command[index:end]` around `:1139–1142`, contents only,
   which also covers single quotes inside recursive scans of `"$( )"`) and the per-character
   copy inside a double-quote frame (around `:1131`). The same mapping applies to characters
   copied inside an unquoted `${…}` (the `brace` frame, around `:1216–1225`); a `$( )` inside
   any of these is code and is extracted as today. A heredoc opener's quoted word (`<<";"`,
   around `:1164`) is mapped too. Write `_QUOTE_MARK` before an opening quote when `_scan`'s own
   state says a word starts there — `word == "" and plain` before the word-end pre-check
   (`:1021–1029`) updates it, outside the dq and brace frames — rather than by looking at the
   previous emitted character. Where it copies an
   unquoted backslash pair whose second character is an operator character, write `_SOFT`
   instead of the pair. Where it copies an unquoted `\r`, write `_SOFT`. Substitution text that
   `_scan` extracts and re-scans gets the same treatment, since it goes through `_scan`.
   Heredoc bodies are dropped before this and are unaffected; a heredoc delimiter line
   followed by `\r` keeps closing as today (`_DELIMITER_END` already excludes `\r`).
4. **`_governs`.** Any piece containing `_SOFT` governs as `;`, with or without `&&` in it —
   `shlex` lexes `&&\r\n` as the one piece `&&<SOFT>\n`, so this is what keeps it from being
   trusted. `raw` still records the `&&` and the newline through `_OPERATORS`.
5. **`_segments`.** After classification, map `_QUOTED` stand-ins back to their characters in
   every token. A token made only of `{` and `}` is handled as `_SOFT` (splits, governs as `;`,
   adds nothing to `raw`) unless it is exactly `{` or `}` and `current` is empty or holds only
   unmarked `_COMMAND_LEADERS` words; that one is a real group as today. `_SOFT` adds nothing to
   `raw` (`_OPERATORS` does not match it). Keep `_QUOTE_MARK` in the tokens.
6. **`_plain(token) -> str`.** A private helper that removes `_QUOTE_MARK`. `segments` applies
   it with the placeholder mapping, so the public output never shows the marker. In
   `_walk_prefix`, the leader, assignment, redirection and fd checks compare the raw token only
   before the first wrapper; the wrapper and executable checks, and after a wrapper the option
   skip and the assignment check (`env "X=1"` is `env`'s own argument), compare `_plain(token)`.
   `git_subcommand` maps `_plain` over `tokens[start:]` before walking git's own options, so
   `git "--no-pager" commit` and `git "-c" a=b commit` still find `commit`, and returns the
   subcommand and arguments marker-free; `_redirected` does the same. Any other place that compares a token's text to
   a name (`_loop_ranges`' loop words, `_leads_uncertainly`, `_redirected`, `switch_target`'s
   callers) reads it through `_plain` unless it is checking shell syntax, in which case a
   quoted token is correctly not that syntax.
7. **Docs.** Module docstring and STRUCTURE.md's guard section: quoting is kept for operator
   characters and leading quotes; the soft separator and the three tokens it covers; the
   known-miss line for quoted operators is removed; "reads both the same way" stays true and
   says the shell-dependent tokens are read so as to be safe in both. The tests entry gets a
   round 5 paragraph.

### Test intents

| # | Must prove | Covers |
|---|---|---|
| T1 | `true \|\| echo ";" \| git checkout -b x && git commit -m x` on `main` refused with the commit reason: red before, green after | A1 |
| T2 | `segments` keeps each quoted operator token in its word (`";"`, `"&&"`, `'&'`, `'\|'`, `'\|\|'`, `'('`, `')'`, `'{'`, `'}'`, a quoted newline, `";"";"`, `a';'`, and a quoted `;` inside `"$( )"` that is code, not quoted, still splitting; a `;` inside an unquoted `${x:-;}` kept in its word); every `\|\|`/`!` form from the Reproduction row built on a quoted token refused on `main`, each checked in bash | A2 |
| T3 | `\;`, `\&`, `\|`, `-exec true \;` and a bare `{`/`}` argument forms refused on `main`; `ForEach-Object { git commit -m x }`, `Invoke-Command -ScriptBlock { git commit -m x }`, `Start-Job { git push origin main }` and `{ git commit -m x; }` refused on `main`; a soft separator never carries `&&` trust (`git checkout -b x \; && git commit -m x` refused on `main`); brace-only tokens (`{ true || echo }} | git checkout -b x && git commit -m x; }`, `echo {}`) soft; real groups after a leader (`then {`, `do {`, `! {`) and PowerShell's `do { … } while ($x)` loop tests (`:3287`, `:3301`, `:3302`) unchanged | A3 |
| T4 | `&&\r\n`, `&&\r\n\r\n`, `&& \r\n` forms refused on `main`; the test at `:2429` rewritten to refused; `git commit\r\n`, `git push\r\n`, `git push origin main\r\n` refused; the CR heredoc tests (`:971`, `:2056–2073`) keep their outcomes | A4 |
| T5 | `'if' git commit -m x`, `'!' git commit -m x`, `"!" git commit -m x`, `"X=1" git commit -m x`, `'>' x git commit -m x`, `echo ";" git commit -m x` allowed on `main` (round 3's `'if'` and `"!"` pins at `:3182–3187` rewritten to allowed, the others kept); `'!' git checkout -b x && git commit -m x` pinned refused; `"git" commit -m x`, `git "commit" -m x`, `"sudo" git commit -m x`, `git "--no-pager" commit -m x`, `git "-c" a=b commit -m x`, `sudo "-E" git commit -m x`, `time "-p" git commit -m x`, `env "X=1" git commit -m x`, `git checkout "main"; git commit -m x` from a branch refused; forged stand-ins and markers in the input blanked; `git_subcommand` returns marker-free text | A5 |
| T6 | See below. | A6 |

T6 in full. The existing suite passes unmodified except the tests A4 and A5 name — `:2429`, and round
3's `'if'` and `"!"` rows at `:3182–3187` — which step 3 or 5 rewrites with a one-line note each
in section 5; rounds 1–4's criteria are re-checked. The
differential runs at step 6:
- **Baseline.** `git show 8972524:.claude/hooks/guard_git.py`, loaded from the scratchpad with
  `.claude/hooks` on `sys.path` and registered in `sys.modules`.
- **Corpus.** Every `(command, branch)` the suite passes to `violation`, captured with a scratch
  `-p` plugin.
- **Variants.** Each command with a quoted-operator argument inserted after its first word
  (`";"`, `"&&"`, `'('`, `'{'`), an escaped one (`\;`), a bare `{`, a `${x:-;}`, and each newline replaced by
  `\r\n`; prefixes `true || echo ";" | ` and `! true | echo ';' | `; branches `main` and `feat/x`.
- **What goes to bash.** Differing rows only, oracle as in round 4 (`git` shadowed with HEAD in a
  file, an empty checkout argument failing, `PATH=/usr/bin:/bin`, wrappers shadowed, stdin
  closed, a timeout, no hostile nesting), **shown live first** by `git commit -m x` landing on
  `main`. PowerShell-only rows are listed, not run.
- **Pass condition.** Every difference involves a quoted, escaped, bare-brace or carriage-return
  token; the oracle agrees or the new refusal is play-safe; zero rows where the new guard allows a
  commit or push that bash lands on `main`.

### Risks

- **A stand-in leaks into a comparison.** If a test shows a quoted name or ref mis-compared
  (`git checkout "main"` not seen as `main`), route that comparison through `_plain`: inside the
  build.
- **The pre-pass cannot tell a word-starting quote cheaply** in some frame. Then write the marker
  for every opening quote; a mid-word marker only affects the three syntax checks, which a
  mid-word quote already fails in bash. Inside the build.
- **An existing test other than those A4 and A5 name changes outcome.** Halt.
- **PowerShell.** Backtick escapes, here-strings and `$'…'` already play safe through
  `UNMODELLED_OPENERS`; if a PowerShell test changes outcome, halt.
- **The cause is elsewhere.** If an A1–A4 form stays allowed after the stand-ins are in place for
  a reason other than these two causes, halt.

### Revised at step 5: read the command both ways

Step 5's test designers found that the soft separator of approach item 3 still lets bash land a
commit on `main`, each confirmed in bash 5.2 with `git` shadowed:

- a switch right after a soft split is trusted although in bash it is an argument:
  `echo a\;git checkout -b x && git commit -m x` and `echo x\r git checkout -b x && git commit -m x`
  (both refused at 8972524, so regressions), `echo \; git checkout …`, `echo { git checkout …`,
  `echo } git checkout …`;
- a soft split cuts one git command in two: `git -c user.name=a\;b commit -m x`,
  `git push -o x\; origin main` from a branch;
- a brace after a soft split, or after `coproc NAME`, `time -p` or `function NAME`, is read
  wrongly as a group or a word (`{ true || echo \; } | …`, `true || coproc C { true; } | …`,
  `! time -p { true; } | …`);
- operator characters inside `${…}` other than `; & | { } < >` (`)`, `(`, a newline) still reach
  `shlex` raw.

The user chose to replace the soft separator with **two readings** (section 1 unchanged — its
criteria and the both-shell-safe scope hold, more exactly). `_prepare`/`_scan` produce the text
twice for the three shell-dependent tokens, and `violation` judges both and returns a refusal if
either refuses:

- **Bash reading.** A backslash-escaped operator character is a literal word character (its
  `_QUOTED` stand-in); an unquoted `\r` is a word character (bash runs `$'\r'` as a word, so
  `&&\r\n` puts a failing command between the `&&` and the newline, and the commit after it is
  read across a newline); a brace-only token is a real group only where bash reads a reserved
  word — the first word of a command, after the leaders, after `time` and its options, after
  `coproc NAME`, or after `function NAME` / `NAME()` — and a word otherwise.
- **PowerShell reading.** A backslash is an ordinary character and the operator after it is
  real (`\;` is the word `\` then `;`); an unquoted `\r` is a line break; a bare `{`/`}` after a
  command word opens or closes a scriptblock, which splits as a group does today.
- Quoted text (single, double, inside `${…}` — every `_QUOTED` character including `(`, `)` and
  a newline) is a word in both readings, as already built; the quote marker and `_plain` are
  unchanged.
- `_SOFT` is removed. `segments` (public) returns the bash reading; nothing private leaks into
  it. The budget give-up path applies the same stand-ins to quoted text before it gives up, or
  plays safe as today.

Guide changes: guide 3's escape and `\r` handling and guide 4–5's soft rules are replaced by the
two readings above; `violation` runs `_judge` per reading and returns the first refusal (commit,
push, unresolved order kept within each reading, bash reading first). T3 and T4 keep their
intents; T2 gains the `${x:-)}`, `${x:-(}` and `${x:-a\nb}` rows; T3 gains every row above; T5 is
unchanged. The designers' reports are at the scratchpad path named in the step 3 brief.

### Coverage

- **Every criterion has a Public API entry:** A1–A6 through `violation`, A2 and A6 through
  `segments`, A5 through `git_subcommand`.
- **Every criterion has a test intent:** A1→T1, A2→T2, A3→T3, A4→T4, A5→T5, A6→T6.
- **Nothing in the Public API lacks a criterion.** No new public surface.

Re-checked after the critique: the Public API is unchanged; A2 and A5 changed at the user's
choice and T2, T3, T5 and T6 changed with them, all still covered.

### Critique

`plan-critic` verdict: accept with changes. Every finding applied:

1. **`'!' git checkout -b x && git commit -m x` cannot be allowed: bash is safe only because a
   command named `!` fails.** Put to the user, who chose to change A5: `'!' git commit -m x` and
   `"!" git commit -m x` allowed, the `&&` form pinned refused; the round 3 rows that change are
   named in T5 and T6.
2. **The bare-brace rule broke PowerShell's `do {` loop and bash's `then {`.** Applied: a brace
   is real when the invocation is empty or holds only unmarked leaders (approach, guide 5, T3).
3. **The quote marker stopped option and wrapper walks (`git "--no-pager" commit`,
   `sudo "-E" git`, `env "X=1" git`).** Applied: raw checks only before the first wrapper,
   `_plain` over git's options and in `_redirected` (guide 6, T5).
4. **`&&\r\n` lexes as one piece that still governed as `&&`.** Applied: any piece holding
   `_SOFT` governs as `;` (guide 4).
5. **Single-quoted text is copied as a slice, not per character.** Applied: guide 3 names the
   copy sites.
6. **Brace-only tokens such as `}}` stayed real separators.** Applied: any brace-only token is
   soft unless it is an exact brace at command position (guide 5, T3).
7. **`${…}` hides the same defect.** Put to the user, who chose to include it: A2 and the Class
   row, guide 3, T2, T6.
8. **Finding a word-starting quote from the previous emitted character is fragile.** Applied:
   guide 3 uses `_scan`'s own `word`/`plain` state.
9. **Leftover template text in Builds on.** Applied: removed.

---

## 3. Implementation notes

> Written in step 3. Only deviations from the plan above, each with its reason. "Built as
> planned" is a complete and good entry. On a fix round, also the reproduction test's red
> run, pasted here before the fix was written — step 6 cites it.

### Reproduction, red (before any production change)

`.venv/bin/pytest -q tests/test_guard_git.py -k test_violation_refuses_an_or_switch_after_a_quoted_separator_word`

```
>       assert reason.startswith(COMMIT_REASON)
E       AssertionError: assert False
E        +  where False = <built-in method startswith of str object at 0xa314a0>('Refused: this would commit to `main`')
E        +    where <built-in method startswith of str object at 0xa314a0> = ''.startswith

tests/test_guard_git.py:3884: AssertionError
FAILED tests/test_guard_git.py::test_violation_refuses_an_or_switch_after_a_quoted_separator_word
====================== 1 failed, 1070 deselected in 0.52s ======================
```

`violation(...)` returned `""` (allowed), as the Defect block's Observed row says.

### Deviations from the plan

Built as planned, with these small departures:

- **Brace leaders compare in lower case.** Guide 5 says a lone `{`/`}` is a real group when the
  invocation holds only unmarked `_COMMAND_LEADERS` words. PowerShell spells `Do { } While` in any
  case and two existing tests (`DO {`, `Do {`) failed with a case-sensitive test, so the check lower-cases
  the word (`word.lower() in _COMMAND_LEADERS`); a quoted word still carries its mark and never matches.
- **Backslash escapes in a heredoc delimiter word and in an unquoted `${ }`** become the operator's
  stand-in (a word character), not `_SOFT`: `_SOFT` is punctuation to `shlex` and would split the word
  (and `<<` + `_SOFT` would swallow the command name after it as a redirection target).
- **`_scan` calls `fresh()` after an unquoted `\r`**, so a substitution written after a carriage return
  lands in front of the invocation it belongs to.
- **`_prepare`'s give-up path** (`command, True`) now also turns `\r` into `_SOFT`, since `\r` is no
  longer whitespace and a raw `commit\r` would otherwise stop reading as `commit`.
- **`_quoted_done`** strips the quote mark and excludes `_SOFT` when it splits words, to keep its meaning.
- **A piece holding `_SOFT` governs as `;`** even when it is only `\r\n` (formerly `\n`), so
  `segments` shows `;` for a CRLF line break; no existing test pins the old value.

Existing tests rewritten (the three A4/A5 name, one line each):

- `test_violation_carries_and_trust_into_and_through_a_substitution`: the `&&\r\n` row (was `:2429`)
  removed from the allowed list; now `test_violation_refuses_a_commit_after_an_and_and_carriage_return`.
- `test_violation_pins_a_quoted_or_misplaced_leader_as_an_over_refusal`: the `'if'` and `"!"` rows removed;
  now `test_violation_allows_a_quoted_leader_on_main`.

After the fix the reproduction is green; the suite is 1162 passed (1161 before, plus the reproduction, the two
replacement tests (four new cases), minus the three rows moved out of parametrized lists).

### Redo after step 5: the two readings (replaces the soft separator)

Step 5 sent the build back with the user's design revision (section 2, "Revised at step 5").
The reproduction test stayed as written and stayed green (the red run above is still the red
run). Built as the revision says, with these notes; the first run's deviations above that
concern `_SOFT` (2, 3, 4, 6 of that list: the escapes, the `\r` handling and the `;` shown for a
CRLF break) are superseded and no longer describe the code.

- **`_SOFT`, `_SOFT_ESCAPED` removed**, and with them `_SOFT` in `PUNCTUATION_CHARS`,
  `SEPARATOR_CHARS`, `_PRIVATE`, `_governs` and `_quoted_done`. `_ESCAPED_OPERATORS`
  (`;&|(){}<>`) replaces them. `INLINE_WHITESPACE` stays `" \t"` and `_WORD_ENDS` loses `\r`
  (the PowerShell walk adds it back).
- **`_prepare(command, powershell=False)`**, `_scan`, `_body_substitutions`, `_segments` and
  `_judge` take a defaulted `powershell` flag (all private). Bash reading: a backslash before
  `;&|(){}<>` is the operator's `_QUOTED` stand-in; an unquoted `\r` is copied as a word
  character (no new command, no comment boundary). PowerShell reading: such a backslash is written
  as an escaped backslash (`\\`, one literal character for `shlex`) and the operator is then read
  as any other; `\r` becomes a newline and starts a new command slot. The give-up path returns the
  command unchanged for bash and with `\r` as `\n` for PowerShell.
- **`${…}` maps every `_QUOTED` character** except the closing `}` (`; & | ( ) { } < >` and the
  newline), by one branch ahead of the `(`, `)`, newline and `<<` branches.
- **`_group_position(words)`** (private): the bash brace rule. A brace-only token is a word in
  `_segments`' bash reading unless it is exactly `{` or `}` at a reserved-word position: nothing
  before it, after `_COMMAND_LEADERS` (case-sensitive; a quoted word carries the mark and matches
  nothing), after `time` and its `-` options, after `coproc NAME` (any one word) and after
  `function NAME`. `coproc echo {` is therefore read as a group, though bash reads `{` there as
  an argument; checked in bash, the guard still refuses every `||` form built on it. The
  PowerShell reading keeps every brace-only token a delimiter, as before the round.
- **`violation`** returns `_judge(command, branch) or _judge(command, branch, powershell=True)`,
  inside the one `try`; each reading keeps the old order of reasons. The `_judge` comment that
  called quoted operators a known miss, the module docstring's "(a soft separator, below)" and its
  `#`-after-CR sentence, and STRUCTURE.md's soft-separator paragraph are rewritten.
- **No existing test changed outcome** beyond the two A4/A5 rewrites of the first run; 1162 passed
  unchanged before any new test (step 5 writes those).

Sanity check against bash 5.2 with `git` shadowed (HEAD in a file, empty checkout argument fails,
`PATH=/usr/bin:/bin`, stdin closed, timeout 5), shown live first by `git commit -m x` printing
`COMMIT on main`: scratchpad `r5b_check.py`, 90 rows (the designers' V-cases, the five
regressions and the A1-A5 rows), **0 rows where bash lands a commit or push on `main` and the
guard allows it**; the two regressions (`echo a\;git checkout -b x && git commit -m x`,
`echo x\r git checkout -b x && git commit -m x`) are refused; every A5 row is allowed. A second
batch (`r5b_check2.py`: 29 brace heads, each after `true || `, `! true | ` and bare) found one
row bash lands and the guard allows, `true || if { true; }; then echo; fi | git checkout -b x &&
git commit -m x`, which 8972524 allows too and which has no quoted, escaped or brace-argument
token in it (an `if` list inside an `||` operand ends the operand at its `;`); left alone, noted
for step 8.

---

## 4. Verification log

> Written in step 4: the static half. Command output, not a summary of it.

| Check | Result |
|---|---|
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `42 files already formatted` |
| `mypy` | `Success: no issues found in 11 source files` |
| `pytest -q` | `1162 passed` (run before and after the docs edits) |
| Plan completeness | no public signature or constant changed (`segments`, `git_subcommand`, `violation` unchanged, as planned); no unplanned public surface |
| `STRUCTURE.md` | in sync after the auditor's edits |
| `python .claude/hooks/guard_git.py` | entry point (hook, no showcase); runs with empty stdin, exit 0 |

Structure-auditor (before this step): no signature drift; four edits plus one optional, each verified against the code and applied: (1) tests entry's round 3 Trust bullet now names the escaped leaders and says the quoted `'if'`/`"!"` rows moved to round 5; (2) `\!` added to the known over-refusals in STRUCTURE.md and in the module docstring (the gap the auditor flagged); (3) the guard's opening paragraph in STRUCTURE.md and the module docstring no longer credit `shlex` alone with keeping a quoted `;`; (4) the `segments` table row states the round 5 contract; optional: "Three rows of two existing tests".

Section 3's deviations against section 1:

| # | Deviation | Invalidates a criterion? |
|---|---|---|
| 1 | Brace leaders compared in lower case | No. Implements A3's "do { } while" and keeps PowerShell loops; marked words never match. |
| 2 | Escapes in heredoc delimiter and unquoted `${ }` become stand-ins, not `_SOFT` | No. Inside one word, as A2 requires for `${x:-;}`; unquoted escapes elsewhere stay soft (A3). |
| 3 | `fresh()` after an unquoted `\r` | No. Keeps substitution order (A4, round 2 criteria). |
| 4 | `_prepare` give-up path turns `\r` into `_SOFT` | No. Play-safe, in line with A4 and the play-safe-on-`main` rule. |
| 5 | `_quoted_done` strips the mark and excludes `_SOFT` | No. Preserves round 3's `done` meaning (A6). |
| 6 | A piece holding `_SOFT` governs as `;`, so `segments` shows `;` for a CRLF break (was `\n`) | No. See below. |

Note: section 3 lists six bullets; the brief's "five" counts the `\r` heading differently, all six are classified here. Deviation 6 (the brief's deviation 5, `segments` output): `grep` finds no test that calls `segments` on a command with `\r`, and the suite is green, so nothing pins the old separator. Checked live: `segments('a &&\r\nb')` and `segments('a\r\nb')` both give separator `;`. This matches A4 (`&&\r\n` is not trusted) and A6/the soft-separator rule that a soft separator is never trusted; `;` is the widest-set separator, so it can only refuse more. Judgment: consistent, not a criterion change; the public output change is within "a soft separator splits and shows as `;`" now in STRUCTURE.md.

No criterion invalidated; no halt.

### Second verify (after the redo)

Run after step 3 was redone with the two readings (section 3, "Redo after step 5"). The first verify above is kept; its deviation table described the soft separator, and rows 2, 3, 4, 5 and 6 are superseded by the redo (the code no longer has `_SOFT`).

| Check | Result |
|---|---|
| `ruff check .` | `All checks passed!` (before and after the docs edits) |
| `ruff format --check .` | `42 files already formatted` |
| `mypy` | `Success: no issues found in 11 source files` |
| `pytest -q` | `1162 passed` (before and after) |
| Plan completeness | `segments`, `git_subcommand`, `violation` (and `switch_target`, `push_targets_main`) unchanged in signature, as planned; `INLINE_WHITESPACE` is `" \t"` as planned; no unplanned public name (the `_SOFT`, `_group_position`, `_ESCAPED_OPERATORS` and `powershell` flags are all private) |
| `STRUCTURE.md` | in sync after the auditor's edit below |
| `python .claude/hooks/guard_git.py` | hook entry point, no showcase; runs with empty stdin, exit 0 |

Structure-auditor (after the redo): no signature drift, no private name leaking, "soft separator" gone everywhere, round 3 Trust bullet and round 5 paragraph match the tests. Applied, each checked against the code: (1) STRUCTURE.md tests entry now says "ahead of the round 2, round 3, round 4 and round 5 sections"; optional: (2) the module docstring's "reads both the same way" now ends "except for the three tokens below", matching the paragraph after it; (3) the `segments` docstring states that a quoted operator character stays in its word, that the bash reading is returned and that no quote mark or stand-in appears in the output; (4) the module docstring's list of unread constructs names `${| cmd; }` as well as `${ cmd; }`.

The redo's three deviations (section 3, "Redo after step 5") against section 1:

| # | Deviation | Invalidates a criterion? |
|---|---|---|
| 1 | `coproc echo {` read as a group (bash reads `{` as an argument there); every `\|\|` form built on it still refused, checked in bash | No. Over-refusal on the safe side of A3; the both-shell-safe scope of section 1 holds. |
| 2 | `_group_position` leaders are case-sensitive in the bash reading while the PowerShell reading keeps every brace-only token a delimiter | No. Each shell's keywords are read in its own reading, and `violation` refuses if either refuses, so A3's `do { } while` and ForEach-Object forms stay refused. |
| 3 | `true \|\| if { true; }; then echo; fi \| git checkout -b x && git commit -m x` allowed although bash lands a commit; 8972524 allows it too and it has no quoted, escaped or brace-argument token | No. Outside the class section 1 names (a different cause: an `if` list ending an `\|\|` operand), so no criterion promises it and A6 does not cover it; left alone and noted for step 8. |

No criterion invalidated; no halt. No test changed outcome in the redo beyond the two rewrites of the first run (A4, A5).

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
