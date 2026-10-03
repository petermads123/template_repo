"""PreToolUse hook: stop commits and pushes that would land on `main`.

`CLAUDE.md` says never commit to `main`, and the remote protects it anyway — but
a rejected push happens after the mistake, and a local commit on `main` has to
be unpicked by hand. This hook refuses the command instead, and says what to do
instead of just saying no.

It reads the command the way a shell does. `shlex` resolves quoting, so a `;` or
`|` inside a commit message stays part of the message instead of being mistaken
for a separator, and emits the real separators as tokens of their own even when
they are glued to a word. The command is then split on those separators into one
invocation per segment.

`shlex` is not a shell, so a pass in front of it (`_prepare`) removes what bash
never runs and `shlex` cannot read: a `#` at the start of a word comments out
the rest of its line, a backslash at the end of a line joins it to the next,
and a heredoc body is data up to its closing delimiter line (or to the end of
the input, as in bash, when the delimiter never arrives). Left in, a quote in a
comment or a body pairs with one in the next command, and either hides a real
`git commit` or makes a harmless command look unbalanced. The pass tracks what
it is inside, because bash's rules change there: a `#` after the `)` of a
`$( )`, inside `${ }` or after a carriage return is part of a word, not a
comment; quotes nest inside `"$( )"`; `<<` inside `$(( ))` or `(( ))` is a
shift, not a heredoc; and an unquoted delimiter lets a backslash-newline join
the closing line. Constructs it does not read -- `$'...'`, PowerShell
here-strings, `<# #>` comments, backtick-escaped quotes and bash 5.3's
`${ cmd; }` -- are not guessed at: while `main` is checked out, a command
carrying one that names `commit` or `push` anywhere, comments and bodies
included, is refused outright, and elsewhere it is judged as parsed, as
unreadable input always was.

Bash runs a command substitution before the command around it, wherever it
sits in a word, so the pass takes each one out and writes it, between two
private marks, in front of the simple command that contains it; the word keeps
a placeholder. That covers `$( )` quoted or not, backticks, `<( )` and `>( )`,
the inside of `$(( ))` and `(( ))`, and nests. The end of a `$( )` is found by
the pass's own walk, so a quote, a heredoc or the `)` of a `case` pattern inside
it is read as it is outside one. `segments` reads the marks as a depth, so the
extracted commands get every rule a plain command gets, separators, `&&` trust,
wrappers and subshells included; a substitution that runs nothing leaves no
trace. A heredoc body is data only when any part of its delimiter is quoted
(`<<'EOF'`, `<<"EOF"`, a backslash before a letter). After an unquoted one bash
expands the body and runs its `$( )` and backtick substitutions, so those are
extracted the same way, in front of the command that opened the heredoc, and
the rest of the body is dropped: an escaped `$(` is text, `$(( ))` is
arithmetic and `${ }` is a parameter, none of them a command, while a
substitution inside either of the last two still runs. A heredoc opened inside
a `$( )`, `<( )` or `>( )` may close on a line that carries the substitution's
own `)`, because bash finds the end of the substitution before it reads the
heredoc: `EOF)`, `EOF )`, `EOF) ; cmd`, `EOFx)` and `EOF git push origin main)`
all end the body at the delimiter, close the substitution and leave the rest of
the line, whatever it is, to be read as commands (checked in bash 5.2 with `git`
shadowed). The guard takes any line that begins with the last queued heredoc's
delimiter and holds a `)` as such a line, which covers everything bash does and
reads a little more as commands, so it can only add refusals. The rule is
limited to those substitutions: a heredoc in a top-level subshell, or in a
backtick pair (whose text bash has complete before it parses it), needs the bare
delimiter line, and so does one whose closing line has no `)`, a leading space
or, under plain `<<`, a tab. A backtick inside double
quotes is also left in the text, because PowerShell reads it as its escape
character, so both readings are judged; one with no partner is just a
character. A substitution that never closes is left in the text, not
extracted. Known misses, all deliberate: a subcommand spelled with hex escapes
or split quotes (`git co""mmit`) does not name `commit` to the raw-text search;
in `"${x:-'$(cmd)'}"` the single quotes are literal in bash but read as quoting
here, which hides the substitution, and so does a lone `'` in a quoted
parameter, as in `echo "${x:-'}" "$(cmd)" "'}"`; a push whose remote or
refspec is made by a substitution (`git push origin "$(git branch
--show-current)"`) is read as naming a branch called `_`; and substitutions
nested more than 30 deep are not followed, so off `main` the text past that is
not judged, while on `main` it plays safe. A command that costs more to read
than its length explains, or on which the guard fails for any reason, is
treated as unreadable.

Each segment is judged against the branches that may be checked out when it
runs, not the one checked out now: `git checkout -b feat/x && git commit` is
allowed from `main`, because `&&` runs its right side only if the switch
succeeded. No other separator carries that guarantee -- after `;` or a newline
the commit runs whether the switch worked or not -- so across those HEAD may be
on the branch it started on or on any branch switched to since, and a commit
or push is refused if `main` is one of them. Nor does a switch on the right of
`||`, which runs only when its left side failed: `a || git checkout -b x && git
commit` commits on the starting branch when `a` succeeded. The `&&` after such an
operand trusts what the left side trusted as well as the switch, so
`git checkout -b feat/x || git checkout feat/x && git commit` is still allowed;
the operand runs from the `||` to the next `&&`, `;`, newline or `&` at its own
substitution depth and group level, and only inside it is the switch trusted. A
substitution runs on the
branches in effect for the command that contains it, and a switch inside it
counts for that command and for what follows. A switch whose target a
substitution made (`git checkout "$(echo main)"`) is one only the shell can
resolve, except after `-b` and `-c`, which cannot land on a branch that exists.

What still cannot be read is refused rather than allowed when it names `commit`
or `push` and `main` is checked out. Such a command would usually fail in the
shell too, so refusing costs little, while allowing it would leave exactly the
hole this hook exists to close. Anywhere else, unreadable input is allowed: the
guard catches slips, and one that blocks legitimate work is worse than one that
misses an exotic invocation.

Inside a segment the command's name is found where a shell would find it, after
the prefix of variable assignments and redirections, with backticks stripped and
the executable matched without regard to case. A short list of wrapper programs
is stepped over too. That list is deliberately incomplete: a wrapper nobody
listed is a miss, which is safe, whereas scanning a segment for any `git` token
would refuse `echo git commit` — the failure this module treats as worse. Only
options are skipped after a wrapper, never a bare word, so an option that takes
a value hides what follows it.

The reserved words that take a command next -- `if`, `then`, `else`, `elif`,
`while`, `until`, `do`, `!` and `coproc` -- are stepped over the same way, singly
or chained (`if !`, `! !`, `time ! git`), so a `git` behind one is judged like
any other. `for`, `select`, `case`, `function` and `in` are followed by a name or
a pattern and are never stepped over. Trust follows the separator, as for any
command, with one exception: a switch led by `!` or `coproc` only widens the
branches an `&&` can trust, because the `&&` after a negated command runs when it
failed and `coproc` returns at once. That holds for everything the word leads --
a pipeline (`! a | git checkout ...`) or a group (`! (git checkout ...)`) -- until
a `;`, a newline, `&`, `&&` or `||` ends the list at its own substitution depth and
group level -- one inside a `$( )` or a deeper group does not. A leader opens a
command only where a command could start, so `echo if case` reads `case` as an
argument. Playing safe, bash's own `if`, `while` and
`until` logic is not modelled: `then`, `do`, `else` and `elif` follow `;` or a
newline, so every branch is in play there, and `if git checkout -b feat/x; then
git commit -m x; fi` is refused from `main`. A loop runs its body again, so a
branch switch anywhere in one counts for all of it: bash loops run from `for`,
`select`, `while` or `until` to the matching `done`, PowerShell's `foreach`, `for`,
`while` and `do { } while ()` -- keywords in any case -- to the end of the command,
and a loop's condition counts with its body. A `done` closes a loop only where
bash reads one: not after `|`, not ahead of a case pattern's `)`, and not at all
when the command writes a quoted `done`, which a tokenizer cannot tell from the
word, so every loop then runs on. A `do {` inside a bash loop is bash's. Known
over-refusals, kept: a quoted or misplaced leader (`'if' git commit`, `x=1 if
git commit`) is stepped over, a compound command ends an `&&` chain's trust, and
a loop in a subshell, `(for ...; done); cmd`, runs on. Known misses: a switch
target that is a variable, a redirection on a compound command, which bash runs
before its body, and PowerShell's glued braces and `ForEach-Object` pipelines.
Known miss: a function is judged where it is defined, not where it is
called, so `f() { git commit; }; git checkout main; f` is not seen.

A push's destination is read with the same care: the arguments are walked rather
than filtered, so an option's value is never mistaken for the remote, and every
ref is reduced to the branch it names. A switch whose target only the running
shell can resolve leaves the branch unknown rather than unchanged, and a
`commit` or `push` that meets an unknown branch is refused with a message saying
so rather than the one about `main`.

It runs for the PowerShell tool as well as Bash, and reads both the same way.
The git invocations that matter parse identically in either shell: quoted
arguments, `;` chains, `{ }` blocks and here-string messages. PowerShell 5.1
has no `&&`, so there a branch switch never carries into the next command, and
a commit on `main` is refused even straight after `git checkout -b`.

Stdlib only: `jq` may not be available and hook commands default to
Git Bash on Windows, so the usual shell recipe does not work here.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

from plan_state import current_branch

PROTECTED = "main"

#: Private marks `_prepare` writes around the commands it extracts from a
#: command substitution, so `segments` can tell how deep an invocation sits.
#: Neither is a character a shell command carries; `_prepare` blanks any that
#: arrive in the input so a command cannot forge a group.
_OPEN = "\x1d"
_CLOSE = "\x1e"

#: What a word keeps in place of a command substitution that was taken out of
#: it. `segments` shows it as `_`; `violation` sees it as it is, so a branch
#: switch whose target is a substitution can be told from one that names a
#: branch. Blanked in the input like the two marks.
_PLACEHOLDER = "\x1f"

#: Characters `shlex` emits as tokens of their own rather than folding into a
#: word. The default set plus the newline, which would otherwise be whitespace
#: and would silently join two commands written on two lines into one.
PUNCTUATION_CHARS = "();<>|&\n" + _OPEN + _CLOSE

#: Whitespace, minus the newline that `PUNCTUATION_CHARS` claims.
INLINE_WHITESPACE = " \t\r"

#: Tokens that end one invocation and begin the next.
SEPARATORS = frozenset({"&&", "||", ";", "|", "&"})

#: The characters those tokens are built from. `shlex` groups a run of
#: punctuation into one token, so `&&` followed by a newline arrives as the
#: single token `"&&\n"`; matching on characters catches every such run.
#: The grouping delimiters are here too: they begin and end a command list, so
#: `(git commit)` has to split rather than leave `(` sitting where the command
#: name should be, which would hide the `git` behind it.
SEPARATOR_CHARS = frozenset("&|;\n(){}" + _OPEN + _CLOSE)

#: The one separator whose right side runs only if its left side succeeded, so
#: a branch switch before it can be trusted to have taken effect.
GUARANTEEING = "&&"

#: Stands for one or more newlines between invocations. Separates them, but
#: guarantees nothing about whether the one before it succeeded.
NEWLINE = "\n"

#: Git options that swallow the next token, hiding the subcommand behind them.
OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--exec-path"}

#: The separator of an invocation whose command substitutions ran immediately
#: before it: a substitution runs first, so what follows it is neither joined
#: to the previous command by an operator nor the start of the command line.
SUBSTITUTED = "$("

#: Subcommands that move HEAD to a different branch.
SWITCH_SUBCOMMANDS = {"checkout", "switch"}

#: Their options that take the new branch's name as the following token.
NEW_BRANCH_OPTIONS = {"-b", "-B", "-c", "-C"}

#: Global options that aim git at a different repository, so anything the
#: invocation does happens somewhere other than here.
REDIRECTING_OPTIONS = {"-C", "--git-dir", "--work-tree"}

#: How git may be spelled as a command name, compared case-insensitively:
#: the documented target platform has a case-insensitive filesystem, and where
#: it does not, `GIT` fails to run anyway so refusing it costs nothing.
GIT_NAMES = {"git", "git.exe"}

#: A leading `NAME=value` is a variable assignment, part of the prefix a shell
#: skips before a command's name rather than the name itself.
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

#: Tokens that begin a redirection. `shlex` emits `>`, `<`, `>>` and `>&` as
#: tokens of their own, and a file descriptor in front of one as another.
REDIRECTION_STARTS = ("<", ">")

#: Programs that run their argument as a command. Deliberately short and
#: deliberately incomplete: a wrapper nobody listed is a miss, which is safe,
#: and extending the set is a one-line change.
WRAPPERS = {"sudo", "env", "time", "nohup", "doas"}

#: `git push` options whose value is the following token. Without these the
#: value is counted as the remote and the real remote as a refspec.
PUSH_OPTIONS_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}

#: Switch targets only the running shell can resolve.
UNRESOLVABLE_TARGETS = {"-", "@{-1}"}

#: What `switch_target` returns for those: the branch changed, to something
#: this module cannot name.
UNRESOLVED = "?"

#: Subcommands worth refusing an unreadable command over. Matched on word
#: boundaries: "committee" is not a commit.
RISKY_SUBCOMMANDS = ("commit", "push")
RISKY_PATTERN = re.compile(r"\b(?:" + "|".join(RISKY_SUBCOMMANDS) + r")\b")

#: Openers of constructs `_prepare` does not read: an ANSI-C string, a
#: PowerShell here-string, a PowerShell block comment, a backtick-escaped quote
#: and bash 5.3's `${ cmd; }` / `${| cmd; }` function substitution. All are
#: looked for outside quotes, each matched as a prefix; `` `" `` and the `${`
#: forms are also looked for inside double quotes. A command that carries one
#: is judged by `violation` with suspicion rather than trusted.
UNMODELLED_OPENERS: tuple[str, ...] = (
    "$'",
    "@'",
    '@"',
    "<#",
    "`'",
    '`"',
    "${ ",
    "${\t",
    "${\n",
    "${|",
)

#: Characters after which a `#` starts a word, and so a comment. The carriage
#: return is not one: bash's blanks are the space and the tab only. A `)` is one
#: only when it closes a subshell, which `_prepare` decides, so it is here for
#: the cases it does not track.
_COMMENT_BOUNDARY = " \t\n;&|()<>"

#: Characters that end a heredoc's delimiter word. Again no carriage return: in
#: bash it belongs to the word, so a CRLF script closes on `EOF\r`.
_DELIMITER_END = " \t\n;&|()<>"


@dataclass(frozen=True)
class Segment:
    """One invocation within a compound command.

    Attributes:
        tokens: The invocation's tokens, with quoting already resolved.
        separator: The separator that preceded it — one of `SEPARATORS`,
            `NEWLINE`, or a grouping delimiter such as `(`. Empty for the first
            invocation in the command, or `SUBSTITUTED` for one whose command
            substitutions ran just before it.
        depth: How many command substitutions the invocation sits inside. A
            substitution's invocations come immediately before the invocation
            that contains it.
    """

    tokens: tuple[str, ...]
    separator: str
    depth: int = 0


def _is_separator(token: str) -> bool:
    """Report whether a token separates invocations rather than being a word.

    Args:
        token: One token from the lexer.

    Returns:
        True if the token is built only from separator characters.
    """
    return token != "" and set(token) <= SEPARATOR_CHARS


def _governs(token: str) -> str:
    """Reduce one separator token to the separator that governs it.

    Args:
        token: A token for which `_is_separator` is true.

    Returns:
        The governing separator. A run containing `&&` keeps its guarantee,
        since an `&&` written at the end of a line still only runs its right
        side if the left side succeeded.
    """
    if GUARANTEEING in token:
        return GUARANTEEING
    stripped = token.strip("\n")
    if not stripped:
        return NEWLINE
    return stripped if stripped in SEPARATORS else stripped[0]


def _join(pending: list[str]) -> str:
    """Reduce a run of consecutive separators to the one that governs.

    An `&&` followed by a line break is a single `&&` join written across two
    lines, so newlines alongside an `&&` do not weaken it. Anything else in the
    run does: `)` ends a subshell whose branch switch never escaped it, and a
    `;` beside an `&&` means at least one path reaches the next invocation
    unconditionally. Only a run that is `&&` and newlines guarantees anything.

    Args:
        pending: The separators seen since the previous invocation ended.

    Returns:
        The governing separator, or an empty string if there were none.
    """
    if not pending:
        return ""
    meaningful = [separator for separator in pending if separator != NEWLINE]
    if not meaningful:
        return NEWLINE
    if all(separator == GUARANTEEING for separator in meaningful):
        return GUARANTEEING
    return next(s for s in meaningful if s != GUARANTEEING)


def _strip_substitution(token: str) -> str:
    """Remove backticks that ride on a token.

    `_prepare` takes a command substitution out of its word, so the lexer no
    longer sees the backticks of one; this is the fallback for a backtick that
    never paired, which stays in the text.

    Args:
        token: One token from the lexer.

    Returns:
        The token without surrounding backticks.
    """
    return token.strip("`")


def _branch_name(ref: str) -> str:
    """Reduce a ref to the branch it names.

    Args:
        ref: A refspec or branch as written on the command line.

    Returns:
        The branch name: stray backticks removed, a leading `+` dropped, the
        destination half of a `src:dst` pair, `refs/heads/` stripped, and `@`
        read as `HEAD`.
    """
    name = _strip_substitution(ref).lstrip("+").split(":")[-1]
    name = name.removeprefix("refs/heads/")
    return "HEAD" if name == "@" else name


def _walk_prefix(tokens: tuple[str, ...]) -> tuple[int, tuple[str, ...]]:
    """Walk the prefix a shell skips before a command's name.

    Args:
        tokens: The invocation's tokens.

    Returns:
        The index of the command name, or `len(tokens)` when the invocation is
        prefix and nothing else, and the reserved words stepped over on the way.
    """
    index = 0
    leaders: list[str] = []
    while index < len(tokens):
        token = tokens[index]
        if ASSIGNMENT.match(token):
            index += 1
            continue
        if token.startswith(REDIRECTION_STARTS):
            index += 2  # the operator and the file it redirects to
            continue
        if (
            token.isdigit()
            and index + 1 < len(tokens)
            and tokens[index + 1].startswith(REDIRECTION_STARTS)
        ):
            index += 1  # a file descriptor; its operator is handled next pass
            continue
        if Path(_strip_substitution(token)).name.lower() in WRAPPERS:
            index += 1
            # Only options are skipped, never a bare word, so this cannot walk
            # past a command name. An option that takes a value hides what
            # follows it -- `sudo -u me git push` reads as `me` -- which is a
            # miss rather than a false refusal.
            while index < len(tokens) and tokens[index].startswith("-"):
                index += 1
            continue
        if token in _STEPPED_LEADERS:
            leaders.append(token)
            index += 1  # the command it leads starts at the next word
            continue
        return index, tuple(leaders)
    return len(tokens), tuple(leaders)


def _command_index(tokens: tuple[str, ...]) -> int:
    """Find where a command's name starts, after the prefix a shell skips.

    A simple command is a run of variable assignments and redirections, then
    the name. Wrapper programs are stepped over too: they are not shell syntax,
    but they run their argument as a command, so the name behind one is the
    name that matters. So are the reserved words that take a command next --
    `if`, `then`, `while`, `!` and the rest of `_COMMAND_LEADERS` -- which a
    shell reads as syntax and not as the command's name. `for`, `select`,
    `case`, `function` and `in` are followed by a name or a pattern, so they
    are never stepped over.

    Args:
        tokens: The invocation's tokens.

    Returns:
        The index of the command name, or `len(tokens)` when the invocation is
        prefix and nothing else.
    """
    return _walk_prefix(tokens)[0]


def _leads_uncertainly(tokens: tuple[str, ...]) -> bool:
    """Report whether `!` or `coproc` leads an invocation.

    `&&` after a negated command runs when the command failed, and `coproc`
    returns at once, so a branch switch they lead cannot be trusted to have
    happened.

    Args:
        tokens: The invocation's tokens.

    Returns:
        True if `!` or `coproc` is among the words before the command name.
    """
    return any(word in _UNCERTAIN_LEADERS for word in _walk_prefix(tokens)[1])


def _redirected(tokens: tuple[str, ...]) -> bool:
    """Report whether a git invocation is aimed at another repository.

    Only the global options before the subcommand count: `-C` is also
    `git commit`'s "reuse this message" option, and `-C` after the subcommand
    says nothing about where the command runs.

    Args:
        tokens: The invocation's tokens.

    Returns:
        True if a global option redirects git elsewhere.
    """
    index = _command_index(tokens) + 1
    while index < len(tokens):
        token = tokens[index]
        if token in REDIRECTING_OPTIONS:
            return True
        if token in OPTIONS_WITH_VALUE:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return False
    return False


def _skip_single(command: str, start: int) -> int:
    """Find the end of a single-quoted string.

    Args:
        command: The command text.
        start: Index of the opening quote.

    Returns:
        The index just past the closing quote, or the length of the command
        when the string never closes.
    """
    end = command.find("'", start + 1)
    return len(command) if end == -1 else end + 1


def _skip_ansi(command: str, start: int) -> int:
    """Find the end of a `$'...'` string, where a backslash escapes a quote.

    Args:
        command: The command text.
        start: Index of the `$`.

    Returns:
        The index just past the closing quote, or the length of the command
        when the string never closes.
    """
    index = start + 2
    while index < len(command):
        if command[index] == "\\":
            index += 2
            continue
        if command[index] == "'":
            return index + 1
        index += 1
    return len(command)


class _TooComplexError(Exception):
    """Raised when reading a command costs more than its length can explain."""


def _spend(budget: list[int], cost: int = 1) -> None:
    """Charge one step of reading against the budget.

    Args:
        budget: A one-item list holding the steps left, shared by every walk
            over the same command.
        cost: How many steps to charge.

    Raises:
        _TooComplexError: When the budget runs out. A hook that reads a hostile
            command for ever is cut off by its timeout, and a timeout lets the
            command run; giving up in time lets `violation` play safe instead.
    """
    budget[0] -= cost
    if budget[0] < 0:
        raise _TooComplexError


def _arith_end(command: str, start: int, budget: list[int]) -> int | None:
    """Find the end of an arithmetic `((...))`, whose `<<` is a shift.

    Args:
        command: The command text.
        start: Index of the first of the two opening parentheses.
        budget: The steps left for reading this command.

    Returns:
        The index just past the closing `))`, or None when the parentheses do
        not close as a pair -- `((echo a); echo b)` is two subshells, and bash
        reads it that way.
    """
    depth = 2
    index = start + 2
    while index < len(command):
        _spend(budget)
        char = command[index]
        if char == "\\":
            index += 2
            continue
        if char == "'":
            index = _skip_single(command, index)
            continue
        if char == '"':
            index += 1
            while index < len(command) and command[index] != '"':
                index += 2 if command[index] == "\\" else 1
            index += 1
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 1:
                return index + 2 if command[index + 1 : index + 2] == ")" else None
        index += 1
    return None


def _heredoc_word(command: str, start: int) -> tuple[str, bool, int] | None:
    """Read a heredoc's delimiter word, resolving its quoting as bash does.

    Args:
        command: The command text.
        start: Index just past the `<<` and any `-`.

    Returns:
        The delimiter with quotes and backslashes removed, whether any were
        there (a quoted delimiter makes the body literal), and the index just
        past the word as written; None when there is no word.
    """
    index = start
    while index < len(command) and command[index] in " \t":
        index += 1
    word = ""
    quoted = False
    begin = index
    while index < len(command) and command[index] not in _DELIMITER_END:
        char = command[index]
        if char == "\\" and index + 1 < len(command):
            word += command[index + 1]
            quoted = True
            index += 2
        elif char in "'\"":
            end = command.find(char, index + 1)
            if end == -1:
                return None
            word += command[index + 1 : end]
            quoted = True
            index = end + 1
        else:
            word += char
            index += 1
    return (word, quoted, index) if index > begin and word else None


def _logical_line(command: str, position: int, join: bool) -> tuple[str, int]:
    """Read one line of a heredoc body, joining continuations when bash does.

    Args:
        command: The command text.
        position: Index of the line's first character.
        join: Whether a backslash-newline joins this line to the next. Bash
            does it for a body whose delimiter was written without quotes.

    Returns:
        The line, and the index of the first character after it.
    """
    line = ""
    while True:
        end = command.find("\n", position)
        piece = command[position:] if end == -1 else command[position:end]
        position = len(command) if end == -1 else end + 1
        trailing = len(piece) - len(piece.rstrip("\\"))
        if join and trailing % 2 == 1 and end != -1:
            line += piece[:-1]
            continue
        return line + piece, position


def _heredoc_bodies(
    command: str,
    start: int,
    queue: list[tuple[str, bool, bool]],
    in_substitution: bool = False,
) -> tuple[int, list[str]]:
    """Skip the bodies of the heredocs opened on the line that just ended.

    Args:
        command: The command text.
        start: Index of the first line after the newline that ended the line.
        queue: The delimiter, whether leading tabs are stripped (`<<-`) and
            whether the delimiter was quoted, for each heredoc, in the order
            they were opened.
        in_substitution: Whether the heredocs were opened inside a `$( )` or
            `<( )`. There bash finds the end of the substitution before it
            reads the heredoc, so the last heredoc's closing line may be its
            delimiter followed by the `)` that closes the substitution --
            `EOF)`, `EOF )`, `EOF) ; cmd`, `EOFx)` -- and the rest of that line
            is ordinary text. Any line that begins with the delimiter and holds
            a `)` ends the body here; that takes in everything bash does and
            reads a little more as commands, which can only add refusals.

    Returns:
        The index just past the last delimiter line -- or, for a line that
        closes the substitution as well, just past its delimiter, so the
        caller reads the rest of the line -- and the text of each body whose
        delimiter was unquoted, the only bodies bash expands, with
        continuation lines joined. When the input ends before a delimiter
        arrives that is the end of the input: bash warns and takes the rest as
        the body, and so does this.
    """
    position = start
    expanded: list[str] = []
    last = len(queue) - 1
    for number, (delimiter, strip_tabs, quoted) in enumerate(queue):
        lines: list[str] = []
        while position < len(command):
            begin = position
            line, position = _logical_line(command, position, join=not quoted)
            text = line.lstrip("\t") if strip_tabs else line
            if text == delimiter:
                break
            if (
                in_substitution
                and number == last
                and text.startswith(delimiter)
                and ")" in text[len(delimiter) :]
            ):
                position = begin
                while strip_tabs and command[position : position + 1] == "\t":
                    position += 1
                # A delimiter split by a continuation is read as text instead.
                position += (
                    len(delimiter) if command.startswith(delimiter, position) else 0
                )
                break
            lines.append(line)
        if not quoted:
            expanded.append("\n".join(lines))
    return position, expanded


def _quoted_end(text: str, start: int) -> int | None:
    """Find the end of a backtick pair.

    Args:
        text: The text holding it.
        start: Index of the opening backtick.

    Returns:
        The index just past the closing backtick, or None when it never
        closes. A backslash escapes the character after it.
    """
    index = start + 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
        elif text[index] == "`":
            return index + 1
        else:
            index += 1
    return None


def _body_substitutions(
    body: str, nesting: int, budget: list[int]
) -> list[tuple[str, str]]:
    r"""Pull the command substitutions out of text that bash expands.

    That is an unquoted heredoc body and the inside of an arithmetic
    expansion, which bash treats like a double-quoted string with the quote
    marks ordinary: `\` escapes only `$`, a backtick and itself, a quote of
    either kind means nothing, and `$( )`, `$(( ))`, `${ }` and backticks
    expand. Only the first runs a command of its own; arithmetic is not one,
    though a substitution inside it is, and `${x:-$(cmd)}` runs `cmd`.

    Args:
        body: The text, with continuation lines already joined.
        nesting: How many substitutions deep the text sits.
        budget: The steps left for reading this command.

    Returns:
        The text of each command substitution that bash would run, in order,
        for `_scan` to read as commands, each with the closer to walk it with:
        `")"` for a `$( )`, whose text then ends with its own `)` so the walk
        reads a heredoc closing line the way it did when the end was found, and
        `""` for a backtick pair. The end of a `$( )` is found with the
        walk `_scan` makes of ordinary text, so a quote, a heredoc or a `case`
        pattern inside it is read as it is there. A substitution that never
        closes runs nothing in bash and is left out, along with the rest.
    """
    found: list[tuple[str, str]] = []
    failed: set[int] = set()
    index = 0
    while index < len(body):
        _spend(budget)
        char = body[index]
        if char == "\\":
            index += 2 if body[index + 1 : index + 2] in ("$", "`", "\\") else 1
        elif char == "`":
            end = _quoted_end(body, index)
            if end is None:
                break
            inner = body[index + 1 : end - 1]
            found.append((re.sub(r"\\([$`\\])", r"\1", inner), ""))
            index = end
        elif body[index : index + 2] == "$(":
            if (
                body[index : index + 3] == "$(("
                and _arith_end(body, index + 1, budget) is not None
            ):
                index += 3  # arithmetic is no command; look inside it
                continue
            _, _, end, closed = _scan(body, index + 2, ")", failed, nesting, budget)
            if not closed:
                break
            found.append((body[index + 2 : end], ")"))
            index = end
        else:
            index += 1
    return found


