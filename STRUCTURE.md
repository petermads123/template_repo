# Structure

Map of everything in this repo. Loaded into context at the start of every session via the
`@STRUCTURE.md` import in `CLAUDE.md`, so it is what Claude uses to find things without
searching.

## Keeping this file current

Update it **in the same change** that causes any of the following:

- a module is added, deleted, renamed or moved
- a public function or class is added or removed
- a public signature changes (parameters, defaults, return type)
- a module's purpose changes

Private helpers (names starting with `_`) are intentionally left out. They are
implementation detail, and listing them is what makes a file like this rot.

The stop gate (`.claude/hooks/stop_gate.py`) cross-checks the module paths named here
against the `.py` files on disk and blocks on a mismatch. It only sees file-level drift —
signature drift is on you, or run the `structure-auditor` subagent.

That covers `src/`, `tests/` and `.claude/hooks/`. The hooks are documented here with full
signature tables, type-checked like the package (`[tool.mypy] files` names all three) and
importable from the suite (`[tool.pytest.ini_options] pythonpath` names `src` and
`.claude/hooks`, so a test imports a hook by module name the same way a sibling hook does
at runtime), so they are held to the same standard despite not being installable.

## Growth

While the package is flat, keep everything here. Once it has subpackages, keep the tree and
one line per subpackage in this file, and move per-subpackage detail into
`.claude/rules/structure-<subpackage>.md` with `paths: ["<subpackage>/**"]` so it loads only
when Claude works in that subpackage. Split rather than delete — there is no length limit
here, but everything in this file is in context every session.

## Tree

```
src/                    everything installable; nothing outside it is packaged
  template_repo/        the package itself (rename this to <package_name>)
tests/                  pytest suite, one test_<module>.py per module
development/            one folder per branch, one file per round: the pipeline's state
.claude/                Claude Code configuration: rules, skills, agents, hooks
.vscode/                editor config (Ruff as formatter, format on save)
pyproject.toml          packaging, Ruff, mypy and pytest configuration
DEVELOPMENT.md          development-side open questions and things to fix later (see CLAUDE.md)
README.md               human setup guide
CLAUDE.md               routing map for Claude
STRUCTURE.md            this file
```

## Package: `src/template_repo/`

### `src/template_repo/__init__.py`

Package entry point. Re-export the public API here so callers can
`from template_repo import X` rather than reaching into modules, using relative imports so
it survives renaming the package folder. Nothing is exported yet — the placeholder script
has no public API.

Every package directory under `src/`, including every subpackage added later, needs one of
these. The stop gate blocks on a directory of modules without it: it is not a package, so
it will not install.

### `src/template_repo/hello_world.py`

Placeholder so the package is not empty. Delete the whole file when real code arrives.

| Signature | Description |
|---|---|
| `main() -> None` | Print `Hello, World!`. |

It is deliberately trivial and is **not** the conventions reference — `/implement` carries
the worked module and `/test` the worked test file, so the examples do not disappear with
the placeholder.

Runnable standalone: `python -m template_repo.hello_world`, once the package is installed
(`pip install -e ".[dev]"`). Under a `src/` layout the repo root is not on `sys.path`, so
without the install it fails with `No module named template_repo` — an un-set-up
environment, not a broken module.

## Tests: `tests/`

### `tests/test_hello_world.py`

Covers the placeholder script's `main` via `capsys`: the exact output, that it is one line,
that nothing goes to stderr, and that a second call prints the same thing. Deleted along
with the script it covers. The edge-case standard is demonstrated in `/test`, not here.

All tests live here and nowhere else — `testpaths = ["tests"]` in `pyproject.toml` means
`pytest` collects nothing outside this directory, and the stop gate blocks on a test file
found anywhere else.

### `tests/test_guard_git.py`

Covers `.claude/hooks/guard_git.py` — every public function plus `main` end to end against a
throwaway repository, over both Bash and PowerShell command forms — and is the regression
suite for the quoting defect its parser was rebuilt to fix. One test asserts a documented
miss rather than a fix: `sudo -u me git push` is allowed, because only options are skipped
after a wrapper and never a bare word.

The shell-lexing cases follow, ahead of the round 2, round 3, round 4, round 5 and round 6 sections. The reproduction for the defect `fix/guard-git-shell-lexing` fixes comes first: a heredoc whose body carries a stray quote (`python3 - <<'EOF'` ... `EOF`), allowed on `main` rather than refused as unreadable. Then, each checked against real bash with `git` shadowed by an echo function:

