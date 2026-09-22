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

Each segment is judged against the branch that will be checked out when it runs,
not the one checked out now: `git checkout -b feat/x && git commit` is allowed
from `main`, because `&&` runs its right side only if the switch succeeded. No
other separator carries that guarantee — after `;` or a newline the commit runs
whether the switch worked or not — so across those the branch is taken as it is
now.

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

A push's destination is read with the same care: the arguments are walked rather
than filtered, so an option's value is never mistaken for the remote, and every
ref is reduced to the branch it names. A switch whose target only the running
shell can resolve leaves the branch unknown rather than unchanged, and a
`commit` or `push` that meets an unknown branch is refused with a message saying
so rather than the one about `main`.

Stdlib only: `jq` is not available on this machine and hook commands default to
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

#: Characters `shlex` emits as tokens of their own rather than folding into a
#: word. The default set plus the newline, which would otherwise be whitespace
#: and would silently join two commands written on two lines into one.
PUNCTUATION_CHARS = "();<>|&\n"

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
SEPARATOR_CHARS = frozenset("&|;\n(){}")

#: The one separator whose right side runs only if its left side succeeded, so
#: a branch switch before it can be trusted to have taken effect.
GUARANTEEING = "&&"

#: Stands for one or more newlines between invocations. Separates them, but
#: guarantees nothing about whether the one before it succeeded.
NEWLINE = "\n"

#: Git options that swallow the next token, hiding the subcommand behind them.
OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--exec-path"}

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


@dataclass(frozen=True)
class Segment:
    """One invocation within a compound command.

    Attributes:
        tokens: The invocation's tokens, with quoting already resolved.
        separator: The separator that preceded it — one of `SEPARATORS`,
            `NEWLINE`, or a grouping delimiter such as `(`. Empty for the first
            invocation in the command.
    """

    tokens: tuple[str, ...]
    separator: str


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
    """Remove the backticks that wrap a command substitution.

    `$( )` needs no equivalent: `(` is a separator, so the invocation inside
    already becomes a segment of its own.

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
        The branch name: substitution backticks removed, a leading `+`
        dropped, the destination half of a `src:dst` pair, `refs/heads/`
        stripped, and `@` read as `HEAD`. A closing backtick rides on the last
        token of a substitution, so a refspec can carry one.
    """
    name = _strip_substitution(ref).lstrip("+").split(":")[-1]
    name = name.removeprefix("refs/heads/")
    return "HEAD" if name == "@" else name


def _command_index(tokens: tuple[str, ...]) -> int:
    """Find where a command's name starts, after the prefix a shell skips.

    A simple command is a run of variable assignments and redirections, then
    the name. Wrapper programs are stepped over too: they are not shell syntax,
    but they run their argument as a command, so the name behind one is the
    name that matters.

    Args:
        tokens: The invocation's tokens.

    Returns:
        The index of the command name, or `len(tokens)` when the invocation is
        prefix and nothing else.
    """
    index = 0
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
        return index
    return len(tokens)


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


def segments(command: str) -> list[Segment] | None:
    """Split a shell command into its individual invocations.

    Args:
        command: The full command line the Bash tool is about to run.

    Returns:
        One segment per invocation, in order, or None if the command could not
        be read at all — an unbalanced quote, most often.
    """
    lexer = shlex.shlex(command, posix=True, punctuation_chars=PUNCTUATION_CHARS)
    lexer.whitespace_split = True
    lexer.whitespace = INLINE_WHITESPACE
    # `shlex` comments out the rest of the line from a bare `#`, even inside a
    # word, which silently discarded everything after `echo ok#1 &&`.
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        return None

    parsed: list[Segment] = []
    current: list[str] = []
    pending: list[str] = []
    separator = ""

    for token in tokens:
        if _is_separator(token):
            if current:
                parsed.append(Segment(tokens=tuple(current), separator=separator))
                current = []
                pending = []
            pending.append(_governs(token))
            separator = _join(pending)
            continue
        current.append(token)

    if current:
        parsed.append(Segment(tokens=tuple(current), separator=separator))
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
        can resolve, such as `-` or `@{-1}`.
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
            return _branch_name(args[index + 1]) if index + 1 < len(args) else ""
        if argument.startswith("-"):
            index += 1
            continue
        return _branch_name(argument)
    return ""


def violation(command: str, branch: str) -> str:
    """Find the reason to refuse this command, if there is one.

    Args:
        command: The full command line.
        branch: The branch currently checked out.

    Returns:
        An explanation to show Claude, or an empty string to allow the command.
    """
    parsed = segments(command)
    if parsed is None:
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

    effective = branch
    for segment in parsed:
        if segment.separator != GUARANTEEING:
            effective = branch  # the switch before this one may not have run

        subcommand, args = git_subcommand(segment.tokens)
        if subcommand in RISKY_SUBCOMMANDS and effective == UNRESOLVED:
            return (
                f"Refused: this would run `git {subcommand}` after a branch switch "
                "whose target only the running shell can resolve, so which branch "
                "it would land on cannot be determined here.\n"
                "Name the branch instead:\n"
                f"    git checkout <branch> && git {subcommand} ..."
            )
        if subcommand == "commit" and effective == PROTECTED:
            return (
                f"Refused: this would commit to `{PROTECTED}`, which this repo "
                "never commits to directly.\n"
                "Move the work onto a branch first, keeping the changes:\n"
                "    git checkout -b <type>/<kebab-case-topic>\n"
                "Prefixes: feat, fix, refactor, docs, test, chore."
            )
        if subcommand == "push" and push_targets_main(args, effective):
            return (
                f"Refused: this would push to `{PROTECTED}`, which is protected "
                "on the remote and would be rejected anyway.\n"
                "Push the feature branch and open a pull request instead:\n"
                "    git push -u origin <branch>"
            )

        target = switch_target(subcommand, args)
        if target and not _redirected(segment.tokens):
            effective = target

    return ""


def main() -> None:
    """Allow or refuse the Bash command about to run."""
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