#: How deep `_scan` follows command substitutions inside one another before it
#: stops extracting and plays safe. Far past anything written by hand; it keeps
#: the recursion inside Python's own limit.
_MAX_NESTING = 30

#: The first characters of `UNMODELLED_OPENERS`, so `_scan` tests only where one
#: could start.
_OPENER_STARTS = frozenset(opener[0] for opener in UNMODELLED_OPENERS)

#: Reserved words after which another command starts: the one list `_scan` uses
#: to place a `case` and `_command_index` uses to find the command name.
_COMMAND_LEADERS = frozenset(
    {"if", "then", "else", "elif", "while", "until", "do", "!", "coproc", "time"}
)

#: The leaders `_command_index` steps over. `time` is left out: it is a wrapper,
#: and is stepped with its options.
_STEPPED_LEADERS = _COMMAND_LEADERS - {"time"}

#: Leaders after which a branch switch is not trusted to have happened before
#: the next `&&`.
_UNCERTAIN_LEADERS = frozenset({"!", "coproc"})

#: Separators that end the list a `!` or `coproc` leads, outside any group.
_LIST_ENDS = frozenset({";", "\n", "&", "&&", "||"})

#: The operators a separator token is built from, in the order a shell reads
#: them: `)&&` is `)` then `&&`.
_OPERATORS = re.compile(r"\|\||&&|\|&|;;&?|;&|[;&|(){}\n]")