- **Heredocs** — a body with no substitution in it is data in every delimiter form (`<<`, `<<'`, `<<"`, `<<\`, `<<-` with tabs); a command after it, on its opener line, after two heredocs on one line or after a comment on the opener is still judged; `git commit -F - <<'EOF'` is refused as a commit and the pipeline's `"$(cat <<'EOF' ...)"` form keeps its outcome; an unquoted delimiter lets a backslash-newline join the closing line and a quoted one does not; a CRLF script closes on `EOF` plus the return; an unterminated heredoc takes the rest as body while an earlier push is still refused; `<<<` is a here-string; a shift in `$((1<<2))`, `(( x <<= 1 ))` and `let` is arithmetic, and `((echo a); ...)` stays two subshells.
- **Substitutions in an unquoted heredoc body** — the halt-table commands refused (`$(git commit)` on `main`, the backtick push also from a branch), each form bash runs (quoted inside the body, a stray apostrophe, continuation, nested parentheses, `${x:-$(...)}`, inside arithmetic, an escaped backslash before the `$(`) refused, and text bash does not run (`\$(`, `$((1<<2))`, `${x}`, an unclosed substitution) allowed; every quoted-delimiter form left as data; harmless substitutions such as `$(date)` allowed on `main`; a stray quote in a substitution not breaking the pairing for a later commit; the second of two heredocs; a body substitution of a double-quoted `$( )` whose heredoc closes on the `)` (nested double-quote frames, a backtick holder, single quotes around and inside, a double quote opened after the heredoc operator, two heredocs with the last one closing, a PowerShell backtick before the substitution; the harmless and quoted-delimiter counterparts allowed, an unbalanced quote with no heredoc left unreadable, and an unterminated heredoc in a substitution — a bash syntax error — read as unreadable); `segments` token expectations for the extracted commands.
- **A heredoc closed by the substitution's `)`** (round 2, after the step 6 halt) — the three shapes the second concept check found refused on `main` and from a branch: a body substitution after a single-quoted double quote, the command after `echo "$(cat <<EOF … EOF)"` (` ; `, newline, quoted delimiter, an apostrophe in the body) and the unquoted `x=$(cat <<EOF … EOF); git push origin main`, with harmless counterparts allowed; a matrix of closing lines checked against bash 5.2 with `git` shadowed (`EOF )`, a tab before the `)`, `EOF)x`, `EOFx)`, a continuation, the rest of the line holding a push in a bare word, a backtick or a `$( )`, `<<-`, quoted delimiters, nesting, a subshell, a backtick pair, `>( )`, `${x:-$( )}`, arithmetic, two heredocs, a comment after the delimiter); lines bash does not close on left as body (a leading space, `EOF;`, `EOF foo` with the `)` on the next line, a top-level subshell); the `$(cat <<EOF)` form whose body follows still judged.

Re-test after that halt (`-k` closing line): a second hunt around the same rule, each shape run in bash 5.2 with `git` shadowed (no bypass found, no production change). A closing line in every kind of substitution (`<( )`, `>( )`, `${x:-$( )}` quoted or not, a `)` in a quote or comment on the line, `EOF\)`, a `case` pattern, a backtick pair, nested `$( )`, what follows the `)` joined by `&&`, `|`, `&`, `#`, a blank line or a quote-laden body); the delimiter shapes a closing line takes (several tabs under `<<-`, a delimiter that is or holds `)`, a body line starting with the delimiter text, two substitutions or two heredocs on one line, a heredoc inside a body); what bash does not run and the guard allows (a `)` in quotes or a comment on the closing line, a leading space, a tab under plain `<<`, a CRLF script); the cases bash rejects as a syntax error and the guard over-refuses; `&&` trust across a closing line, with the `;` over-refusal on `main`; and the pipeline's own commit form (`EOF\n)"`, `EOF)"`, a `)` and an apostrophe in the message) refused on `main`, allowed on a branch and after `git checkout -b x &&`.
- **Comments** — a word-start `#` comments out the line after each blank and operator, so quotes in comments no longer pair across lines; a `#` is kept as text after a `$( )`, inside `${ }`, after a carriage return, a quote or an escaped blank, in `$#` and `${#x}`; a comment inside backticks ends at the backtick; a `#` after a subshell's `)` or a redirect is a comment; a switch whose `&&` is only in a comment is distrusted.
- **Continuations** — a backslash-newline joins `git` and `commit` or `push` in either branch, inside double quotes and across an `&&`, but not in single quotes, not after an escaped backslash and not inside a comment.
- **Unmodelled syntax** — the exact `UNMODELLED_OPENERS` set; each reproduction bypass refused on `main` with its own reason and allowed on a branch, in a detached HEAD and on `Main`; forms that name neither commit nor push, or hide the opener in quotes, a comment or a body, allowed; the accepted `&&` plus `$'...'` cost pinned; and recorded misses (a hex-escaped or split-quote subcommand, a risky word in a comment still refusing) so changing them is a decision.

Round 2 of the same fix (`development/fix/guard-git-shell-lexing/02-...`) adds the reproduction
for command substitutions inside a word: `echo "$(git commit -m x)"` refused on `main` instead of
allowed. Five round 1 tests that pinned the old behaviour were rewritten to the new one — the
substitution miss, the three that pin where an extracted command sits in `segments`' output, and
the unresolvable switch across a weak join — and the `UNMODELLED_OPENERS` pin gained the funsub
openers. The rest of the round's suite follows the reproduction, each group checked against real
bash with `git` shadowed:

- **Substitution positions** — twenty-two positions a `$( )` sits in (assignments, `${x:-…}`,
  tests, here-strings, redirections, `for`/`case` words, arrays, `printf -v`, `$[ ]`, wrappers,
  subshells, nesting) refused on `main`, a push form from a branch; `segments` puts each
  extracted command at depth 1 before the command containing it, with `SUBSTITUTED` on that
  command, the first group inheriting its separator, two groups in a row, two levels closing,
  and the pipeline's own `"$(cat <<'EOF' … EOF\n)"` form with a `)` and an apostrophe in it;
  forged group marks and placeholders in the input are blanked.
- **Backticks and process substitution** — every position, nested, and `<( )`/`>( )` in either
  direction, replaced whole by the placeholder; PowerShell escapes (`` `n ``, `` `t ``, an
  unpaired backtick before a `#`) no longer hide a later push or misplace the slot.
- **Order and trust** — the substitution runs before its command (three forms and a nested one),
  `&&` trust carried into and through groups, an empty group leaving the separator alone, a
  switch inside a substitution widening the command's branches (two pinned over-refusals), and a
  switch aimed at another repository ignored.
- **Main as any branch it could be** — an untrusted switch to `main` after `;`, a newline, `||`,
  `&`, `|`, a subshell or a substitution; a switch elsewhere allowed; the commit, push, then
  unresolved order of reasons; a switch target a substitution made refused as unresolvable
  (`-b`/`-c` excepted), with `switch_target` pinned on the placeholder.
- **Funsub** — every opener, inside double quotes too, refused on `main` with the reason naming
  it, allowed elsewhere or when it names neither commit nor push.
- **Harmless and literal text** — `git status` in a substitution, single-quoted and escaped
  `$(`, plain arithmetic and an empty group allowed on `main`.
- **`case` patterns and arithmetic** — a pattern's `)` inside a `$( )`, a backtick or a heredoc
  body no longer closes it, `case` as an argument opens nothing, a `case` outside any
  substitution still reads; a substitution inside `$(( ))` or `(( ))`, quoted or not, is judged
  while plain arithmetic is left alone.
- **Limits and failure** — thousands of nested or unclosed openers finish quickly and play safe
  on `main`, a nesting past the limit is pinned as unjudged off `main`, an internal error is
  refused on `main` and allowed elsewhere (`violation` and `main`), and the recorded misses (a
  lone `'` inside a quoted `${ }`) are pinned so changing them is a decision; a `git checkout -` inside a substitution refuses the command as unresolvable, and a detached HEAD (`""`) still refuses a push to `main` inside a substitution while allowing a commit.

Round 3 (`development/fix/guard-git-shell-lexing/03-...`) adds the reproduction for the reserved
words, under its own heading at the end of the file: `if git commit -m x; then echo ok; fi` refused
on `main` instead of allowed. The rest of the round's suite follows it, each shape checked against
bash with `git` shadowed where bash can run it:

- **Reserved words at a command position** — twenty-seven commands refused on `main` (every leader,
  chains such as `if !`, `! !` and `time !`, after `&&`, `||`, `|`, `&`, `;` and a newline, inside
  `$( )`, backticks, `<( )`, a subshell, a group and an unquoted heredoc body, after an assignment
  or a redirection); a quoted heredoc body left as data; a push to `main` after a leader refused from a branch too, and a push of `HEAD` after a leader
  resolved against the branch it is on (refused on `main`, allowed elsewhere).
- **Hidden switches** — a switch after a leader counted for a later commit from a branch and from a
  detached HEAD; a switch to another branch, a `-C` switch and `-m then` allowed.