#: Where a list is: the depth of the substitution it sits in, and how many
#: `(` and `{` are open there.
_Key = tuple[int, int]

#: Words that open a bash loop, and the leaders among them.
_LOOP_COMMANDS = frozenset({"for", "select"})
_LOOP_LEADERS = frozenset({"while", "until"})

#: Characters that end a word, and those that make a word more than plain text.
_WORD_ENDS = " \t\r\n;&|()<>{}"
_WORD_SPECIALS = "\\\"'`$"


def _prepare(command: str) -> tuple[str, bool]:
    """Remove what a shell never runs and `shlex` cannot read.

    Walks the command once, tracking quotes as bash does. Outside quotes it
    drops a `#` comment up to its newline, deletes a backslash-newline so the
    lines join, and drops each heredoc body up to its delimiter line, leaving
    the `<<` operator and its delimiter word. Every command substitution --
    `$( )` quoted or not, backticks, `<( )` and `>( )`, and those in an
    unquoted heredoc body or an arithmetic expansion -- is taken out of its
    word and written, wrapped in two private marks, in front of the simple
    command that contains it, because bash runs it first; the word keeps a
    placeholder. Everything else passes through unchanged, so a command with
    none of these constructs lexes as before.

    The walk keeps a stack of what it is inside, because the rules change there:
    a `#` is not a comment inside `${...}` or right after the `)` that closes a
    `$(...)` (the word goes on), quotes nest inside `"$(...)"`, a `<<` inside
    `$((...))` or `((...))` is a shift, and the `)` that ends a `case` pattern
    closes nothing.

    Args:
        command: The full command line.

    Returns:
        The transformed text, and whether the command contains a construct this
        scan does not read, one of `UNMODELLED_OPENERS`. A command too tangled
        to read within its budget comes back unchanged and flagged, so that
        `violation` plays safe rather than running out of time.
    """
    command = command.replace(_OPEN, " ").replace(_CLOSE, " ")
    command = command.replace(_PLACEHOLDER, " ")
    budget = [20 * len(command) + 50_000]
    try:
        text, unmodelled, _, _ = _scan(command, 0, "", set(), 0, budget)
    except (_TooComplexError, RecursionError):
        return command, True
    return text, unmodelled