- **Trust** — a switch led by `!` or `coproc` (also after `time`, chained, a push, a switch to
  `main`) refused; the same inside a negated pipeline or group (`! true | git checkout ...`,
  `! (git checkout ...)&&`, `coproc { }`); `&&` trust kept where no `!` leads the switch, a
  negation ended by `;`, and `ok | {target}` rather than `possible | {target}`; the order of the
  reasons; the accepted cost of a switch in a condition pinned (refused on `main`, allowed from a
  branch) with the compound-command and escaped or misplaced leader over-refusals (`\!`, `x=1 if`, `>/dev/null !`, `sudo -n !`; the quoted `'if'` and `"!"` rows moved to round 5 as allowed).
- **Leaders as arguments** — `echo if case; git commit` inside a substitution refused (a leader
  that is an argument opens no `case`), while a `case` after a real leader still opens one.
- **Words that are not commands** — `echo if`, `for git in`, `select`, `case git in`, `IF` and
  `Then` allowed; `{ }`, `time`, `case`, both function forms unchanged; a leader with nothing behind it.
- **Loops** — a switch anywhere in a bash, nested, substituted, unclosed or PowerShell loop counted
  for the whole loop; PowerShell keywords in any case; the range bounded (a switch after `done`, a
  loop-free commit, a switch to another branch, a `-C` switch, `do { }` in a bash loop); a `done` that is a case pattern or
  quoted not closing the loop, and the places a real one does; a stray `done`; a loop in a
  subshell pinned as running on; a repeated call giving the same answer.
- **`git_subcommand`** — every leader, chained leaders and wrappers, the arguments returned, the
  name-taking words, the closers `fi`, `done` and `esac`, case and the glued `!git` not stepped,
  leaders alone, a leader after the command read as an argument, and a `-C` git after a leader
  returned as is for `violation` to judge.

Round 4 (`development/fix/guard-git-shell-lexing/04-...`) adds the reproduction for the trust after
`||`, under its own heading at the end of the file: `git status || git checkout -b x && git commit -m x`
refused on `main` instead of allowed. The rest of the round's suite follows it, each form checked
against bash 5.2 with `git` shadowed by a function keeping HEAD in a file:

- **Every `||` operand form** — twenty-seven forms refused on `main` (a later pipeline stage via `|`
  and `|&`; `time`, `sudo`, `nohup`, an assignment or a redirection before the switch; a substitution
  on the switch; chained `||`; `||` after an `&&` chain; `coproc true ||`; a heredoc on the switch;
  an `&&` ending a line; more `&&` segments; the commit inside `"$( )"` or `$( )`; the whole inside
  `{ }`, `$( )` or an `if` condition; a group glued either side; a trailing space before the
  newline; a heredoc body substitution), the push of `HEAD`, the named switch from a branch, a
  switch to `main` before the `||`, a left side that may have failed, and the line forms (blank
  lines, a comment, a continuation, `||` then `|` then a newline).
- **Union and closing** — both sides of an `||` unioned for the `&&` after it (five allowed);
  an operand closed by a substitution ending, by `;` or a newline, and by its group closing; an `||`
  written inside a quoted heredoc body read as data; the rule leaving a branch or a detached HEAD alone; a
  dangling `||` allowed and a leading one that names a commit refused; a 5,000-link chain and
  2,000 open groups finishing quickly.
- **The `!`/`coproc` scope** — nine forms refused on `main`: a negation or `coproc` whose switch carries a
  `$( )` or backtick holding `&&`, `;`, `||` or a nested `!`, the same leak on an `||` operand's switch, and
  `! true | ` with a trailing space before the newline; a scope ended by `;` or by an `||` at its own level
  (`! git diff --quiet || { ... }` allowed, the same `||` with an unbraced switch refused by the operand rule).
- **What stays allowed** — create-or-switch, `git fetch || true && ...`, `true || false && ...`, an
  `||` operand wholly in a group, the staged-commit chain and two ended substitutions leaving no state.
- **A substitution opening with a group, siblings and `case`** (found by the step 5 readers) — a
  `$( (true) )`, `$( { true; } )` or backtick group in an `||` switch's substitution no longer
  leaves the outer group count raised; state at a substitution's depth ends when it closes, so a
  sibling substitution after `$(true || ...)` or `$(! true)` is judged on its own; `;;`, `;&` and
  `;;&` end a `case` clause's list, so a later clause is not charged with an earlier `||` or `!`.
  `! true` + newline + `{ git checkout -b x && git commit -m x; }` is pinned as refused, as at 43eeea3.
- **The separator runs behind each segment** (read through the private splitter behind `segments`) — eighteen pinned runs (`||` before a group, `; } &&`,
  `)&&`, `||(`, `);`, an empty group, a newline run, `case` terminators, a substitution's inherited
  run followed by what is written inside it, the close marker before siblings and before the command
  around a substitution, operators dropped before a close), and the segments identical whether or not
  the runs are collected.

Round 5 (`development/fix/guard-git-shell-lexing/05-...`) adds the reproduction for quoted
operators, under its own heading at the end of the file: `true || echo ";" | git checkout -b x && git commit -m x`
refused on `main` instead of allowed. Three rows of two existing tests changed outcome as the concept agreed:
round 3's quoted `'if'` and `"!"` pins are now allowed on `main`
(`test_violation_allows_a_quoted_leader_on_main`) and the `&&\r\n` row of the substitution-trust test is
now refused (`test_violation_refuses_a_commit_after_an_and_and_carriage_return`). The rest of the round's
suite follows the reproduction, each bash claim run in bash 5.2 with `git` shadowed (HEAD in a file, an empty
checkout argument failing, `PATH=/usr/bin:/bin`, stdin closed, a timeout, the oracle shown live first by a
plain commit landing on `main`); a row with no oracle is PowerShell-only or needs a real `sudo`/`env`, and the
guard is asserted to play safe there:

- **`segments`, quoted operators** -- twenty-one quoted words (`";"`, `"&&"`, `'&'`, `'|'`, `'||'`, `'('`, `')'`,
  `'{'`, `'}'`, `'<'`, `'>'`, `";"";"`, `a';'`, a quoted newline or CRLF, a quote inside the other kind) and ten
  operator characters inside an unquoted `${...}` each stay in one invocation; a real operator beside a quoted
  one, a quote state carried through `"$( )"`, a quoted heredoc delimiter (three spellings) and an unbalanced
  quote around an operator (`None`).
- **`segments`, the bash reading** -- fifteen shell-dependent tokens (an escaped operator character, a brace
  argument, a carriage return inside a word) are word characters; a brace is a group only after nothing, a
  leader, `time`, `coproc NAME` or `function NAME`, never when quoted; `a\r\nb` and `a &&\r\nb` keep the
  `\r` in a word; no stand-in or quote mark appears in any token or separator, and every private character in
  the input is blanked, in `segments` and in `violation` (a forged `if`, a split `git`, a split push option).
- **The `||` operand and the `!` scope** -- the reproduction row's twenty-six quoted or `${...}` words refused
  after `true || echo W | git checkout -b x && git commit -m x`, all twenty-six again after `! true | echo W | git checkout -b feat/x && ...`, allowed from
  another branch, plus the group form `{ true || echo } | ...; }`; a real `;` or `&&` beside a quoted one still
  ends the operand (five allowed forms).
- **Shell-dependent tokens, both readings** -- twelve tokens (`\;`, `\&`, `\|`, `\(`, `\)`, `\{`, `\<`, `{`, `}`,
  `{}`, `}}`, `{ }`) after `echo` ahead of a switch and after an `||`; the readers' regressions (an escaped
  `;` glued to a word, `-exec true \;`, a carriage return in a word, a brace after an escaped operator, `coproc C {`,
  `time -p {`, `function f {`, a cased `DO {`, `${x:-)}` and `${x:-a\nb}`, a split through `git -c user.name=a\;b commit` and
  `push -o x\; origin main`); the thirteen over-refusals pinned on purpose (bash lands nothing; PowerShell reads the
  token as an operator, or the guard does not model a command that fails); and the PowerShell scriptblocks (`ForEach-Object { }`, `Invoke-Command`, `Start-Job`,
  `% { }`, `try { }`, a `Do { } While` and `foreach` block counting a switch), asserted
  refused with no oracle.
- **Carriage return** -- `&&\r\n`, `&&\r\n\r\n`, `&& \r\n` and a backslash-CR continuation refused on `main`; a
  commit or push ended by `\r`, `\r\n` or ` \r\n` refused; a quoted `\r` and one after the last command
  allowed.
- **Quoted words at command position** -- `'if'`, `'!'`, `"!"`, `"X=1"`, `'>'`, `echo ";"` and `''if`
  followed by a commit allowed on `main`; a quoted program, wrapper, option, subcommand or ref still the word
  it spells (twenty-seven refused rows, `'!' git checkout -b x && git commit -m x` pinned as an over-refusal);
  a switch written with quoted words still trusted; `git_subcommand` over tokens carrying the quote mark
  (never a leader, assignment or redirection; marker-free output; its own tokens not mutated).
- **Quote and escape state** -- forty-nine rows around an operator: an escaped quote, a backslash in single
  quotes, `"\\"`, nesting through `"$( )"`, backticks and `${...}`, `$"..."`, a quoted operator beside a
  refspec, a push option or a switch.
- **Rounds 1 to 4 unchanged** -- nineteen rows run through the same oracle: a commit message holding `;`, `|`,
  `&&`, `(` and `{`, `"$(git commit -m x)"`, the pipeline's own heredoc commit, quoted and escaped heredoc
  delimiters, `${x:-a; git commit -m x; }`, the `||` rules and three `!` forms with a quoted operator.
- **Limits** -- four thousand quoted or escaped operators in one command and a two-thousand-link `||` chain
  finish quickly; a command too tangled to read (the pre-pass forced to give up) is refused on `main` when it names
  `commit` or `push` and allowed otherwise; the round 5 forms give the same answer twice.

Round 6 (`development/fix/guard-git-shell-lexing/06-...`) adds the reproduction for compounds, under its
own heading at the end of the file: `true || if true; then echo; fi | git checkout -b x && git commit -m x`
refused on `main` instead of allowed. Step 4 adds the reproduction for a closer written with an escape or a
quote (`true || while false; do :; \done; :; done | git checkout -b x && git commit -m x`, also `d\one`,
`do''ne`, `f\i`, `es\ac` and `[[ x == \]] && b ]]`, after `true ||` and `!`): sixty rows, each checked in bash
to land the commit on `main`. Step 5 adds the rest of the round's suite, each row run in bash 5.2 with `git`
shadowed by a function keeping HEAD in a file (an empty checkout argument failing, `PATH=/usr/bin:/bin`, stdin
closed, a timeout, the oracle shown live first by a plain commit landing on `main`) and, except where noted, landing the
commit on `main`. The scope openers are `true ||`, `git status ||` and `!` (the matrix uses `true ||`, `false ||` and `!`
instead; the `false ||` operand runs, so those rows are refused as play-safe); each body is also asserted allowed from another branch:

- **Misplaced openers** -- sixteen words that look like an opener but follow an assignment, a redirection, a wrapper,
  a backslash or a quote (`x=1 while`, `>/dev/null until`, `sudo if`, `env while`, `nohup case`, `time 'if'`,
  `\! while`) inside an `if` and a `while` body.
- **Closer runs** -- a closing word written straight after `)`, `}` or another closer (`(echo) fi`, `{ :; } fi`,
  `fi fi`, `done done`, `[[ a ]] fi`, `((1)) fi`, `case ... b) (:) esac`), twenty-three bodies; a `}` after a closer is a group
  in both readings; `coproc NAME <compound>` and `coproc <compound>` (thirteen bodies); `case` with an empty last
  clause bare, in `{ }` and in `( )`; the brace-position check behind `segments` reading a brace after a run of closing
  words as a group, and after an argument (`echo fi`, `fi echo`, a quoted `fi`, `x=1 done`) as a word.
- **The rest of the class** -- `[[ ]]` forms, a `case` pattern's parentheses after each terminator, nested cases and
  patterns spelled like a closing word, chained leaders, the arithmetic `for`, `time -p` before `|` and `|&`, and a push
  after six compound shapes, as `git push origin HEAD` and as a bare `git push`, refused with the push reason.
- **Whole commands** -- a compound inside a substitution, backticks and an unquoted heredoc body; the negation inside
  a leading `if` and the clause-terminator scopes still allowed; the compound `&&` over-refusals, `coproc` forms,
  `(( ))`, `{ }`, `( )`, function definitions, a stray `fi`, `done` or `esac` and a compound left open or closed by the
  wrong word kept refused (twenty rows); fifteen rows allowed, among them an escaped `\[[` or `i\f` and a switch after a
  closed loop or inside a compound.
- **The pairing** -- the private compound pairing behind `violation` reports every valid body above as paired and twenty
  unpaired shapes as not (an opener left open, a closer with no opener or the wrong one, one inside a substitution that
  ends first, a closing word where none can stand); a command that does not pair is refused with the commit reason after
  a switch the bash reading would otherwise trust, and allowed from another branch, while the same switch after a paired
  `if` is trusted; the PowerShell reading is exempt; `\!` shows as `!` in `segments`, opens no compound but is still
  stepped over as a leader, and a forged mark is blanked.
- **The container matrix** -- three openers by twenty-two constructs that hold a list terminator (`{ ; }`, `( ; )`,
  `$( ; )`, backticks, `if`, `case` with `a)` and `(a)` patterns, the loops, `[[ && ]]`, `(( && ))`, a function, and
  nests of them) bare, in braces and with the whole command in braces: 198 rows, pure Python.