def _scan(
    command: str,
    start: int,
    closer: str,
    failed: set[int],
    nesting: int,
    budget: list[int],
) -> tuple[str, bool, int, bool]:
    """Walk part of a command for `_prepare`, stopping at a closing `)` if asked.

    Args:
        command: The full command text; indices refer to it.
        start: Where to begin.
        closer: `")"` to stop at the `)` that closes the `$( )` or `<( )` the
            walk starts inside, or `""` to walk to the end.
        failed: Positions of substitutions already found never to close, so a
            run of unclosed ones is not walked again and again.
        nesting: How many substitutions deep this walk is.
        budget: The steps left for reading this command, shared by every walk.

    Returns:
        The prepared text, whether an unmodelled construct was met, the index
        just past what was consumed, and whether the closer arrived -- always
        True for a walk to the end.

    Raises:
        _TooComplexError: When the budget runs out.
    """
    out: list[str] = [""]  # the first item is the slot of the first command
    slot = 0
    queue: list[tuple[str, bool, bool]] = []
    queue_slots: list[int] = []
    frames: list[str] = []  # "dq", "cmd" ($( or <( ), "paren", "brace", "bt"
    cases: list[int] = []  # how many frames deep each open `case` sits
    unmodelled = False
    boundary = True  # whether a `#` here would start a word
    word = ""  # the plain text of the word being read
    plain = True  # whether the word is plain text, with no quote or expansion
    command_position = True  # whether a word here would be a command's name
    index = start
    length = len(command)

    def fresh() -> None:
        """Reserve the slot in front of a new simple command."""
        nonlocal slot
        out.append("")
        slot = len(out) - 1

    def place(text: str, flag: bool, target: int) -> None:
        """Write one extracted substitution into a command's slot."""
        nonlocal unmodelled
        if _lex(text) is not None:  # one bash cannot run either is dropped
            out[target] += _OPEN + text + _CLOSE
            unmodelled = unmodelled or flag

    def from_text(text: str, target: int) -> bool:
        """Extract the substitutions of text bash expands; report any found."""
        nonlocal unmodelled
        if nesting >= _MAX_NESTING:
            unmodelled = True  # too deep to follow: play safe
            return False
        inners = _body_substitutions(text, nesting + 1, budget)
        for inner, ends in inners:
            prepared, flag, _, _ = _scan(inner, 0, ends, set(), nesting + 1, budget)
            place(prepared, flag, target)
        return bool(inners)

    def inside(position: int) -> tuple[str, bool, int] | None:
        """Prepare the substitution whose text begins at `position`."""
        nonlocal unmodelled
        if nesting >= _MAX_NESTING:
            unmodelled = True  # too deep to follow: play safe
            return None
        if position - 2 in failed:
            return None
        found = _scan(command, position, ")", failed, nesting + 1, budget)
        if not found[3]:
            failed.add(position - 2)
            return None
        return found[0], found[1], found[2]

    def finish_word() -> None:
        """End the word being read, opening or closing a `case` if it is one."""
        nonlocal word, plain, command_position
        if plain and command_position and word == "case":
            cases.append(len(frames))
        elif (
            plain
            and command_position
            and word == "esac"
            and cases
            and cases[-1] == len(frames)
        ):
            cases.pop()
        if word or not plain:
            # A leader opens a command only where a command could start: in
            # `echo if case` the `if` is an argument and `case` is one too.
            command_position = plain and command_position and word in _COMMAND_LEADERS
        word, plain = "", True

    while index < length:
        _spend(budget)
        char = command[index]
        pair = command[index : index + 2]
        top = frames[-1] if frames else ""
        in_double = top == "dq"

        if not in_double and top != "brace":
            if char in _WORD_ENDS:
                finish_word()
                if char in ";&|\n({)":
                    command_position = True
            elif char in _WORD_SPECIALS:
                plain = False
            elif plain:
                word += char

        if char in _OPENER_STARTS:
            for opener in UNMODELLED_OPENERS:
                if command.startswith(opener, index) and (
                    not in_double or opener == '`"' or opener.startswith("${")
                ):
                    unmodelled = True

        if char == "\\":
            if pair == "\\\n":
                index += 2  # a continuation: the lines join
                continue
            if in_double and pair[1:] not in ('"', "\\", "$", "`"):
                out.append(char)  # a backslash that escapes nothing
                index += 1
            else:
                out.append(pair)
                index += 2
            boundary = False
            continue
        if in_double and pair == '`"':
            out.append(pair)  # PowerShell's escaped quote; flagged above
            index += 2
            continue
        if char == '"':
            if in_double:
                frames.pop()
            else:
                frames.append("dq")
            out.append(char)
            index, boundary = index + 1, False
            continue
        if char == "$" and pair in ("$(", "${"):
            if pair == "${":
                funsub = command[index + 2 : index + 3] in (" ", "\t", "\n", "|")
                if not funsub:  # bash 5.3's `${ cmd; }` is flagged, not a parameter
                    frames.append("brace")
                boundary = funsub
                out.append(pair)
                index += 2
                continue
            if command[index + 2 : index + 3] == "(":
                arith = _arith_end(command, index + 1, budget)
                if arith is not None:
                    if from_text(command[index + 3 : arith - 2], slot):
                        out.append(_PLACEHOLDER)  # what ran is in the slot
                    else:
                        out.append(command[index:arith])
                    index, boundary = arith, False
                    continue
            found = inside(index + 2)
            if found is not None:
                place(found[0], found[1], slot)
                out.append(_PLACEHOLDER)
                index, boundary = found[2], False
                continue
            frames.append("cmd")
            boundary = True
            out.append(pair)
            index += 2
            continue
        if char == "`":
            if top == "bt":
                frames.pop()
                boundary = False
                out.append(char)
                index += 1
                continue
            end = _quoted_end(command, index)
            if end is not None and nesting >= _MAX_NESTING:
                unmodelled = True  # too deep to follow: play safe
                end = None
            if end is not None:
                inner = re.sub(r"\\([$`\\])", r"\1", command[index + 1 : end - 1])
                text, flag, _, _ = _scan(inner, 0, "", set(), nesting + 1, budget)
                place(text, flag, slot)
                if in_double:
                    # PowerShell reads the backtick as its escape character, so
                    # the text stays for it to be judged that way as well.
                    kept = command[index:end]
                    out.append(kept)
                    unmodelled = unmodelled or '`"' in kept
                    if len(re.findall(r'(?<!\\)"', kept)) % 2:
                        frames.pop()  # the kept text closed the string
                else:
                    out.append(_PLACEHOLDER)
                index, boundary = end, False
                continue
            if in_double:
                # Nothing to pair with: in bash an error, in PowerShell an
                # escape. Either way the string goes on, so a `#` after it is
                # still text and the quote that closes it still closes it.
                out.append(char)
                index, boundary = index + 1, False
                continue
            frames.append("bt")
            boundary = True
            out.append(char)
            index += 1
            continue
        if in_double:
            out.append(char)
            index += 1
            continue

        if pair == "$'":
            end = _skip_ansi(command, index)
            out.append(command[index:end])
            index, boundary = end, False
        elif char == "'":
            end = _skip_single(command, index)
            out.append(command[index:end])
            index, boundary = end, False
        elif char == "#" and boundary and top != "brace":
            stops = [command.find("\n", index)]
            if top == "bt":
                stops.append(command.find("`", index))
            found_stops = [stop for stop in stops if stop != -1]
            index = min(found_stops) if found_stops else length
        elif pair in ("<(", ">(") and (found := inside(index + 2)) is not None:
            place(found[0], found[1], slot)
            out.append(_PLACEHOLDER)  # the whole construct, `<` or `>` included
            index, boundary = found[2], False
        elif command[index : index + 3] == "<<<":
            out.append("<<<")
            index, boundary = index + 3, True
        elif pair == "<<":
            dash = command[index + 2 : index + 3] == "-"
            word_read = _heredoc_word(command, index + 2 + dash)
            if word_read is None:
                out.append("<<")  # no delimiter to read: leave it to `shlex`
                index, boundary = index + 2, True
                continue
            delimiter, quoted, end = word_read
            out.append(command[index:end])
            queue.append((delimiter, dash, quoted))
            queue_slots.append(slot)
            index, boundary = end, False
        elif char == "\n":
            out.append(char)
            index += 1
            boundary = True
            if queue:
                index, bodies = _heredoc_bodies(command, index, queue, closer == ")")
                owners = [
                    s
                    for (_, _, quoted), s in zip(queue, queue_slots, strict=True)
                    if not quoted
                ]
                queue, queue_slots = [], []
                for body, owner in zip(bodies, owners, strict=True):
                    from_text(body, owner)
            fresh()
        elif char == "(":
            arith = _arith_end(command, index, budget) if pair == "((" else None
            if arith is not None:
                if from_text(command[index + 2 : arith - 2], slot):
                    out.append(_PLACEHOLDER)
                else:
                    out.append(command[index:arith])
                index, boundary = arith, False
                continue
            previous = command[index - 1 : index] if index else ""
            frames.append("cmd" if previous in ("<", ">") else "paren")
            out.append(char)
            index, boundary = index + 1, True
            if frames[-1] == "paren":
                fresh()
        elif char == ")":
            if cases and cases[-1] == len(frames):
                out.append(char)  # the end of a `case` pattern closes nothing
                index, boundary = index + 1, True
                fresh()
                continue
            if closer == ")" and not frames:
                if queue:
                    unmodelled = True  # its body follows the substitution
                return "".join(out), unmodelled, index + 1, True
            popped = frames.pop() if top in ("cmd", "paren") else "paren"
            out.append(char)
            index, boundary = index + 1, popped == "paren"
            fresh()
        elif char == "}" and top == "brace":
            frames.pop()
            out.append(char)
            index, boundary = index + 1, False
        else:
            previous = command[index - 1 : index] if index else ""
            following = command[index + 1 : index + 2]
            out.append(char)
            index += 1
            starts_command = (
                (char in ";&|" and previous not in ("<", ">") and following != ">")
                or (char == "{" and boundary and following in (" ", "\t", "\n"))
            ) and top != "brace"
            boundary = char in _COMMENT_BOUNDARY
            if starts_command:
                fresh()

    return "".join(out), unmodelled, length, closer == ""