- **Depth** -- two thousand nested `case`, two thousand nested `if` (closed with `;` and with a run of closers), a thousand nested `if` holding a subshell closed
  by `) fi`, three thousand unclosed `[[` and five thousand stray closers finish in seconds.

### `tests/test_plan_state.py`

Covers `.claude/hooks/plan_state.py`: every public function, the `Plan` properties either
side of `GATE_FROM_STEP`, and the git helpers against a throwaway repository.

### `tests/test_stop_gate.py`

Covers `.claude/hooks/stop_gate.py`: every public function and `main`'s paths through the
gate. `gate_failures`, `enforce` and `main` are driven through a monkeypatched `venv_tool`,
`capture` and checks rather than real executables: running them for real would invoke Ruff,
mypy and `pytest` from inside `pytest`, and stub executables would need a shell script on
POSIX and an `.exe` on Windows.


## Plans: `development/`

One folder per branch, one numbered file per round inside it, created at the close of step
1 from `TEMPLATE.md` and carried through all ten steps:

```
development/
  TEMPLATE.md                     copied for each new round; never itself active
  feat/csv-export/                the folder is the branch name, so it nests one level
    01-csv-export.md              round 1, shipped
    02-streaming-writer.md        round 2, opened from round 1's recommendation R2
```

Each file holds the concept and acceptance criteria, the plan, the verification and test
logs, the concept-check audit, the recommendations and the pull request, plus a `Halted`
section if the build stopped to ask. A fix round's section 1 also carries a **Defect**
block — reproduction, root cause, class, blast radius, scope — filled from the `/fix`
diagnosis; its presence is what tells the later steps the round is a fix. Every round
of a feature shares one branch and one pull request; a later round's **Builds on** section
names what the earlier rounds delivered, and its step 6 re-checks their acceptance criteria
as a regression pass.

The first line after the title is the workflow's state and is read by the hooks:

```
<!-- claude-plan step=3 status=active -->
```

`step` is 1 to 10; `status` is `active`, `done`, `parked` or `template`. Exactly one file
across the whole repo should be `active` — opening a round stands its predecessor down to
`done`, and step 9 marks the newest round `done` in the commit that opens the pull request,
so `main` never carries a live marker. Every step commits and pushes the file with what it
produced: plan files are the record of why the code looks the way it is, the state any
session resumes from, and what `/create-pr` builds the pull request body from.

## Claude configuration: `.claude/`

| Path | Role |
|---|---|
| `settings.json` | Registers the four hooks; pre-approves ruff/mypy/pytest, `python -m`, and the git commands the pipeline uses (read-only ones plus add, commit, push, fetch, checkout, switch, merge, mv) so an unattended build never stalls on a prompt — `guard_git.py` is what keeps that safe |
| — | Every skill pins `model` and `effort` in its frontmatter; the table in `CLAUDE.md` says which and why |
| `skills/build/` | `/build` — steps 3 to 7 as one unattended block, with `models.md` holding the per-step model and effort table and its rationale: a subagent per step on its pinned model, the step's readers (`structure-auditor`, `test-designer`) run by the orchestrator and handed over in the brief, work-in-progress commits, commit and push after each, halting rules, trace relay, resume from the marker or an interrupted run |
| `rules/python.md` | Coding conventions, auto-loaded for `**/*.py` |
| `skills/repo-setup/` | `/repo-setup` — one-time setup of a repo made from this template; carries `main_protect.solo.json` and `main_protect.collab.json` |
| `skills/feature/` | `/feature` — starts or resumes the pipeline |
| `skills/fix/` | `/fix` — starts the pipeline from a defect: reproduces, finds the root cause, sizes the class, has the diagnosis criticised, decides whether it is a bug at all, then hands to `/conceptualize` as a fix round |
| `skills/conceptualize/` | `/conceptualize` — step 1, agree the concept |
| `skills/plan/` | `/plan` — step 2, design it |
| `skills/implement/` | `/implement` — step 3, write the code (inside `/build`) |
| `skills/verify/` | `/verify` — step 4, static verification |
| `skills/test/` | `/test` — step 5, edge-case suite |
| `skills/concept-check/` | `/concept-check` — step 6, audit against the concept |
| `skills/ship/` | `/ship` — step 7, close the round: whole-tree gates and diff review (inside `/build`) |
| `skills/recommend/` | `/recommend` — step 8: critical follow-ups only, usually none, decided with the user; lesser ideas noted in `DEVELOPMENT.md`; with nothing critical it hands on to `/create-pr` |
| `skills/create-pr/` | `/create-pr` — step 9, pull request ready for review |
| `skills/watch-pr/` | `/watch-pr` — step 10, hourly review watch until merge or close |
| `skills/small-change/` | `/small-change` — cosmetic edits, outside the pipeline |
| `agents/diagnosis-critic.md` | Subagent that tries to falsify a defect diagnosis before step 1 agrees a fix on it — re-runs the reproduction, traces the cause independently, checks the class (feeds `/fix`); may run code from a scratch directory but never writes to the tree; pinned to `opus` |
| `agents/plan-critic.md` | Read-only subagent that reads a plan against its concept and the repo before the user accepts it (feeds step 2); pinned to `opus` |
| `agents/test-designer.md` | Read-only subagent that finds edge cases; run twice at step 5 with the `input-space` and `contract` briefs |
| `agents/brainstormer.md` | Read-only subagent that proposes at most three follow-ups through one lens — `user`, `maintainer`, `integrator` or `defect-class` — or none; step 8 runs only `defect-class`, on a fix round, and the others run when the user asks what to build next |
| `agents/structure-auditor.md` | Read-only subagent that reconciles this file (feeds steps 4 and 6) |

### `.claude/hooks/plan_state.py`

Shared by the other hooks: parses the `claude-plan` marker out of the plan files and
answers which plan is active, plus the small git helpers the hooks need. Importable by its
siblings because Python puts a script's own directory on `sys.path`. Stdlib only.

| Signature | Description |
|---|---|
| `Plan` | Frozen dataclass: `path`, `step`, `status`, `title`, `branch`, `feature` (the folder relative to `development/`, so the branch name with its `/`; empty for `TEMPLATE.md`), `round_number`, plus `step_name` and `gated` properties. |
| `parse(path: Path) -> Plan \| None` | Parse one plan file, or None if it has no valid marker. |
| `all_plans(project_dir: Path) -> list[Plan]` | Every parseable plan in every feature folder, most recently modified first. |
| `active_plan(project_dir: Path) -> Plan \| None` | The plan the pipeline is working through. |
| `feature_rounds(project_dir: Path, feature: str) -> list[Plan]` | One feature's rounds, oldest first; `feature` is the folder relative to `development/`, as on `Plan.feature`. |
| `git_lines(project_dir: Path, args: list[str]) -> list[str]` | Run git, return output lines. |
| `current_branch(project_dir: Path) -> str` | The checked-out branch, or `""`. |
| `main() -> None` | Showcase: prints the plans found, the active one and its sibling rounds. |

`GATE_FROM_STEP = 8` is the step at which the stop gate starts blocking: steps 3 to 7 are
the build, which carries its own gates and must be able to halt on a red tree.
`PLAN_DIR = development` is the directory it scans; `Plan.feature` is a folder path relative
to it, so a branch-named folder such as `feat/csv-export` comes back with its `/`.

### `.claude/hooks/session_brief.py`

`SessionStart` hook. Injects the active plan's step into a new session's context, the skill
that resumes it (`/build` for steps 3 to 7), plus what any earlier rounds of the same
feature delivered, so work resumes without the user having to re-explain it. Silent when
no plan is active — including while a pull request is open, since step 9 closes the plan.
Stdlib only.

| Signature | Description |
|---|---|
| `brief(project_dir: Path, plan: Plan) -> str` | Describe one active plan's state. |
| `main() -> None` | Entry point: emit the brief as session context. |

### `.claude/hooks/guard_git.py`

`PreToolUse` hook on `Bash` and `PowerShell`. Refuses a `git commit` or `git push` that
would land on `main`. Reads the command the way a shell does — a pre-pass marks every quoted operator character and `shlex` then resolves quoting, so a `;` or `|`
inside a commit message stays part of the message (below) — then splits it on the real separators
into one invocation per segment. The grouping delimiters `(`, `)`, `{` and `}` split too, so
a command hidden inside `(git commit -m "x")` is seen rather than left with `(` sitting
where its name should be.

Each segment is judged against the set of branches that may be checked out when it runs.
Only `&&` guarantees its left side succeeded, so a branch switch replaces the set across a
run of separators that is `&&` and newlines (bar the right side of an `||`, below), and only
widens it across anything else:
`git checkout -b feat/x && git commit` is allowed from `main`, and so is the same pair with
the `&&` ending the line, while after `;`, `|`, `||`, `&`, a bare newline or a mixed run
such as `; &&` HEAD may be on the branch it started on or on any branch switched to since,
and a commit or push is refused when `main` is one of them — from a branch too, so
`git checkout main; git commit` is refused. A switch made inside a subshell that has since
closed is distrusted the same way, as possibly having happened; one aimed elsewhere by a
global `-C`, `--git-dir` or `--work-tree` changes nothing here. A switch on the right of `||`
runs only when its left side failed, so the `&&` after that operand trusts what the left side
trusted as well as the switch (`a || git checkout -b x && git commit` is refused from `main`,
`git checkout -b feat/x || git checkout feat/x && git commit` allowed): the operand runs from
the `||` to the next `&&`, `;`, `&`, newline or `case` clause terminator (`;;`, `;&`, `;;&`) at its own
substitution depth and group level — a newline only where no `||`, `|` or `&&` runs into it — or until
the group or substitution it sits in closes, and only inside it is the switch trusted. A reserved-word compound
(`if` to `fi`, `case` to `esac`, `while`, `until`, `for` or `select` to `done`, `[[` to `]]`) is a group of its own
in that key, as `{ }` and `( )` are, so a terminator inside one does not end an operand or `!` scope opened outside
it, and a `case` pattern's parentheses (the optional `(` and the first `)` after `in` or after a `;;`, `;&` or `;;&`)
are the pattern's rather than a group's. Bash reads a reserved word only as the first word of a command, so `if`,
`while` and `until` open a compound as leaders, chained or not, and `case`, `for`, `select` and `[[` as the command
word, where the walk from the start of the invocation meets only reserved words that take a command next (`then`,
`do`, `else`, `elif`, `!`, `time` and its options, `coproc` with or without a name: `coproc C while …`). After an
assignment, a redirection, a wrapper program or any ordinary word, and when the word is written with a quote or a
backslash, it is an ordinary word and opens nothing (`x=1 while`, `>/dev/null if`, `sudo case`, `\! while`); a `[[`
whose `]]` is in the same invocation opens nothing. `fi`, `esac` and `done` close one as the first word of an
invocation that follows `;`, a newline, `&`, a `case` clause terminator, a `)` or a `}`, as each further closing word
written after one (`fi fi`, `done done`), and as the closing word after a `]]` that closed a `[[` (`[[ a ]] fi`); a
closing word ahead of a case pattern's `)` is the pattern's and closes nothing. A `]]` token closes an open `[[`. Each
substitution depth pairs its own, and a substitution's end drops what was open inside it. A command in which some
opener or closer finds no partner (an opener left open, a closer that matches nothing or the wrong kind, a closing
word where none can stand) is a syntax error to bash, or a shape the pairing does not read, so in the bash reading no
branch switch in it is trusted: each leaves `main` among the branches HEAD could be on, as a `!` does, and the
command can only be refused more, never less (the PowerShell reading has no `fi` and is exempt). A `!` or `coproc` scope is keyed between the compounds its invocation opens: outside an `if`, `while` or
`until` written before the `!`, and inside one written after it or opened by the command word. So
`! if true; then echo; fi | git checkout -b feat/x && git commit -m x` keeps the scope past the `fi` and is refused,
while in `if ! git diff --quiet; then git checkout -b feat/x && git commit -m x; fi` the `;` before `then` ends it
and the commit is allowed. What still cannot be read is refused when it names `commit` or
`push` — matched on word boundaries, so `committee` is not a commit — while `main` is
checked out, and allowed anywhere else.

Within a segment it finds the command name where a shell would, after the prefix of
variable assignments and redirections, so `GIT_EDITOR=true git commit` and
`>log git commit` are seen. Backticks around a substitution are stripped, the executable is
matched without regard to case, and a short list of wrapper programs — `sudo`, `env`,
`time`, `nohup`, `doas` — is stepped over. That list is deliberately incomplete: a wrapper
nobody listed is a miss, which is safe, while scanning a segment for any `git` token would
refuse `echo git commit`, which is the failure this module treats as worse. Only options are
skipped after a wrapper, never a bare word, so an option that takes a value hides what
follows it.