def _lex(prepared: str) -> list[str] | None:
    """Split prepared text into shell tokens.

    Args:
        prepared: Command text after `_prepare`.

    Returns:
        The tokens, quoting resolved, or None if a quote never closes or the
        text ends in a backslash.
    """
    lexer = shlex.shlex(prepared, posix=True, punctuation_chars=PUNCTUATION_CHARS)
    lexer.whitespace_split = True
    lexer.whitespace = INLINE_WHITESPACE
    # `shlex` comments out the rest of the line from a bare `#`, even inside a
    # word, which silently discarded everything after `echo ok#1 &&`.
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        return None


def segments(command: str) -> list[Segment] | None:
    """Split a shell command into its individual invocations.

    Args:
        command: The full command line the shell tool is about to run.

    Returns:
        One segment per invocation, in order, or None if the command could not
        be read at all — an unbalanced quote or a trailing backslash. Heredoc
        bodies, comments and continuations are removed first, and a heredoc
        whose delimiter never arrives takes the rest of the input as its body.
        Every command substitution -- in a word, in backticks, in `<( )`, in
        an arithmetic expansion or in an unquoted heredoc body -- becomes
        invocations of its own, one depth deeper, immediately before the
        invocation that contains it, which is marked `SUBSTITUTED`; the first of
        them inherits the separator that preceded the containing invocation. A
        substitution that runs nothing leaves no trace. A word that held one
        reads `_`.
    """
    parsed = _segments(command)
    if parsed is None:
        return None
    return [
        Segment(
            tuple(token.replace(_PLACEHOLDER, "_") for token in segment.tokens),
            segment.separator,
            segment.depth,
        )
        for segment in parsed
    ]