The reserved words that take a command next — `if`, `then`, `else`, `elif`, `while`, `until`,
`do`, `!` and `coproc` — are stepped over the same way, singly or chained, so a `git` behind
one is judged like any other (`for`, `select`, `case`, `function` and `in` are followed by a
name or pattern and never stepped over). The one list is shared with the pre-pass's `case`
placement, and a leader opens a command only where a command could start (`echo if case` reads
`case` as an argument). Trust follows the separator, except that a switch led by `!` or `coproc`
— or inside the pipeline or group such a word leads, until a `;`, newline, `&`, `&&`, `||` or a `case` clause's `;;`, `;&` or `;;&` ends
the list at its own substitution depth and group level (one inside a `$( )` or a deeper group does not), or the group or substitution it sits in closes — only widens what an `&&` can trust, because the `&&` after a negated
command runs when it failed and `coproc` returns at once. bash's own `if`/`while`/`until` logic is not modelled:
`then`, `do`, `else` and `elif` follow `;` or a newline, so every branch is in play, and
`if git checkout -b feat/x; then git commit -m x; fi` is refused from `main`. A branch
switch anywhere in a loop counts for all of it — bash loops from `for`, `select`, `while` or
`until` to the matching `done`, PowerShell's `foreach`, `for`, `while` and `do { } while ()`
(keywords in any case) to the end of the command, a loop's condition included. A `done` closes a
loop only where bash reads one — not after `|`, not ahead of a case pattern's `)`, and not at all
when the command writes a quoted `done` — and one written straight after a `)`, a `}` or another `done`
closes no loop here either, which only widens the loop to the end of the command; a `do {` inside a bash loop is bash's. Known
over-refusals: a misplaced or backslash-escaped leader (`x=1 if`, `\!`) is stepped over when finding the command's name
(it opens no compound), a compound command ends an `&&`
chain's trust, a loop in a subshell runs on; a backslash-escaped operator or bare brace argument that
PowerShell reads as an operator is refused although bash lands nothing (`echo \; git commit -m x`,
`git checkout -b x \; && git commit -m x`, `&& echo { &&`), `'!' git checkout -b x && git commit -m x` is
refused because a command named `!` failing is not modelled, `coproc NAME {` is read as a group even
where bash reads `{` as an argument, and a `coproc` leading a compound piped into a switch
(`coproc if true; then :; fi | git checkout -b x && git commit -m x`) is refused although bash commits on `x`. Known misses: a function is judged where it is
defined, not where it is called; a switch target that is a variable; a redirection on a compound
command, which bash runs before its body; PowerShell's glued braces and `ForEach-Object` pipelines.