def _segments(
    command: str, *, runs: list[tuple[str, ...]] | None = None
) -> list[Segment] | None:
    """Split a command as `segments` does, leaving the placeholder as it is.

    Args:
        command: The full command line.
        runs: When given, receives one entry per returned segment: the operators
            written between it and the previous invocation, in order, one
            element each (`)&&` is `)` and `&&`). A substitution's first
            segment carries the run it inherits its separator from, and a
            segment whose separator is `SUBSTITUTED` an empty one.

    Returns:
        What `segments` returns, with `_PLACEHOLDER` standing in each word where
        a substitution was.
    """
    tokens = _lex(_prepare(command)[0])
    if tokens is None:
        return None

    parsed: list[Segment] = []
    current: list[str] = []
    pending: list[str] = []
    raw: list[str] = []  # the operators behind `pending`, as written
    separator = ""
    depth = 0
    after_close = False  # a substitution closed and no operator has come since
    # State at each group's mark.
    opened: list[tuple[int, str, list[str], list[str], bool]] = []

    def flush() -> None:
        if current:
            parsed.append(Segment(tuple(current), separator, depth))
            if runs is not None:
                runs.append(tuple(raw))
            current.clear()

    for token in tokens:
        if not _is_separator(token) and _OPEN not in token and _CLOSE not in token:
            current.append(token)
            continue
        for piece in re.split(f"([{_OPEN}{_CLOSE}])", token):
            if piece and piece not in (_OPEN, _CLOSE) and not _is_separator(piece):
                current.append(piece)  # a mark glued to punctuation that is no operator
            elif piece == _OPEN:
                flush()
                opened.append(
                    (len(parsed), separator, list(pending), list(raw), after_close)
                )
                depth += 1
                if after_close:
                    separator = SUBSTITUTED
            elif piece == _CLOSE:
                flush()
                depth = max(depth - 1, 0)
                if opened:
                    count, was_separator, was_pending, was_raw, was_after = opened.pop()
                    if len(parsed) == count:
                        # The group ran nothing, so the command around it
                        # follows whatever it would have followed without it.
                        separator, pending, raw, after_close = (
                            was_separator,
                            was_pending,
                            was_raw,
                            was_after,
                        )
                        continue
                pending = []
                raw = []
                separator = SUBSTITUTED
                after_close = True
            elif piece:
                if current:
                    flush()
                    pending = []
                    raw = []
                pending.append(_governs(piece))
                raw.extend(_OPERATORS.findall(piece))
                separator = _join(pending)
                after_close = False
            # The pieces left to right: an operator glued to a mark, as in
            # `&&\x1d` or `\x1e;`, is read in the order it was written.

    flush()
    return parsed