A quoted word is never an operator. The pre-pass writes what `shlex` would throw away into the
text: inside quotes, and inside an unquoted `${ }`, each of `; & | ( ) { } < >` and the newline
becomes a private stand-in that stays in its word and is mapped back by `segments`, so `echo ";" x`
is one invocation and no quoted text reaches an `||` operand or a `!` scope. A word that holds a quote or a
backslash escape anywhere in it carries a private mark in front of the first one, so `'if'`, `"!"`, `"X=1"`,
`'>'`, `d\one` and `do''ne` are words and not a reserved word, a compound's closer, an assignment or a
redirection (`\!` has a mark of its own, which keeps the round 3 over-refusal of stepping over it as a leader but lets it
open no compound) (`'!' git commit -m x` is allowed on `main`), while
`"git" commit` is still git: every comparison of a token's text strips the mark. Three tokens differ
between bash and PowerShell, so the pre-pass writes the text twice and `violation` judges both
readings, returning a refusal from either (bash's first). A backslash before an operator character is
a word character in bash (the operator's stand-in) and a literal backslash in PowerShell, which leaves
the operator real; a carriage return is a word character in bash (`&&\r\n` runs a command named `\r`,
so the commit after it is read across a newline) and a line break in PowerShell; a bare `{` or `}`
argument is a word in bash and a script block delimiter in PowerShell (`ForEach-Object { git commit }`
stays refused). In the bash reading a brace is a group only where a reserved word could stand — the
first word, after `;`, a newline or an operator, after `then`, `do`, `!` and the other leaders, after
`time` and its options, after `coproc NAME`, after `function NAME` and after a run of closing words (`fi`, `esac`,
`done`) — and a word anywhere else
(`echo {`, `echo }}`, `{}`); leaders match case-sensitively. In the PowerShell reading every brace
token is a delimiter, as it was before round 5. `segments` returns the bash reading.

`shlex` is not a shell, so a private pass runs in front of it and removes what
bash never runs: a `#` at the start of a word comments out the rest of its line, a
backslash-newline joins two lines, and a heredoc body (`<<WORD`, `<<-WORD`, quoted or not,
never `<<<`) is dropped up to its delimiter line, leaving the `<<` and its word so the
invocation still reads as a redirection. A heredoc whose delimiter never arrives takes the rest of
the input as its body, as bash does. A heredoc opened inside a `$( )`, `<( )` or `>( )` may close on
a line that carries the substitution's own `)` — bash finds the end of the substitution before it
reads the heredoc — so `EOF)`, `EOF )`, `EOF) ; cmd`, `EOFx)` and `EOF git push origin main)` end the
body at the delimiter, close the substitution and leave the rest of the line to be read as
commands (verified in bash 5.2): any line that begins with the last queued heredoc's delimiter and
holds a `)` counts, which covers everything bash does and reads a little more as commands. A
heredoc in a top-level subshell or a backtick pair needs the bare delimiter line. A body after a quoted delimiter is pure data; one after an
unquoted delimiter is expanded by bash, so its `$( )` and backtick substitutions are extracted
(below) and the rest of the text is dropped — an escaped `$(` is text,
`$(( ))` is arithmetic and `${ }` a parameter (a substitution inside either still runs), and a
substitution that never closes runs nothing. The pass tracks what it is inside — `$( )`, `${ }`,
backticks, double quotes, `$(( ))` and `(( ))` — because the rules change there: a `#` after a
`$( )` or inside `${ }` is part of a word, `<<` in arithmetic is a shift, and quotes nest in
`"$( )"`. Known misses, kept deliberately: a subcommand spelled with hex escapes or split
quotes, which the raw-text search does not read as `commit`, and `"${x:-'$(cmd)'}"`, whose
single quotes are literal in bash but read as quoting here. The pass also reports a construct
it does not read — a pair in `UNMODELLED_OPENERS`: `$'...'`, PowerShell here-strings, `<# #>`
comments, backtick-escaped quotes, bash 5.3's `${ cmd; }` and `${| cmd; }`. It does not guess: with `main` checked out, such a command that names `commit` or
`push` is refused with its own message, and anywhere else it is judged as parsed.

Bash runs a command substitution before the command around it, wherever it sits in a word,
so the pass takes each one out — `$( )` quoted or not, backticks, `<( )` and `>( )`, the
inside of `$(( ))` and `(( ))`, and the ones in an unquoted heredoc body — and writes it,
between two private marks (`\x1d`, `\x1e`, blanked if the input carries them), in front of the
simple command that contains it. The end of a `$( )` is found by the pass's own walk, which
reads the `)` of a `case` pattern as the pattern's and not the substitution's. The word keeps
a placeholder (`\x1f`, shown as `_` by `segments`; `violation` sees it as it is, so a switch
target a substitution made is told from a branch name). `segments` reads the marks as
`Segment.depth`, so the extracted commands get every rule a plain command gets: separators,
`&&` trust, wrappers, subshells, nesting; a substitution that runs nothing leaves no trace.
`violation` runs a substitution on the branches in effect for its containing command, and a
switch inside it counts for that command. A backtick inside double quotes also stays in the
text, because PowerShell reads it as an escape, and one with no partner is only a character; a
substitution that never closes stays in the text and is not extracted. Reading a command is
budgeted in proportion to its length: past it, the pass gives the command back unchanged and
flagged, which plays safe on `main`, and a failure of any kind in `violation` is treated as
unreadable input — refused on `main` when it names `commit` or `push`, allowed elsewhere.

A push's destination is read with the same care. The arguments are walked rather than
filtered, so an option that takes a value — `-o`, `--push-option`, `--repo`,
`--receive-pack`, `--exec` — does not leave its value standing where the remote should be,
and `git push -o ci.skip origin` is seen as the bare push it is. Every ref is then reduced
to the branch it names: a leading `+` dropped, the destination half of a `src:dst` pair
taken, `refs/heads/` stripped, backticks removed and `@` read as `HEAD`. Switch targets go
through the same reduction, so `git checkout refs/heads/main` is a switch to `main`.

A branch switch whose target only the running shell can resolve — `git checkout -`,
`@{-1}`, a word a command substitution made — leaves the branch *unknown* rather than unchanged, and a `commit` or `push` that
meets an unknown branch is refused with a message saying so rather than the one about
`main`. Stdlib only.

| Signature | Description |
|---|---|
| `Segment` | Frozen dataclass: `tokens`, the `separator` that preceded them — one of `SEPARATORS`, a newline, a grouping delimiter (`""` for the first) or `SUBSTITUTED` — and `depth: int = 0`, the number of command substitutions the invocation sits inside. |
| `SUBSTITUTED: str` | `"$("`, the separator of an invocation whose command substitutions ran immediately before it. |
| `segments(command: str) -> list[Segment] \| None` | Split a command into invocations after comments, continuations and heredoc bodies are removed, or None if it cannot be read: an unbalanced quote or a trailing backslash. A heredoc whose delimiter never arrives takes the rest of the input as its body. Every command substitution — in a word, in backticks, in `<( )`/`>( )`, in an arithmetic expansion or in an unquoted heredoc body — becomes invocations of its own, one depth deeper, immediately before the invocation that contains it, which is marked `SUBSTITUTED`; the first of them inherits the separator that preceded the containing invocation, and a substitution that runs nothing leaves no trace. A word that held one reads `_`. A quoted operator character stays in its word (`echo ";" x` is one invocation), and it returns the bash reading — an escaped operator character is a word character, a bare brace argument is a word unless a reserved word could stand there, and a carriage return stays in its word — while no private stand-in or quote mark appears in the output. |
| `git_subcommand(tokens: tuple[str, ...]) -> tuple[str, tuple[str, ...]]` | Identify the git subcommand and its arguments. |
| `push_targets_main(args: tuple[str, ...], branch: str) -> bool` | Whether a push would update `main`. |
| `switch_target(subcommand: str, args: tuple[str, ...]) -> str` | The branch a `checkout`/`switch` moves to, `""` when it moves none, or the sentinel `UNRESOLVED` (`"?"`) for a target only the running shell can resolve — `-`, `@{-1}`, or a word a command substitution made (for `-B` and `-C`, the name they take). |
| `violation(command: str, branch: str) -> str` | The reason to refuse, or `""` to allow. Judges every invocation, substitutions included, against every branch it may run on, in the bash reading of the command and then in the PowerShell one (they differ on a backslash before an operator character, a bare brace argument and a carriage return), refusing if either refuses. While `main` is checked out, a command carrying any of `UNMODELLED_OPENERS` that names `commit` or `push` is refused outright. Never raises: a failure of any kind while judging is treated as unreadable input, refused on `main` when the command names `commit` or `push` and allowed elsewhere. |
| `UNMODELLED_OPENERS: tuple[str, ...]` | `("$'", "@'", '@"', "<#", "`'", '`"', "${ ", "${\t", "${\n", "${\|")`: the openers of syntax the pre-pass does not read — an ANSI-C string, a PowerShell here-string, a PowerShell block comment, a backtick-escaped quote, bash 5.3's `${ cmd; }` and `${| cmd; }`. Each is matched as a prefix. Looked for outside quotes, and `` `" `` and the `${` forms inside double quotes too. A command carrying one is what `violation` refuses on `main` when it names `commit` or `push`. |
| `main() -> None` | Entry point: allow or refuse the command. |

### `.claude/hooks/lint_py.py`

`PostToolUse` hook. Runs `ruff format` and `ruff check --fix` on any `.py` file Claude
writes or edits, and reports unfixable issues back via exit code 2. Stdlib only.

| Signature | Description |
|---|---|
| `find_ruff(project_dir: Path) -> Path \| None` | Locate Ruff in the project venv. |
| `run(ruff: Path, args: list[str]) -> CompletedProcess[str]` | Run Ruff, capturing output. |
| `target_file(payload: dict[str, object], project_dir: Path) -> Path \| None` | Extract the edited `.py` file from the hook payload. |
| `main() -> None` | Entry point: format, fix, report. |

### `.claude/hooks/stop_gate.py`

`Stop` hook. Reads the active plan's step to decide how strict to be: advisory through step
7, blocking from step 8 and whenever no plan is active, and only when a Python file changed
in the tree or on the branch. When it blocks it runs ruff, mypy
and pytest, cross-checks `STRUCTURE.md` against the modules on disk, reports any test file
sitting outside `tests/` where `pytest` would silently never collect it, and reports any
package directory under `src/` missing its `__init__.py`. Bypass with
`.claude/.skip-gate`. Stdlib only.

| Signature | Description |
|---|---|
| `venv_tool(project_dir: Path, name: str) -> Path \| None` | Locate a tool in the project venv. |
| `capture(cmd: list[str], cwd: Path, timeout: int) -> CompletedProcess[str]` | Run a command, capturing output. |
| `changed_python_files(project_dir: Path) -> set[str]` | Python files changed in the tree or on this branch. |
| `tracked_python_files(project_dir: Path) -> set[str]` | All non-ignored Python files. |
| `structure_problems(project_dir: Path) -> list[str]` | File-level drift between this file and disk. |
| `stray_test_files(project_dir: Path) -> list[str]` | Test files outside `tests/`, which pytest never collects. |
| `missing_init_files(project_dir: Path) -> list[str]` | Package directories under `src/` with no `__init__.py`. |
| `gate_failures(project_dir: Path) -> list[str]` | Run the verification set, collect failures. |
| `advisory_notes(project_dir: Path, plan: Plan, changed: set[str]) -> list[str]` | Non-blocking observations for the steps below the gate. |
| `notice(message: str) -> None` | Show the user a message without blocking. |
| `block(reason: str) -> None` | Emit the block decision and exit. |
| `enforce(project_dir: Path) -> None` | Run the verification set and block on failure. |
| `main() -> None` | Entry point: decide whether the turn may end. |