def git_subcommand(tokens: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    """Identify the git subcommand in one invocation.

    Args:
        tokens: The invocation's tokens.

    Returns:
        The subcommand and the arguments following it. Both are empty when the
        invocation is not git.
    """
    start = _command_index(tokens)
    if start >= len(tokens):
        return "", ()
    if Path(_strip_substitution(tokens[start])).name.lower() not in GIT_NAMES:
        return "", ()

    index = start + 1
    while index < len(tokens):
        token = tokens[index]
        if token in OPTIONS_WITH_VALUE:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token, tokens[index + 1 :]
    return "", ()


def push_targets_main(args: tuple[str, ...], branch: str) -> bool:
    """Decide whether a `git push` would write to the protected branch.

    Args:
        args: Arguments following `push`.
        branch: The branch that will be checked out when the push runs.

    Returns:
        True if the push would update `main` on the remote.
    """
    if {"--all", "--mirror"} & set(args):
        return True

    positional: list[str] = []
    index = 0
    while index < len(args):
        argument = args[index]
        if argument in PUSH_OPTIONS_WITH_VALUE:
            index += 2  # the option and its value, which is not the remote
            continue
        if argument.startswith("-"):
            index += 1
            continue
        positional.append(argument)
        index += 1

    refspecs = positional[1:]  # the first positional is the remote
    if not refspecs:
        return branch == PROTECTED

    for spec in refspecs:
        destination = _branch_name(spec)
        if destination == PROTECTED:
            return True
        if destination == "HEAD" and branch == PROTECTED:
            return True
    return False


def switch_target(subcommand: str, args: tuple[str, ...]) -> str:
    """Name the branch a `checkout` or `switch` moves to.

    Args:
        subcommand: The git subcommand, as returned by `git_subcommand`.
        args: The arguments following it.

    Returns:
        The branch name, reduced by `_branch_name`; an empty string when the
        invocation does not move HEAD to a named branch, as `git checkout --
        file` restores a file and every other subcommand leaves the branch
        alone; or `UNRESOLVED` when the target is one only the running shell
        can resolve: `-`, `@{-1}`, or a word a command substitution made, and
        for `-B` and `-C` the name they take, which may be an existing branch.
    """
    if subcommand not in SWITCH_SUBCOMMANDS:
        return ""

    index = 0
    while index < len(args):
        argument = args[index]
        if argument == "--":
            return ""
        if argument in UNRESOLVABLE_TARGETS:
            return UNRESOLVED
        if argument in NEW_BRANCH_OPTIONS:
            if index + 1 >= len(args):
                return ""
            name = args[index + 1]
            # A name made by a substitution still leaves the branch, and `-b`
            # cannot land on one that exists; `-B` and `-C` can.
            if _PLACEHOLDER in name and argument in ("-B", "-C"):
                return UNRESOLVED
            return _branch_name(name)
        if argument.startswith("-"):
            index += 1
            continue
        return UNRESOLVED if _PLACEHOLDER in argument else _branch_name(argument)
    return ""


def _unreadable(command: str, branch: str) -> str:
    """Refuse a command this guard could not read, if it names a risky one.

    Args:
        command: The full command line.
        branch: The branch currently checked out.

    Returns:
        The refusal while `main` is checked out and the command names `commit`
        or `push`; an empty string anywhere else, where unreadable input is
        allowed.
    """
    if branch == PROTECTED and RISKY_PATTERN.search(command):
        return (
            "Refused: this command could not be read — an unbalanced quote, "
            f"most likely — and it names `commit` or `push` while `{PROTECTED}` "
            "is checked out.\n"
            "Rewrite it so the quoting is balanced, or move onto a branch "
            "first:\n"
            "    git checkout -b <type>/<kebab-case-topic>"
        )
    return ""


def violation(command: str, branch: str) -> str:
    """Find the reason to refuse this command, if there is one.

    Args:
        command: The full command line.
        branch: The branch currently checked out.

    Returns:
        An explanation to show Claude, or an empty string to allow the command.
        With `main` checked out, a command that names `commit` or `push` and
        uses syntax this guard does not read -- see `UNMODELLED_OPENERS` -- is
        refused with a reason saying so. A `commit` or `push` is otherwise
        refused when `main` is among the branches it may run on. A command the
        guard fails on, whatever the failure, is treated as unreadable.
    """
    try:
        return _judge(command, branch)
    except Exception:  # a hook that crashes lets the command run
        return _unreadable(command, branch)


#: Separators a bash `done` never follows: it ends a list, so it comes after `;`,
#: a newline or `&`. After `|` it is a case pattern.
_NOT_BEFORE_DONE = frozenset({"|", "||", "&&", "(", "{", ")", "}"})

#: Loop words PowerShell spells in any case; bash spells them in lower case only.
_POWERSHELL_LOOPS = frozenset({"foreach", "for", "while"})


def _quoted_done(text: str) -> bool:
    r"""Report whether a word that reads `done` once unquoted is written with quotes.

    A tokenizer drops the quotes, so `"done"` and `\done` look like the
    reserved word that closes a loop; the prepared text still has them.

    Args:
        text: The command after `_prepare`.

    Returns:
        True if some word holds a quote or a backslash and reads `done` without.
    """
    for word in re.findall(r"[^\s;&|()<>{}]+", text):
        if re.search(r"['\"\\]", word) and re.sub(r"['\"\\]", "", word) == "done":
            return True
    return False


def _loop_ranges(
    parsed: list[Segment], quoted_done: bool = False
) -> dict[int, set[str]]:
    """Find the loops in a command and the branches switched to inside each.

    A switch late in a loop body governs the next iteration, so every switch
    inside a loop counts for the whole loop. Bash loops run from `for`,
    `select`, `while` or `until` to the matching `done`; PowerShell loops --
    `foreach`, or a `do` before a `{` -- run to the end of the command. A start
    with no `done` runs to the end, and a `done` with no start is ignored. A
    `done` closes a loop only where the shell reads one: not after `|`, not in
    front of a case pattern's `)`, and not at all when the command writes a
    quoted `done` -- it cannot be told apart, so every loop then runs on. The
    keywords of PowerShell's loops match in any case, and a lone `do` before a
    `{` inside a bash loop is bash's own.

    Args:
        parsed: The invocations of the command, in order.
        quoted_done: Whether the command writes `done` with quotes or a
            backslash, as `_quoted_done` finds.

    Returns:
        For the first invocation of each loop -- that of its condition's
        substitutions, when it has any -- the branches switched to anywhere in
        the loop.
    """
    last = len(parsed) - 1
    ranges: list[tuple[int, int]] = []
    open_loops: list[int] = []
    for index, segment in enumerate(parsed):
        tokens = segment.tokens
        name = _command_index(tokens)
        word = tokens[name] if name < len(tokens) else ""
        leaders = _walk_prefix(tokens)[1]
        following = parsed[index + 1] if index < last else None
        if tokens[:1] == ("done",):
            pattern = following is not None and following.separator == ")"
            if (
                open_loops
                and not quoted_done
                and not pattern
                and segment.separator not in _NOT_BEFORE_DONE
            ):
                ranges.append((open_loops.pop(), index))
        elif word in _LOOP_COMMANDS or _LOOP_LEADERS.intersection(leaders):
            open_loops.append(index)
        elif (
            (word != word.lower() and word.lower() in _POWERSHELL_LOOPS)
            or word.lower() == "foreach"
            or (
                len(tokens) == 1
                and tokens[0].lower() == "do"
                and not open_loops
                and following is not None
                and following.separator == "{"
            )
        ):
            ranges.append((index, last))
    ranges.extend((start, last) for start in open_loops)

    widened: dict[int, set[str]] = {}
    for start, end in ranges:
        first = start
        while first > 0 and parsed[first - 1].depth > parsed[start].depth:
            first -= 1
        targets = widened.setdefault(first, set())
        for segment in parsed[first : end + 1]:
            subcommand, args = git_subcommand(segment.tokens)
            target = switch_target(subcommand, args)
            if target and not _redirected(segment.tokens):
                targets.add(target)
    return widened


def _walk_run(
    run: tuple[str, ...],
    level: int,
    ok: set[str],
    nest: dict[int, int],
    operands: list[tuple[_Key, set[str]]],
    negating: set[_Key],
) -> set[str]:
    """Read one run of operators for the `||` operands and `!` scopes it ends.

    A list ends at `&&`, `;`, `&` or a newline, and a group's close ends every
    list opened inside it. Only the ones at the key they were opened at end: an
    operator inside a substitution or a deeper group is another list's.

    Args:
        run: The operators between two invocations, in written order.
        level: The substitution depth the run belongs to.
        ok: The branches HEAD could be on if every command of the current `&&`
            chain succeeded.
        nest: How many groups are open at each level; updated.
        operands: The `||` operands being read, with what their left side
            trusted; entries are added and removed.
        negating: The lists a `!` or `coproc` leads; keys are removed.

    Returns:
        The branches the operands that ended trusted on their left side, for the
        caller to add to `ok`.
    """
    widened: set[str] = set()
    only_newlines = all(operator == "\n" for operator in run)

    def close(at: int, group: int, *, below: bool) -> None:
        # Ends what was opened at `group` -- or, for a close, in any group
        # deeper than it -- on this level.
        def ended(key: _Key) -> bool:
            return key[0] == at and (key[1] > group if below else key[1] == group)

        for entry in [e for e in operands if ended(e[0])]:
            operands.remove(entry)
            widened.update(entry[1])
        negating.difference_update([k for k in negating if ended(k)])

    for operator in run:
        group = nest.get(level, 0)
        key = (level, group)
        if operator == "||":
            if operands and operands[-1][0] == key:
                operands[-1][1].update(ok)  # chained: a || b || c
            else:
                operands.append((key, set(ok)))
        elif operator in _LIST_ENDS and (operator != "\n" or only_newlines):
            close(level, group, below=False)
        elif operator in ("(", "{"):
            nest[level] = group + 1
        elif operator in (")", "}"):
            left = max(group - 1, 0)
            close(level, left, below=True)
            nest[level] = left
    return widened


def _judge(command: str, branch: str) -> str:
    """Judge a command; `violation` is this with the failures caught.

    Args:
        command: The full command line.
        branch: The branch currently checked out.

    Returns:
        What `violation` returns.
    """
    prepared, unmodelled = _prepare(command)
    if unmodelled and branch == PROTECTED and RISKY_PATTERN.search(command):
        return (
            "Refused: this command uses syntax this guard does not read — "
            "`$'...'`, a bash 5.3 `${ cmd; }`, a PowerShell here-string, "
            "block comment or backtick-escaped quote — and it names `commit` or `push` while "
            f"`{PROTECTED}` is checked out.\n"
            "Rewrite it without that syntax, or move onto a branch first:\n"
            "    git checkout -b <type>/<kebab-case-topic>"
        )

    runs: list[tuple[str, ...]] = []
    parsed = _segments(command, runs=runs)
    if parsed is None:
        return _unreadable(command, branch)

    # `ok` is every branch HEAD could be on if each command of the current `&&`
    # chain succeeded, `possible` every branch it could be on at all. Only a
    # switch that an `&&` guards replaces `ok`, and not one on the right of an
    # `||`, which runs only when its left side failed: when that operand ends,
    # `ok` takes in what the left side trusted too. The others only widen
    # `possible`.
    ok = {branch}
    possible = {branch}
    # One frame per substitution being run: the branches the containing command
    # could start on, and the branches the substitution has switched to.
    frames: list[tuple[set[str], set[str]]] = []
    loops = _loop_ranges(parsed, _quoted_done(prepared))
    # Open `||` operands, each with what its left side trusted, and the lists a
    # `!` or `coproc` leads, both keyed by where the list sits: its substitution
    # depth and how many groups are open there. Only an operator at that key ends
    # one, or the group or substitution it sits in closing.
    nest: dict[int, int] = {}
    operands: list[tuple[_Key, set[str]]] = []
    negating: set[_Key] = set()
    previous_depth = 0
    for number, segment in enumerate(parsed):
        for level in [level for level in nest if level > segment.depth]:
            del nest[level]
        negating.difference_update([k for k in negating if k[0] > segment.depth])
        while operands and operands[-1][0][0] > segment.depth:
            ok |= operands.pop()[1]  # a substitution that has ended
        run = runs[number] if number < len(runs) else ()
        ok |= _walk_run(
            run, min(segment.depth, previous_depth), ok, nest, operands, negating
        )
        previous_depth = segment.depth
        if number in loops:
            ok |= loops[number]
            possible |= loops[number]
        popped: tuple[set[str], set[str]] | None = None
        while len(frames) > segment.depth:
            context, targets = frames.pop()
            popped = (context, targets | (popped[1] if popped else set()))
        if segment.separator == SUBSTITUTED and popped is not None:
            # The command containing the substitutions that just ran, started on
            # wherever they left HEAD.
            here = popped[0] | popped[1]
        elif segment.separator == SUBSTITUTED and frames:
            here = frames[-1][0] | frames[-1][1]  # the next substitution in a row
        else:
            here = set(ok if segment.separator == GUARANTEEING else possible)
        while len(frames) < segment.depth:
            frames.append((set(here), set()))

        subcommand, args = git_subcommand(segment.tokens)
        if subcommand == "commit" and PROTECTED in here:
            return (
                f"Refused: this would commit to `{PROTECTED}`, which this repo "
                "never commits to directly.\n"
                "Move the work onto a branch first, keeping the changes:\n"
                "    git checkout -b <type>/<kebab-case-topic>\n"
                "Prefixes: feat, fix, refactor, docs, test, chore."
            )
        if subcommand == "push" and any(push_targets_main(args, b) for b in here):
            return (
                f"Refused: this would push to `{PROTECTED}`, which is protected "
                "on the remote and would be rejected anyway.\n"
                "Push the feature branch and open a pull request instead:\n"
                "    git push -u origin <branch>"
            )
        if subcommand in RISKY_SUBCOMMANDS and UNRESOLVED in here:
            return (
                f"Refused: this would run `git {subcommand}` after a branch switch "
                "whose target only the running shell can resolve, so which branch "
                "it would land on cannot be determined here.\n"
                "Name the branch instead:\n"
                f"    git checkout <branch> && git {subcommand} ..."
            )

        target = switch_target(subcommand, args)
        if target and not _redirected(segment.tokens):
            # What `!` negates and `coproc` backgrounds leaves the `&&` after it
            # unsure whether the switch happened.
            unsure = bool(negating) or _leads_uncertainly(segment.tokens)
            ok = here | {target} if unsure else {target}
            possible.add(target)
            for _, targets in frames:
                targets.add(target)
        else:
            ok = set(here)
        if _leads_uncertainly(segment.tokens):
            negating.add((segment.depth, nest.get(segment.depth, 0)))

    return ""


def main() -> None:
    """Allow or refuse the Bash or PowerShell command about to run."""
    # lstrip the BOM: some shells prepend one when piping to a native command.
    raw = sys.stdin.read().lstrip("﻿").strip()
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        sys.exit(0)  # never block on a payload we cannot read

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        sys.exit(0)
    command = tool_input.get("command")
    if not isinstance(command, str) or "git" not in command:
        sys.exit(0)

    project_dir = Path(payload.get("cwd") or Path.cwd())
    reason = violation(command, current_branch(project_dir))
    if reason:
        print(reason, file=sys.stderr)
        sys.exit(2)  # exit 2 blocks the tool call and shows Claude the reason

    sys.exit(0)


if __name__ == "__main__":
    main()
