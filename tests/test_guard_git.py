import io
import json
import subprocess
from pathlib import Path

import guard_git
import pytest
from guard_git import (
    PROTECTED,
    SUBSTITUTED,
    UNRESOLVED,
    Segment,
    git_subcommand,
    push_targets_main,
    segments,
    switch_target,
    violation,
)

OTHER = "feat/topic"


def refused(command: str, branch: str) -> bool:
    return bool(violation(command, branch))


# --- Segment -----------------------------------------------------------------


def test_segment_is_frozen() -> None:
    segment = Segment(tokens=("git", "status"), separator="")

    with pytest.raises(AttributeError):
        segment.separator = "&&"  # type: ignore[misc]  # frozen by design


def test_segment_keeps_its_tokens_and_separator() -> None:
    segment = Segment(tokens=("git", "push"), separator="&&")

    assert segment.tokens == ("git", "push")
    assert segment.separator == "&&"


# --- segments ----------------------------------------------------------------


def test_segments_returns_one_segment_for_a_simple_command() -> None:
    assert segments("git status") == [Segment(tokens=("git", "status"), separator="")]


def test_segments_is_empty_for_an_empty_command() -> None:
    assert segments("") == []


def test_segments_is_empty_for_whitespace_only() -> None:
    assert segments("   \t  ") == []


@pytest.mark.parametrize("separator", ["&&", "||", ";", "|", "&"])
def test_segments_splits_on_every_separator(separator: str) -> None:
    parsed = segments(f"git status {separator} git log")

    assert parsed is not None
    assert [segment.tokens for segment in parsed] == [("git", "status"), ("git", "log")]
    assert parsed[1].separator == separator


def test_segments_splits_a_separator_glued_to_a_word() -> None:
    parsed = segments('git commit -m "a";git push')

    assert parsed is not None
    assert [segment.tokens for segment in parsed] == [
        ("git", "commit", "-m", "a"),
        ("git", "push"),
    ]


@pytest.mark.parametrize("punctuation", [";", "|", "&&", "||"])
def test_segments_keeps_punctuation_inside_a_quoted_argument(punctuation: str) -> None:
    parsed = segments(f'git commit -m "before {punctuation} after"')

    assert parsed == [
        Segment(
            tokens=("git", "commit", "-m", f"before {punctuation} after"), separator=""
        )
    ]


def test_segments_treats_a_newline_as_a_separator() -> None:
    parsed = segments('git checkout -b x\ngit commit -m "y"')

    assert parsed is not None
    assert len(parsed) == 2
    assert parsed[1].separator == "\n"


def test_segments_collapses_a_run_of_newlines_into_one_separator() -> None:
    parsed = segments("git status\n\n\ngit log")

    assert parsed is not None
    assert len(parsed) == 2
    assert parsed[1].separator == "\n"


def test_segments_keeps_a_newline_inside_a_quoted_message() -> None:
    parsed = segments('git commit -m "first\nsecond"')

    assert parsed == [
        Segment(tokens=("git", "commit", "-m", "first\nsecond"), separator="")
    ]


def test_segments_keeps_the_guarantee_when_and_is_split_across_lines() -> None:
    parsed = segments("git checkout -b x &&\ngit commit -m 'y'")

    assert parsed is not None
    assert parsed[1].separator == "&&"


def test_segments_returns_none_for_an_unbalanced_quote() -> None:
    assert segments('git commit -m "unbalanced') is None


def test_segments_is_idempotent() -> None:
    command = 'git checkout -b x && git commit -m "a; b"'

    assert segments(command) == segments(command)


def test_segments_handles_a_non_ascii_message() -> None:
    parsed = segments('git commit -m "café — naïve ✅"')

    assert parsed == [
        Segment(tokens=("git", "commit", "-m", "café — naïve ✅"), separator="")
    ]


def test_segments_handles_a_very_long_message() -> None:
    message = "x" * 10_000
    parsed = segments(f'git commit -m "{message}"')

    assert parsed is not None
    assert parsed[0].tokens[-1] == message


# --- git_subcommand ----------------------------------------------------------


def test_git_subcommand_finds_the_subcommand_and_its_arguments() -> None:
    assert git_subcommand(("git", "push", "origin", "main")) == (
        "push",
        ("origin", "main"),
    )


def test_git_subcommand_is_empty_for_a_non_git_invocation() -> None:
    assert git_subcommand(("ls", "-la")) == ("", ())


def test_git_subcommand_is_empty_for_no_tokens() -> None:
    assert git_subcommand(()) == ("", ())


def test_git_subcommand_is_empty_for_git_with_no_subcommand() -> None:
    assert git_subcommand(("git",)) == ("", ())


@pytest.mark.parametrize("executable", ["git", "git.exe", "/usr/bin/git"])
def test_git_subcommand_accepts_git_however_it_is_spelled(executable: str) -> None:
    assert git_subcommand((executable, "commit"))[0] == "commit"


@pytest.mark.parametrize(
    "option", ["-C", "-c", "--git-dir", "--work-tree", "--exec-path"]
)
def test_git_subcommand_steps_over_an_option_and_its_value(option: str) -> None:
    assert git_subcommand(("git", option, "value", "commit"))[0] == "commit"


def test_git_subcommand_steps_over_a_valueless_option() -> None:
    assert git_subcommand(("git", "--no-pager", "commit"))[0] == "commit"


# --- push_targets_main -------------------------------------------------------


def test_push_targets_main_for_a_bare_push_on_main() -> None:
    assert push_targets_main((), PROTECTED) is True


def test_push_targets_main_is_false_for_a_bare_push_elsewhere() -> None:
    assert push_targets_main((), OTHER) is False


@pytest.mark.parametrize(
    "refspec",
    ["main", "HEAD:main", "refs/heads/main", "+main", "main:main", "+refs/heads/main"],
)
def test_push_targets_main_recognises_every_refspec_shape(refspec: str) -> None:
    assert push_targets_main(("origin", refspec), OTHER) is True


@pytest.mark.parametrize("option", ["--all", "--mirror"])
def test_push_targets_main_for_options_that_push_everything(option: str) -> None:
    assert push_targets_main((option, "origin"), OTHER) is True


def test_push_targets_main_is_false_for_a_feature_refspec() -> None:
    assert push_targets_main(("-u", "origin", OTHER), OTHER) is False


def test_push_targets_main_follows_head_to_the_current_branch() -> None:
    assert push_targets_main(("origin", "HEAD"), PROTECTED) is True
    assert push_targets_main(("origin", "HEAD"), OTHER) is False


def test_push_targets_main_ignores_a_branch_merely_named_like_main() -> None:
    assert push_targets_main(("origin", "maintenance"), OTHER) is False


# --- switch_target -----------------------------------------------------------


@pytest.mark.parametrize("option", ["-b", "-B"])
def test_switch_target_reads_a_new_branch_from_checkout(option: str) -> None:
    assert switch_target("checkout", (option, "feat/x")) == "feat/x"


@pytest.mark.parametrize("option", ["-c", "-C"])
def test_switch_target_reads_a_new_branch_from_switch(option: str) -> None:
    assert switch_target("switch", (option, "feat/x")) == "feat/x"


def test_switch_target_reads_an_existing_branch() -> None:
    assert switch_target("checkout", ("main",)) == PROTECTED


def test_switch_target_skips_options_before_the_branch() -> None:
    assert switch_target("checkout", ("--quiet", "feat/x")) == "feat/x"


def test_switch_target_is_empty_for_a_file_restore() -> None:
    assert switch_target("checkout", ("--", "file.py")) == ""


def test_switch_target_is_empty_for_another_subcommand() -> None:
    assert switch_target("commit", ("-m", "message")) == ""


def test_switch_target_is_empty_without_arguments() -> None:
    assert switch_target("checkout", ()) == ""


def test_switch_target_is_empty_when_the_option_has_no_value() -> None:
    assert switch_target("checkout", ("-b",)) == ""


# --- violation: punctuation inside a quoted commit message --------------------


@pytest.mark.parametrize(
    "message",
    [
        "Add parser; drop the old one",
        "Handle a|b correctly",
        "Fix && polish",
        "Either || or",
        "Background & foreground",
        "first line\nsecond line",
    ],
)
def test_violation_refuses_a_commit_whose_message_carries_punctuation(
    message: str,
) -> None:
    assert refused(f'git commit -m "{message}"', PROTECTED)


def test_violation_allows_those_same_commits_off_main() -> None:
    assert not refused('git commit -m "Add parser; drop the old one"', OTHER)


# --- violation: branch switches ----------------------------------------------


@pytest.mark.parametrize("switch", ["checkout -b", "checkout -B", "switch -c"])
def test_violation_allows_a_commit_after_a_guaranteed_switch_away(switch: str) -> None:
    assert not refused(f'git {switch} feat/x && git commit -m "m"', PROTECTED)


def test_violation_refuses_a_commit_after_a_switch_to_main() -> None:
    assert refused('git checkout main && git commit -m "m"', OTHER)


def test_violation_refuses_a_push_after_a_switch_to_main() -> None:
    assert refused("git checkout main && git push", OTHER)


@pytest.mark.parametrize("separator", [";", "||", "&", "\n"])
def test_violation_distrusts_a_switch_that_may_not_have_run(separator: str) -> None:
    command = f'git checkout -b feat/x {separator} git commit -m "m"'

    assert refused(command, PROTECTED)


def test_violation_trusts_a_switch_joined_across_lines_by_and() -> None:
    assert not refused('git checkout -b feat/x &&\ngit commit -m "m"', PROTECTED)


def test_violation_resets_the_branch_after_a_weak_separator() -> None:
    command = 'git checkout -b feat/x && git status ; git commit -m "m"'

    assert refused(command, PROTECTED)


def test_violation_carries_a_switch_through_an_intervening_command() -> None:
    command = 'git checkout -b feat/x && git status && git commit -m "m"'

    assert not refused(command, PROTECTED)


# --- violation: unreadable input ---------------------------------------------


@pytest.mark.parametrize("word", ["commit", "push"])
def test_violation_refuses_unreadable_input_naming_a_risky_subcommand(
    word: str,
) -> None:
    reason = violation(f'git {word} -m "unbalanced', PROTECTED)

    assert "could not be read" in reason


def test_violation_allows_unreadable_input_off_main() -> None:
    assert not refused('git commit -m "unbalanced', OTHER)


def test_violation_allows_unreadable_input_naming_nothing_risky() -> None:
    assert not refused('echo "unbalanced', PROTECTED)


# --- violation: everything that already held ---------------------------------


def test_violation_refuses_a_plain_commit_on_main() -> None:
    assert refused('git commit -m "Add the parser"', PROTECTED)


def test_violation_allows_a_plain_commit_off_main() -> None:
    assert not refused('git commit -m "Add the parser"', OTHER)


def test_violation_refuses_a_commit_reached_through_a_directory_option() -> None:
    assert refused('git -C /somewhere commit -m "m"', PROTECTED)


@pytest.mark.parametrize(
    "command",
    [
        "git push",
        "git push origin main",
        "git push origin HEAD:main",
        "git push origin refs/heads/main",
        "git push origin +main",
        "git push --all",
        "git push --mirror",
    ],
)
def test_violation_refuses_every_push_that_would_reach_main(command: str) -> None:
    assert refused(command, PROTECTED)


def test_violation_allows_pushing_a_feature_branch() -> None:
    assert not refused(f"git push -u origin {OTHER}", OTHER)


@pytest.mark.parametrize("command", ["ls -la", "echo hello", "python -m pytest", ""])
def test_violation_ignores_commands_that_are_not_git(command: str) -> None:
    assert not refused(command, PROTECTED)


def test_violation_allows_a_redirection_on_a_harmless_subcommand() -> None:
    assert not refused("git log > out.txt", PROTECTED)


def test_violation_refuses_the_second_half_of_a_chain() -> None:
    assert refused('git status && git commit -m "m"', PROTECTED)


def test_violation_names_the_protected_branch_in_its_reason() -> None:
    assert PROTECTED in violation('git commit -m "m"', PROTECTED)


def test_violation_is_idempotent() -> None:
    command = 'git commit -m "a; b"'

    assert violation(command, PROTECTED) == violation(command, PROTECTED)


# --- violation: commands hidden behind grouping ------------------------------


@pytest.mark.parametrize(
    "command",
    [
        '(git commit -m "x")',
        '{ git commit -m "x"; }',
        '(cd sub && git commit -m "x")',
        "(git push origin main)",
    ],
)
def test_violation_sees_through_grouping_delimiters(command: str) -> None:
    assert refused(command, PROTECTED)


def test_violation_still_trusts_a_switch_inside_a_subshell() -> None:
    assert not refused('(git checkout -b feat/x && git commit -m "m")', PROTECTED)


# --- violation: separators glued to a newline --------------------------------


@pytest.mark.parametrize("separator", [";", "||", "&", "|"])
def test_violation_splits_a_separator_glued_to_a_newline(separator: str) -> None:
    assert refused(f"git status {separator}\ngit push origin main", PROTECTED)


def test_violation_refuses_a_commit_after_a_weak_separator_and_newline() -> None:
    assert refused('git checkout -b feat/x ;\ngit commit -m "m"', PROTECTED)


def test_violation_trusts_and_glued_to_a_newline() -> None:
    assert not refused('git checkout -b feat/x &&\ngit commit -m "m"', PROTECTED)


# --- violation: regressions found while the parser was rebuilt ---------------


@pytest.mark.parametrize(
    "command",
    [
        'echo ok#1 && git commit -m "m"',
        "git log --grep=#12 && git push origin main",
    ],
)
def test_violation_survives_an_unquoted_hash(command: str) -> None:
    assert refused(command, PROTECTED)


def test_segments_keeps_a_hash_inside_a_word() -> None:
    parsed = segments("echo ok#1 && git status")

    assert parsed is not None
    assert parsed[0].tokens == ("echo", "ok#1")


def test_violation_distrusts_a_switch_made_inside_a_subshell() -> None:
    assert refused('(git checkout -b feat/x) && git commit -m "m"', PROTECTED)


def test_violation_still_trusts_a_switch_sharing_the_subshell() -> None:
    assert not refused('(git checkout -b feat/x && git commit -m "m")', PROTECTED)


def test_violation_distrusts_a_switch_in_another_repository() -> None:
    command = 'git -C /other checkout -b feat/x && git commit -m "m"'

    assert refused(command, PROTECTED)


def test_violation_distrusts_a_switch_across_a_mixed_separator_run() -> None:
    assert refused('git checkout -b feat/x ; && git commit -m "m"', PROTECTED)


@pytest.mark.parametrize("word", ["committee", "pushover", "recommitted"])
def test_violation_does_not_read_a_longer_word_as_a_risky_subcommand(
    word: str,
) -> None:
    assert not refused(f'echo "this is about the {word}', PROTECTED)


def test_violation_still_refuses_unreadable_input_on_a_real_word() -> None:
    assert refused('git commit -m "unbalanced', PROTECTED)


# --- PowerShell syntax: the hook also runs for the PowerShell tool -----------

POWERSHELL_HERE_STRING_COMMIT = "git commit -m @'\nAdd parser\n\nWith a body line.\n'@"


@pytest.mark.parametrize(
    "command",
    [
        "git add -A; git commit -m 'Add parser'",
        "git status; if ($?) { git commit -m 'm' }",
        POWERSHELL_HERE_STRING_COMMIT,
        "git commit `\n  -m 'continued on the next line'",
        "$env:GIT_EDITOR = 'true'; git commit",
        "git checkout -b feat/x; git commit -m 'no && in PowerShell 5.1'",
    ],
)
def test_violation_refuses_powershell_commits_on_main(command: str) -> None:
    assert refused(command, PROTECTED)


@pytest.mark.parametrize(
    "command",
    [
        "git add -A; git commit -m 'Add parser'",
        "git status; if ($?) { git commit -m 'm' }",
        POWERSHELL_HERE_STRING_COMMIT,
        "git commit `\n  -m 'continued on the next line'",
        "$env:GIT_EDITOR = 'true'; git commit",
        "git push -u origin feat/x",
        "if ($?) { git push origin HEAD }",
    ],
)
def test_violation_allows_powershell_work_off_main(command: str) -> None:
    assert not refused(command, OTHER)


@pytest.mark.parametrize(
    "command",
    [
        "git status; if ($?) { git push origin main }",
        "git push origin HEAD:main",
    ],
)
def test_violation_refuses_powershell_pushes_to_main_from_anywhere(
    command: str,
) -> None:
    assert refused(command, OTHER)


# --- main: the hook's real entry point ---------------------------------------


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo_on_main(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-b", PROTECTED)
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "seed.txt").write_text("seed", encoding="utf-8")
    git(tmp_path, "add", "seed.txt")
    git(tmp_path, "commit", "-m", "seed")
    return tmp_path


def run_hook(monkeypatch: pytest.MonkeyPatch, payload: object) -> int | str | None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    with pytest.raises(SystemExit) as exit_info:
        guard_git.main()
    return exit_info.value.code


def test_main_blocks_a_commit_on_main(
    monkeypatch: pytest.MonkeyPatch,
    repo_on_main: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = {
        "tool_input": {"command": 'git commit -m "Add parser; drop the old one"'},
        "cwd": str(repo_on_main),
    }

    assert run_hook(monkeypatch, payload) == 2
    assert PROTECTED in capsys.readouterr().err


def test_main_allows_a_commit_after_branching(
    monkeypatch: pytest.MonkeyPatch, repo_on_main: Path
) -> None:
    payload = {
        "tool_input": {"command": 'git checkout -b feat/x && git commit -m "m"'},
        "cwd": str(repo_on_main),
    }

    assert run_hook(monkeypatch, payload) == 0


def test_main_allows_a_commit_off_main(
    monkeypatch: pytest.MonkeyPatch, repo_on_main: Path
) -> None:
    git(repo_on_main, "checkout", "-b", OTHER)
    payload = {
        "tool_input": {"command": 'git commit -m "m"'},
        "cwd": str(repo_on_main),
    }

    assert run_hook(monkeypatch, payload) == 0


def test_main_blocks_a_commit_on_main_from_powershell(
    monkeypatch: pytest.MonkeyPatch, repo_on_main: Path
) -> None:
    payload = {
        "tool_name": "PowerShell",
        "tool_input": {"command": "git add -A; git commit -m 'Add parser'"},
        "cwd": str(repo_on_main),
    }

    assert run_hook(monkeypatch, payload) == 2


def test_the_hook_is_registered_for_both_shell_tools() -> None:
    settings = json.loads(
        (Path(__file__).parents[1] / ".claude" / "settings.json").read_text(
            encoding="utf-8"
        )
    )
    matchers = [
        entry["matcher"]
        for entry in settings["hooks"]["PreToolUse"]
        if any("guard_git.py" in hook["command"] for hook in entry["hooks"])
    ]

    assert len(matchers) == 1
    assert set(matchers[0].split("|")) >= {"Bash", "PowerShell"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"tool_input": "not a dict"},
        {"tool_input": {}},
        {"tool_input": {"command": 42}},
        {"tool_input": {"command": "ls -la"}},
    ],
)
def test_main_allows_anything_it_cannot_read_as_a_git_command(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]
) -> None:
    assert run_hook(monkeypatch, payload) == 0


def test_main_allows_an_unparseable_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json"))

    with pytest.raises(SystemExit) as exit_info:
        guard_git.main()

    assert exit_info.value.code == 0


def test_main_tolerates_a_byte_order_mark(
    monkeypatch: pytest.MonkeyPatch, repo_on_main: Path
) -> None:
    payload = json.dumps(
        {"tool_input": {"command": 'git commit -m "m"'}, "cwd": str(repo_on_main)}
    )
    monkeypatch.setattr("sys.stdin", io.StringIO("﻿" + payload))

    with pytest.raises(SystemExit) as exit_info:
        guard_git.main()

    assert exit_info.value.code == 2


# =============================================================================
# Recognising the command
# =============================================================================


# --- a variable-assignment prefix --------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        'GIT_EDITOR=true git commit -m "m"',
        'GIT_EDITOR=true EDITOR=vi git commit -m "m"',
        'EMPTY= git commit -m "m"',
        'MSG="a; b" git commit -m "m"',
    ],
)
def test_violation_finds_a_commit_behind_an_assignment(command: str) -> None:
    assert refused(command, PROTECTED)


def test_violation_finds_a_push_behind_an_assignment() -> None:
    assert refused("GIT_SSH_COMMAND=ssh git push origin main", OTHER)


def test_violation_allows_an_assignment_prefixing_something_harmless() -> None:
    assert not refused("GIT_EDITOR=true git status", PROTECTED)


# --- a redirection prefix ----------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        '>log git commit -m "m"',
        '> log git commit -m "m"',
        '>>log git commit -m "m"',
        '2>&1 git commit -m "m"',
        '<in git commit -m "m"',
    ],
)
def test_violation_finds_a_commit_behind_a_redirection(command: str) -> None:
    assert refused(command, PROTECTED)


def test_violation_finds_a_commit_behind_both_prefixes() -> None:
    assert refused('GIT_EDITOR=true >log git commit -m "m"', PROTECTED)


# --- command substitution ----------------------------------------------------


def test_violation_finds_a_push_inside_backticks() -> None:
    assert refused("`git push origin main`", OTHER)


def test_violation_finds_a_commit_inside_backticks() -> None:
    assert refused('`git commit -m "m"`', PROTECTED)


def test_violation_finds_a_push_inside_a_dollar_substitution() -> None:
    assert refused("$(git push origin main)", OTHER)


# --- wrapper programs --------------------------------------------------------


@pytest.mark.parametrize("wrapper", ["sudo", "env", "time", "nohup", "doas"])
def test_violation_finds_a_push_under_each_wrapper(wrapper: str) -> None:
    assert refused(f"{wrapper} git push origin main", OTHER)


@pytest.mark.parametrize("wrapper", ["sudo", "env", "time", "nohup", "doas"])
def test_violation_finds_a_commit_under_each_wrapper(wrapper: str) -> None:
    assert refused(f'{wrapper} git commit -m "m"', PROTECTED)


def test_violation_steps_over_a_wrappers_own_flags() -> None:
    assert refused('sudo -n git commit -m "m"', PROTECTED)


def test_violation_misses_a_command_behind_a_wrapper_option_value() -> None:
    # Documented limit, not an oversight: only options are skipped after a
    # wrapper, never a bare word, because skipping a bare word is how a scan
    # walks onto a `git` that is an argument. `me` is read as the command name.
    # If this ever starts refusing, that is a decision to take deliberately.
    assert not refused("sudo -u me git push origin main", OTHER)


def test_violation_allows_a_wrapper_running_something_else() -> None:
    assert not refused("sudo apt install git", PROTECTED)


# --- how git is spelled ------------------------------------------------------


@pytest.mark.parametrize(
    "executable", ["GIT", "Git", "git.EXE", "Git.exe", "/usr/bin/GIT"]
)
def test_violation_matches_the_executable_without_regard_to_case(
    executable: str,
) -> None:
    assert refused(f'{executable} commit -m "m"', PROTECTED)


# --- refspec shapes ----------------------------------------------------------


@pytest.mark.parametrize(
    "option", ["-o", "--push-option", "--repo", "--receive-pack", "--exec"]
)
def test_violation_does_not_read_a_push_option_value_as_the_remote(
    option: str,
) -> None:
    assert refused(f"git push {option} value origin", PROTECTED)


def test_push_targets_main_skips_an_option_value() -> None:
    assert push_targets_main(("-o", "ci.skip", "origin"), PROTECTED) is True


@pytest.mark.parametrize("alias", ["@", "HEAD"])
def test_push_targets_main_follows_both_spellings_of_head(alias: str) -> None:
    assert push_targets_main(("origin", alias), PROTECTED) is True
    assert push_targets_main(("origin", alias), OTHER) is False


def test_violation_refuses_a_push_to_the_head_alias() -> None:
    assert refused("git push origin @", PROTECTED)


@pytest.mark.parametrize(
    "target", ["main", "refs/heads/main", "+refs/heads/main", "+main"]
)
def test_switch_target_reduces_a_ref_to_its_branch(target: str) -> None:
    assert switch_target("checkout", (target,)) == PROTECTED


def test_violation_refuses_a_commit_after_switching_to_main_by_full_ref() -> None:
    assert refused('git checkout refs/heads/main && git commit -m "m"', OTHER)


# --- a switch that cannot be resolved ----------------------------------------


@pytest.mark.parametrize("target", ["-", "@{-1}"])
def test_switch_target_reports_an_unresolvable_target(target: str) -> None:
    assert switch_target("checkout", (target,)) == UNRESOLVED
    assert switch_target("switch", (target,)) == UNRESOLVED


@pytest.mark.parametrize("branch", [PROTECTED, OTHER])
def test_violation_refuses_a_commit_after_an_unresolvable_switch(branch: str) -> None:
    assert refused('git checkout - && git commit -m "m"', branch)


def test_violation_refuses_a_push_after_an_unresolvable_switch() -> None:
    assert refused("git switch - && git push", OTHER)


def test_violation_says_the_branch_is_undetermined_rather_than_main() -> None:
    reason = violation('git checkout - && git commit -m "m"', OTHER)

    assert "cannot be determined" in reason
    assert "would commit to" not in reason


def test_violation_allows_a_harmless_command_after_an_unresolvable_switch() -> None:
    assert not refused("git checkout - && git status", OTHER)


def test_violation_refuses_after_an_unresolvable_switch_across_a_weak_join() -> None:
    # `;` does not guarantee the switch ran, so the branch is either one: the real
    # branch or whatever `-` names, which cannot be told from here.
    assert violation('git checkout - ; git commit -m "m"', OTHER).startswith(
        "Refused: this would run `git commit` after a branch switch"
    )


# --- the false positives command recognition must not introduce --------------


@pytest.mark.parametrize(
    "command",
    [
        "echo git commit",
        "echo git push origin main",
        "grep push log.txt",
        "git log --grep=commit",
        "sudo apt install git",
        "time ls",
        "cat commit.txt",
        "./scripts/git-commit-helper.sh",
        "git commit --dry-run --short",
    ],
)
def test_violation_allows_what_is_not_a_git_invocation(command: str) -> None:
    assert not refused(command, OTHER)


@pytest.mark.parametrize(
    "command",
    [
        "echo git commit",
        "grep push log.txt",
        "git log --grep=commit",
        "sudo apt install git",
        "time ls",
    ],
)
def test_violation_allows_those_same_commands_on_main(command: str) -> None:
    assert not refused(command, PROTECTED)


def test_violation_allows_a_commit_message_naming_git_and_sudo() -> None:
    assert not refused('git commit -m "run sudo git push by hand"', OTHER)


# --- shell lexing: heredocs, comments, continuations -------------------------


def test_violation_allows_a_heredoc_with_a_stray_quote_on_main() -> None:
    command = "python3 - <<'EOF'\nx = '''main's push'''\nEOF"

    assert not refused(command, PROTECTED)


COMMIT_REASON = "Refused: this would commit to `main`"
PUSH_REASON = "Refused: this would push to `main`"
UNMODELLED_REASON = "Refused: this command uses syntax this guard does not read"
UNREADABLE_REASON = "Refused: this command could not be read"


# --- heredocs ----------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "cat <<'EOF' > notes.txt\ngit commit -m x\nEOF",
        "cat <<EOF > notes.txt\ngit commit -m x\nEOF",
        'cat <<"EOF" > notes.txt\ngit commit -m x\nEOF',
        "cat <<\\EOF > notes.txt\ngit commit -m x\nEOF",
        "cat <<-EOF\n\tdon't push\n\tEOF",
        "cat <<EOF\nx\nEOF",
    ],
    ids=["single", "bare", "double", "backslash", "dash-tabs", "no-trailing-newline"],
)
def test_violation_reads_a_heredoc_body_as_data_in_every_delimiter_form(
    command: str,
) -> None:
    assert violation(command, PROTECTED) == ""


@pytest.mark.parametrize(
    "command",
    [
        "cat <<EOF > f\nhello\nEOF\ngit commit -m x",
        "cat <<A <<B\na\nA\nb\nB\ngit commit -m x",
        "cat <<EOF > f && git commit -m x\nbody\nEOF",
        "cat <<EOF # note\nit's\nEOF\ngit commit -m x # '",
        "cat <<EOF|grep x\nbody\nEOF\ngit commit -m x",
        "cat <<EOF;\nbody\nEOF\ngit commit -m x",
        'cat <<E"O"F\nx\nEOF\ngit commit -m x',
        "cat <<-\tEOF\n\tx\n\tEOF\ngit commit -m x",
    ],
    ids=[
        "after",
        "two-heredocs",
        "opener-line",
        "comment-on-opener",
        "pipe-ends-word",
        "semicolon-ends-word",
        "quoted-inside-word",
        "dash-then-blank",
    ],
)
def test_violation_still_judges_a_command_after_a_heredoc(command: str) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_refuses_a_heredoc_fed_commit_as_a_commit_not_as_unreadable() -> None:
    command = "git commit -F - <<'EOF'\nfix main's guard\nEOF"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)
    assert violation(command, OTHER) == ""


@pytest.mark.parametrize("branch", [PROTECTED, OTHER])
def test_violation_keeps_the_pipelines_own_commit_form(branch: str) -> None:
    command = "git commit -m \"$(cat <<'EOF'\nfix main's guard\n\nbody\nEOF\n)\""

    expected = COMMIT_REASON if branch == PROTECTED else ""
    assert violation(command, branch).startswith(expected)


def test_violation_closes_the_first_heredoc_on_the_first_delimiter() -> None:
    # Line 2 closes A and line 3 is B's body, so the commit is not run.
    command = "cat <<A; cat <<B\nB\nA\ngit commit -m x\nB"

    assert violation(command, PROTECTED) == ""


@pytest.mark.parametrize(
    "command",
    [
        "cat <<EOF\nE\\\nOF\ngit commit -m x\nEOF",
        "cat <<EOF\r\nhi\r\nEOF\r\ngit commit -m x\r\n",
    ],
    ids=["continuation-joins-delimiter", "crlf-word-includes-return"],
)
def test_violation_closes_a_heredoc_where_bash_does(command: str) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_gives_a_quoted_delimiter_no_line_joining() -> None:
    command = "cat <<'EOF'\nE\\\nOF\ngit commit -m x\nEOF"

    assert violation(command, PROTECTED) == ""


def test_violation_takes_the_rest_of_an_unterminated_heredoc_as_its_body() -> None:
    assert violation("cat <<EOF\nwill push later", PROTECTED) == ""
    assert violation("cat <<EOF\ngit commit -m x", PROTECTED) == ""


@pytest.mark.parametrize(
    "command",
    ["git push origin main; cat <<EOF", "git push origin main\ncat <<"],
)
def test_violation_keeps_a_push_that_runs_before_an_unterminated_heredoc(
    command: str,
) -> None:
    assert violation(command, OTHER).startswith(PUSH_REASON)


def test_segments_drops_the_body_of_a_heredoc_that_never_closes() -> None:
    assert segments("cat <<EOF\nbody") == [Segment(("cat", "<<", "EOF"), "")]


def test_segments_keeps_a_heredoc_operator_with_no_word_as_a_token() -> None:
    assert segments("cat <<-") == [Segment(("cat", "<<", "-"), "")]


def test_segments_returns_none_for_an_unclosed_quote_in_a_delimiter() -> None:
    assert segments("cat <<'EOF\nx") is None


def test_segments_keeps_a_lone_heredoc_operator_as_a_token() -> None:
    assert segments("cat << \ngit status") == [
        Segment(("cat", "<<"), ""),
        Segment(("git", "status"), "\n"),
    ]


def test_segments_drops_a_heredoc_body_but_keeps_its_operator_and_word() -> None:
    command = "cat <<'EOF' > notes.txt\ngit commit -m x\nEOF"

    assert segments(command) == [Segment(("cat", "<<", "EOF", ">", "notes.txt"), "")]


@pytest.mark.parametrize(
    "command",
    [
        "cat <<EOF\nx's\nEOF\nls",
        "cat <<'EOF'\nx's\nEOF\nls",
        'cat <<"EOF"\nx\'s\nEOF\nls',
        "cat <<\\EOF\nx's\nEOF\nls",
        "cat <<-EOF\n\tx's\n\tEOF\nls",
    ],
    ids=["bare", "single", "double", "backslash", "dash"],
)
def test_segments_resumes_after_each_heredoc_form(command: str) -> None:
    parsed = segments(command)

    assert parsed is not None
    assert len(parsed) == 2
    assert parsed[1] == Segment(("ls",), "\n")


def test_segments_does_not_strip_spaces_from_a_dash_heredoc_closing_line() -> None:
    # `<<-` strips tabs only, so the spaced EOF is body and the last one closes.
    assert segments("cat <<-EOF\n\tx\n  EOF\nEOF") == [
        Segment(("cat", "<<", "-EOF"), "")
    ]


def test_segments_reads_two_heredocs_on_one_line_in_order() -> None:
    assert segments("cat <<A; cat <<B\nB\nA\nx\nB") == [
        Segment(("cat", "<<", "A"), ""),
        Segment(("cat", "<<", "B"), ";"),
    ]


def test_segments_treats_a_triple_angle_as_a_here_string() -> None:
    parsed = segments("cat <<< hi\ngit status")

    assert parsed is not None
    assert parsed[-1] == Segment(("git", "status"), "\n")


def test_segments_does_not_read_a_here_string_as_a_heredoc() -> None:
    assert violation("cat <<< hi\ngit commit -m x", PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "echo $((1<<2)); git push origin main",
        "echo $((1 << 2)); git push origin main",
        "x=1; (( x <<= 1 )); git push origin main",
        'echo "$((1<<2))"; git push origin main',
        "let 'x=1<<2'; git push origin main",
    ],
    ids=["glued", "spaced", "command", "quoted", "let"],
)
def test_violation_reads_a_shift_as_arithmetic_not_as_a_heredoc(command: str) -> None:
    assert violation(command, OTHER).startswith(PUSH_REASON)
    assert violation(command, PROTECTED).startswith(PUSH_REASON)


def test_violation_reads_nested_subshells_that_look_like_arithmetic() -> None:
    assert violation("((echo a); git commit -m x)", PROTECTED).startswith(COMMIT_REASON)


# --- comments ----------------------------------------------------------------


def test_violation_refuses_a_commit_hidden_by_quotes_in_comments() -> None:
    command = "# it's fine\ngit commit -m x\n# that's it"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_allows_a_word_start_comment_naming_a_commit() -> None:
    assert violation("echo ok # git commit -m x", PROTECTED) == ""


def test_violation_keeps_a_hash_inside_a_word_live() -> None:
    assert violation("echo ok#1 && git commit -m m", PROTECTED).startswith(
        COMMIT_REASON
    )


@pytest.mark.parametrize(
    "command",
    [
        "echo a;# it's\ngit commit -m x # '",
        "echo a|# it's\ngit commit -m x # '",
        "echo a &# it's\ngit commit -m x # '",
        "(# it's\ngit commit -m x # ')",
        "{ # it's\ngit commit -m x # '; }",
        "echo a\t# it's\ngit commit -m x # '",
    ],
    ids=["semicolon", "pipe", "ampersand", "paren", "brace-blank", "tab"],
)
def test_violation_starts_a_comment_after_each_operator_and_blank(
    command: str,
) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "echo $(true)# ; git push origin main",
        "x=a; echo ${x/ #/}; git push origin main",
        "x=a; echo ${x:- #}; git push origin main",
        'echo "$(echo " #")"; git push origin main',
        "echo ok\r# ; git push origin main",
        "echo 'a'# ; git push origin main",
        "echo a\\ # ; git push origin main",
        "echo `echo a #`; git push origin main",
        "set -- a; echo $# ; git push origin main",
        "x=abc; echo ${#x}; git push origin main",
        "echo a=#b; git push origin main",
        "echo {a,b}#; git push origin main",
    ],
    ids=[
        "after-cmdsub",
        "in-param-expansion",
        "in-param-default",
        "nested-quotes",
        "after-return",
        "after-single-quote",
        "after-escaped-blank",
        "inside-backticks",
        "dollar-hash",
        "length-expansion",
        "after-equals",
        "after-brace-expansion",
    ],
)
def test_violation_reads_a_hash_that_bash_keeps_in_a_word_as_text(
    command: str,
) -> None:
    assert violation(command, OTHER).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "(echo a)# ; git push origin main",
        "echo a >#x\ngit push origin main",
        "echo ##a; git push origin main",
    ],
    ids=["after-subshell", "after-redirect", "double-hash"],
)
def test_violation_comments_out_what_bash_does_after_a_closing_paren_or_redirect(
    command: str,
) -> None:
    assert violation(command, OTHER) == ""


def test_violation_ends_a_comment_inside_backticks_at_the_backtick() -> None:
    assert violation("echo `echo a # c`; git commit -m x", PROTECTED).startswith(
        COMMIT_REASON
    )


def test_violation_comments_inside_a_substitution_run_to_the_line_end() -> None:
    command = "echo $(echo a # it's\n); git push origin main"

    assert violation(command, OTHER).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    ["git commit -m '# not a comment'", 'git commit -m "# not a comment"'],
)
def test_violation_reads_a_hash_inside_quotes_as_text(command: str) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_distrusts_a_switch_whose_and_is_only_in_a_comment() -> None:
    command = "git checkout -b feat/x # &&\ngit commit -m x"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_segments_drops_a_word_start_comment_and_keeps_its_newline() -> None:
    assert segments("echo ok # it's\ngit status") == [
        Segment(("echo", "ok"), ""),
        Segment(("git", "status"), "\n"),
    ]


def test_segments_keeps_the_commands_after_a_closing_substitution_hash() -> None:
    parsed = segments("echo $(true)# ; git status")

    assert parsed is not None
    assert parsed[-1] == Segment(("git", "status"), ";")


@pytest.mark.parametrize("command", ["", "   ", "\n\n", "\\\n", "# only a comment"])
@pytest.mark.parametrize("branch", [PROTECTED, OTHER])
def test_violation_allows_input_with_no_command_in_it(
    command: str, branch: str
) -> None:
    assert violation(command, branch) == ""
    assert segments(command) == []


# --- continuations -----------------------------------------------------------


@pytest.mark.parametrize(
    ("command", "branch"),
    [
        ("git \\\ncommit -m x", PROTECTED),
        ("git \\\npush origin main", PROTECTED),
        ("git \\\npush origin main", OTHER),
        ('git commit -m "a\\\nb"', PROTECTED),
    ],
    ids=["commit", "push-from-main", "push-from-branch", "inside-double-quotes"],
)
def test_violation_joins_a_backslash_newline(command: str, branch: str) -> None:
    assert refused(command, branch)


def test_violation_keeps_a_branch_switch_across_a_continuation() -> None:
    for command in (
        "git checkout -b feat/x && \\\ngit commit -m x",
        "git checkout -b feat/x \\\n&& git commit -m x",
        "git checkout -b feat/x && # make it\ngit commit -m x",
        "git checkout -b feat/x && git commit -F - <<'EOF'\nfix main's guard\nEOF",
        "git checkout -b feat/x && cat <<EOF > f &&\nbody\nEOF\ngit commit -m x",
    ):
        assert violation(command, PROTECTED) == "", command


def test_segments_joins_a_continuation_only_outside_single_quotes() -> None:
    assert segments("git \\\ncommit -m x") == [
        Segment(("git", "commit", "-m", "x"), "")
    ]
    assert segments("echo 'a\\\nb'") == [Segment(("echo", "a\\\nb"), "")]
    assert segments('echo "a\\\nb"') == [Segment(("echo", "ab"), "")]


def test_segments_does_not_join_an_escaped_backslash_to_the_next_line() -> None:
    assert segments("echo a\\\\\ngit status") == [
        Segment(("echo", "a\\"), ""),
        Segment(("git", "status"), "\n"),
    ]


def test_violation_keeps_an_escaped_backslash_before_a_newline_in_double_quotes() -> (
    None
):
    assert violation('echo "a\\\\\n"; git push origin main', OTHER).startswith(
        PUSH_REASON
    )
    assert segments('echo "a\\\\\n"; git status') == [
        Segment(("echo", "a\\\n"), ""),
        Segment(("git", "status"), ";"),
    ]


def test_segments_leaves_a_continuation_inside_a_comment_alone() -> None:
    assert segments("echo ok # path\\\ngit status") == [
        Segment(("echo", "ok"), ""),
        Segment(("git", "status"), "\n"),
    ]


def test_segments_joins_a_continuation_before_a_separator() -> None:
    assert segments("echo a \\\n&& git status") == [
        Segment(("echo", "a"), ""),
        Segment(("git", "status"), "&&"),
    ]


# --- constructs the scanner does not read ------------------------------------

UNMODELLED_BYPASSES = [
    "echo $'it\\'s'; git commit -m x # '",
    "$m = @'\nit's\n'@\ngit commit -m x # '",
    "$m = @\"\nit's\n\"@\ngit commit -m x # '",
    "<# it's #>\ngit commit -m x # '",
    "<# a\nit's\n#>\ngit commit -m x # '",
    '$x = "say `"hi"; git commit -m x # "',
]


def test_unmodelled_openers_is_the_documented_set() -> None:
    assert guard_git.UNMODELLED_OPENERS == (
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


@pytest.mark.parametrize("command", UNMODELLED_BYPASSES)
def test_violation_refuses_unmodelled_syntax_naming_a_commit_on_main(
    command: str,
) -> None:
    assert violation(command, PROTECTED).startswith(UNMODELLED_REASON)


@pytest.mark.parametrize("command", UNMODELLED_BYPASSES)
def test_violation_allows_unmodelled_syntax_off_main(command: str) -> None:
    assert violation(command, OTHER) == ""


@pytest.mark.parametrize("branch", ["", "Main"])
def test_violation_limits_the_distrust_to_the_exact_protected_branch(
    branch: str,
) -> None:
    assert violation("echo $'it\\'s'; git commit -m x # '", branch) == ""


def test_violation_refuses_a_heredoc_hidden_bypass_by_the_heredoc_rule() -> None:
    command = "cat <<EOF >/dev/null\nit's\nEOF\ngit commit -m x # '"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "printf $'a\\tb\\n' > f",
        "$m = @'\nit's\n'@\nWrite-Output $m",
        "<# note #>\ngit status",
        "echo hi $'there'",
    ],
)
def test_violation_allows_unmodelled_syntax_that_names_nothing_risky(
    command: str,
) -> None:
    assert violation(command, PROTECTED) == ""


@pytest.mark.parametrize(
    "command",
    [
        "echo '@\"push\"@'",
        'echo "<# push #>"',
        "echo \"$'push'\"",
        "echo hi # $'push'",
        "cat <<'EOF'\n$'push'\nEOF",
    ],
    ids=["single-quoted", "double-quoted", "dollar-in-double", "comment", "body"],
)
def test_violation_ignores_openers_hidden_by_quotes_comments_and_bodies(
    command: str,
) -> None:
    assert violation(command, PROTECTED) == ""


def test_violation_flags_a_backtick_quote_inside_double_quotes() -> None:
    command = 'echo "say `"hi`" and push"'

    assert violation(command, PROTECTED).startswith(UNMODELLED_REASON)


def test_violation_does_not_flag_unmodelled_text_inside_a_heredoc_body() -> None:
    command = "cat <<'EOF' > notes\necho $'it\\'s'\nEOF\ngit commit -m x"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_refuses_a_switch_then_ansi_message_on_main() -> None:
    # The accepted cost A6 names: the branch switch is real, the distrust still fires.
    command = "git checkout -b feat/x && git commit -m $'a\\nb'"

    assert violation(command, PROTECTED).startswith(UNMODELLED_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "# it's\ngit push origin main # '",
        "cat <<'EOF' > f\nit's\nEOF\ngit push origin main",
        "echo $'x'; git push origin main",
    ],
    ids=["comment", "heredoc", "ansi-string"],
)
def test_violation_keeps_refusing_a_push_to_main_from_a_branch(command: str) -> None:
    assert violation(command, OTHER).startswith(PUSH_REASON)


def test_violation_gives_the_unmodelled_reason_branch_advice() -> None:
    reason = violation(UNMODELLED_BYPASSES[0], PROTECTED)

    assert "git checkout -b" in reason
    assert "`main`" in reason


def test_violation_documents_two_known_misses_of_the_raw_text_search() -> None:
    # A subcommand spelled with an escape or split quotes does not name `commit`
    # to the raw-text search, so the distrust does not fire. Adversarial rather
    # than a slip; recorded so a change to it is a decision.
    assert violation("git $'\\x63ommit' -m x", PROTECTED) == ""
    assert violation("echo $'it\\'s'; git co\"\"mmit -m x # '", PROTECTED) == ""


# --- substitutions in an unquoted heredoc body -------------------------------
#
# Bash expands `$( )` and backticks in a body whose delimiter was written without
# quotes, and runs what they hold. Every expectation below was checked against
# bash 5.2 with `git` shadowed by an echo function.


@pytest.mark.parametrize(
    "command",
    [
        "cat <<EOF > f\n$(git commit -m x)\nEOF",
        "cat <<EOF > f\n`git commit -m x`\nEOF",
        "cat <<EOF > f\n`git push origin main`\nEOF",
    ],
    ids=["dollar-paren-commit", "backtick-commit", "backtick-push"],
)
def test_violation_refuses_a_substitution_in_an_unquoted_body_on_main(
    command: str,
) -> None:
    assert refused(command, PROTECTED)


@pytest.mark.parametrize(
    "command",
    [
        "cat <<EOF > f\n`git push origin main`\nEOF",
        "cat <<EOF > f\n$(git push origin main)\nEOF",
    ],
    ids=["backtick", "dollar-paren"],
)
def test_violation_refuses_a_push_to_main_in_an_unquoted_body_from_a_branch(
    command: str,
) -> None:
    assert violation(command, OTHER).startswith(PUSH_REASON)


def test_violation_names_the_commit_not_the_heredoc_for_a_body_substitution() -> None:
    command = "cat <<EOF > f\n$(git commit -m x)\nEOF"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)
    assert violation(command, OTHER) == ""


@pytest.mark.parametrize(
    "opener",
    ["<<'EOF'", '<<"EOF"', "<<\\EOF", '<<E"O"F', "<<-'EOF'"],
    ids=["single", "double", "backslash", "quote-inside-word", "dash-single"],
)
@pytest.mark.parametrize("branch", [PROTECTED, OTHER])
def test_violation_leaves_a_quoted_delimiter_body_pure_data(
    opener: str, branch: str
) -> None:
    command = f"cat {opener} > f\n$(git commit -m x)\n`git push origin main`\nEOF"

    assert violation(command, branch) == ""


@pytest.mark.parametrize(
    "body",
    [
        "\\$(git commit -m x)",
        "\\`git commit -m x\\`",
        "$((1<<2))",
        "$(( 1 + 2 ))",
        "${x}",
        "${#x} and ${x:-default}",
        "cost $ 5, $1 and $$",
        "# $(not closed",
        "`never closed git commit",
        "$(git commit -m x",
    ],
    ids=[
        "escaped-dollar",
        "escaped-backticks",
        "shift-arithmetic",
        "arithmetic",
        "parameter",
        "parameter-forms",
        "lone-dollars",
        "unclosed-in-comment-like-text",
        "unclosed-backtick",
        "unclosed-dollar-paren",
    ],
)
def test_violation_does_not_read_text_or_arithmetic_in_an_unquoted_body_as_a_command(
    body: str,
) -> None:
    assert violation(f"cat <<EOF > f\n{body}\nEOF", PROTECTED) == ""


def test_violation_reads_an_escaped_backslash_before_a_substitution_as_live() -> None:
    # `\\` is one backslash, so the `$(` after it is not escaped. Bash runs it.
    command = "cat <<EOF > f\n\\\\$(git commit -m x)\nEOF"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "body",
    [
        "'$(git commit -m x)'",
        '"$(git commit -m x)"',
        "it's $(git commit -m x)",
        '$(echo "it\'s"; git commit -m x)',
        "$(git \\\ncommit -m x)",
        "$(echo y\ngit commit -m x)",
        "$( (git commit -m x) )",
        "$((git commit -m x); echo)",
        "$(echo ')'; git commit -m x)",
        "$(git commit -m x # ) not the end\n)",
        "${y:-$(git commit -m x)}",
        "$(( $(git commit -m x) + 1 ))",
        "`echo y; git commit -m x`",
        "# a comment is only text here: $(git commit -m x)",
    ],
    ids=[
        "single-quoted",
        "double-quoted",
        "stray-apostrophe",
        "quote-pair-inside",
        "continuation",
        "second-line",
        "subshell",
        "two-parens-not-arithmetic",
        "paren-in-quotes",
        "paren-in-comment",
        "parameter-default",
        "inside-arithmetic",
        "backtick-second-command",
        "hash-is-text",
    ],
)
def test_violation_refuses_every_body_substitution_form_bash_runs(body: str) -> None:
    assert violation(f"cat <<EOF > f\n{body}\nEOF", PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "cat <<EOF > f\n$(date)\nEOF",
        "cat <<EOF > f\nrun `git status` and $(git log --oneline)\nEOF",
        'cat <<EOF > f\n$(echo "it\'s")\nEOF',
        "cat <<EOF > f\nit's `date`\nEOF",
        "cat <<EOF > f\n$(cat <<'INNER'\ngit commit -m x\nINNER\n)\nEOF",
    ],
    ids=[
        "date",
        "read-only-git",
        "quote-inside",
        "apostrophe-and-date",
        "nested-heredoc",
    ],
)
def test_violation_allows_a_harmless_body_substitution_on_main(command: str) -> None:
    assert violation(command, PROTECTED) == ""


def test_violation_still_judges_the_command_after_a_body_with_substitutions() -> None:
    command = 'cat <<EOF > f\n$(echo "it\'s"; date)\nEOF\ngit commit -m x'

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_keeps_quote_pairing_after_a_body_substitution_with_a_stray_quote() -> (
    None
):
    # The apostrophe sits inside the substitution's own double quotes; it must not
    # pair with the one in the comment after the real commit.
    command = "cat <<EOF > f\n$(echo \"it's\")\nEOF\ngit commit -m x # '"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_reads_a_backtick_pair_around_an_apostrophe_as_unrunnable() -> None:
    # Bash rejects the unbalanced quote, so nothing runs; the guard drops it rather
    # than letting it make the whole command unreadable.
    command = "cat <<EOF > f\n`it's`\nEOF\ngit push origin main"

    assert violation(command, OTHER).startswith(PUSH_REASON)


def test_violation_judges_a_substitution_in_the_second_of_two_heredocs() -> None:
    command = "cat <<'A' <<B\n$(git commit -m x)\nA\n$(git commit -m y)\nB"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)
    # Only the quoted one is data: swap them and the first is the live one.
    quoted_second = "cat <<A <<'B'\n$(date)\nA\n$(git commit -m y)\nB"
    assert violation(quoted_second, PROTECTED) == ""


def test_violation_expands_the_rest_of_an_unterminated_unquoted_body() -> None:
    assert violation("cat <<EOF\n$(git commit -m x)", PROTECTED).startswith(
        COMMIT_REASON
    )
    assert violation("cat <<'EOF'\n$(git commit -m x)", PROTECTED) == ""


def test_violation_joins_a_continuation_before_reading_a_body_substitution() -> None:
    # `$` and `(` are separated by a backslash-newline that bash deletes.
    command = "cat <<EOF > f\n$\\\n(git commit -m x)\nEOF"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_flags_unmodelled_syntax_inside_a_body_substitution() -> None:
    command = "cat <<EOF > f\n$(git commit -m $'a')\nEOF"

    assert violation(command, PROTECTED).startswith(UNMODELLED_REASON)


def test_violation_looks_inside_quotes_within_a_body_substitution() -> None:
    # A substitution nested in quotes inside a body substitution runs in bash, and
    # a plain `echo "$(git commit)"` outside a heredoc is read the same way.
    assert violation(
        'cat <<EOF\n$(echo "$(git commit -m x)")\nEOF', PROTECTED
    ).startswith(COMMIT_REASON)
    assert violation('echo "$(git commit -m x)"', PROTECTED).startswith(COMMIT_REASON)


def test_segments_puts_a_body_substitution_before_the_command_that_opened_it() -> None:
    command = "cat <<EOF > f\n$(git commit -m x)\nEOF"

    assert segments(command) == [
        Segment(("git", "commit", "-m", "x"), "", 1),
        Segment(("cat", "<<", "EOF", ">", "f"), SUBSTITUTED, 0),
    ]


def test_segments_orders_dollar_paren_and_backtick_substitutions_as_written() -> None:
    command = "cat <<EOF\n`git add .` text $(git commit -m x)\nEOF\nls"

    assert segments(command) == [
        Segment(("git", "add", "."), "", 1),
        Segment(("git", "commit", "-m", "x"), SUBSTITUTED, 1),
        Segment(("cat", "<<", "EOF"), SUBSTITUTED, 0),
        Segment(("ls",), "\n", 0),
    ]


def test_segments_leaves_a_quoted_delimiter_body_out_entirely() -> None:
    command = "cat <<'EOF'\n$(git commit -m x)\nEOF\nls"

    assert segments(command) == [
        Segment(("cat", "<<", "EOF"), ""),
        Segment(("ls",), "\n"),
    ]


def test_segments_unescapes_a_nested_backtick_pair_for_the_inner_command() -> None:
    command = "cat <<EOF\n`echo \\`git commit -m x\\``\nEOF"

    parsed = segments(command)

    assert parsed is not None
    assert parsed[0] == Segment(("git", "commit", "-m", "x"), "", 2)
    assert parsed[1] == Segment(("echo", "_"), SUBSTITUTED, 1)


def test_violation_distrust_searches_the_raw_command_comments_included() -> None:
    # Deliberate: the search is over the text as written, so a risky word in a
    # comment beside an unmodelled construct still refuses on main.
    assert violation("echo $'a' # then push", PROTECTED).startswith(UNMODELLED_REASON)


# --- the unreadable fallback after the pass ----------------------------------


def test_violation_still_calls_an_unbalanced_quote_unreadable() -> None:
    assert violation("echo 'oops; git push", PROTECTED).startswith(UNREADABLE_REASON)
    assert violation("echo 'oops; git push", OTHER) == ""


# --- command substitutions inside a word (fix round 2) -----------------------


def test_violation_refuses_a_commit_in_a_double_quoted_substitution_on_main() -> None:
    assert violation('echo "$(git commit -m x)"', PROTECTED).startswith(COMMIT_REASON)


UNRESOLVED_REASON = "Refused: this would run `git "

#: Every double-quoted or nested `$( )` position the class names (A2, T2), each
#: running `git commit` before its enclosing command.
SUBSTITUTION_POSITIONS = [
    'echo "result: $(git commit -m x)"',
    'out="$(git commit -m x 2>&1)"',
    'echo "${x:-$(git commit -m x)}"',
    '[[ -n "$(git commit -m x)" ]]',
    'declare x="$(git commit -m x)"',
    'cat <<<"$(git commit -m x)"',
    'echo > "$(git commit -m x)"',
    'echo $(echo "$(git commit -m x)")',
    'echo "$(cd /tmp; git commit -m x)"',
    'echo "$(sudo git commit -m x)"',
    'echo "$( (git commit -m x) )"',
    'for x in "$(git commit -m x)"; do :; done',
    'case "$(git commit -m x)" in a) :;; esac',
    'a=("$(git commit -m x)")',
    'printf -v v "$(git commit -m x)"',
    "echo $[ $(git commit -m x) ]",
    'export V="$(git commit -m x)"',
    'local V="$(git commit -m x)"',
    '[ -z "$(git commit -m x)" ]',
    'test -z "$(git commit -m x)"',
    'echo "$(echo hi)" "$(git commit -m x)"',
    'echo "a $(true) b $(git commit -m x) c"',
]


@pytest.mark.parametrize("command", SUBSTITUTION_POSITIONS)
def test_violation_refuses_a_commit_in_every_substitution_position(
    command: str,
) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_refuses_a_push_in_a_quoted_assignment_on_main_and_from_a_branch() -> (
    None
):
    command = 'out="$(git push origin main 2>&1)"'

    assert violation(command, PROTECTED).startswith(PUSH_REASON)
    assert violation(command, OTHER).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        'echo "$(git push origin main)"',
        'echo "${x:-$(git push origin main)}"',
        "echo `git push origin main`",
        "diff <(git push origin main) f",
        "diff <(a) <(git push origin main)",
        'echo "$(( $(git push origin main) ))"',
    ],
)
def test_violation_refuses_a_push_to_main_inside_a_substitution_from_a_branch(
    command: str,
) -> None:
    assert violation(command, OTHER).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        'echo "$(cat <<EOF > f\n$(git push origin main)\nEOF)"',
        'echo "$(cat <<EOF > f\n`git push origin main`\nEOF)"',
        'x="$(cat <<EOF\n$(git push origin main)\nEOF)"',
        "x=$(cat <<EOF\n$(git push origin main)\nEOF)",
    ],
)
def test_violation_judges_a_body_substitution_of_an_unclosed_quoted_substitution(
    command: str,
) -> None:
    # The delimiter glued to the `)` is no closing line, so the heredoc runs to
    # the end of the input, closing quote included, and bash still runs the body.
    assert violation(command, OTHER).startswith(PUSH_REASON)
    assert violation(command, PROTECTED).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        # Two double-quote frames are open around the heredoc.
        'echo "$(echo "$(cat <<EOF\n$(git push origin main)\nEOF)")"',
        'echo "$(echo "$(cat <<EOF\n$(git push origin main)\nEOF)")" && ls',
        # A backtick substitution holding the heredoc, and one holding the body.
        'echo "`cat <<EOF\n$(git push origin main)\nEOF`"',
        'echo "$(cat <<EOF\n$(echo "$(git push origin main)")\nEOF)"',
        # Single quotes before, after and inside the frames.
        'echo \'"\' "$(cat <<EOF\n$(git push origin main)\nEOF)"',
        "echo \"$(cat <<EOF\n$(git push origin main)\nEOF)\" 'x'",
        "echo \"$(echo 'x' \"$(cat <<EOF\n$(git push origin main)\nEOF)\")\" 'y'",
        # A double quote opened after the heredoc operator, on the same line.
        'cat <<EOF "$(git push origin main)"\nbody\nEOF',
        # A PowerShell backtick inside the string before the substitution.
        'echo "a`b $(cat <<EOF\n$(git push origin main)\nEOF)"',
        # Two heredocs on one line; the second closes the substitution.
        'echo "$(cat <<A <<B\nx\nA\n$(git push origin main)\nB)"',
        # Two quoted substitutions, the first closing properly.
        'echo "$(cat <<A\n$(git push origin main)\nA\n)" "$(cat <<B\nx\nB\n)"',
        'echo "a" "$(cat <<EOF\n$(git push origin main)\nEOF)" "b"',
    ],
)
def test_violation_judges_a_body_substitution_inside_nested_quotes_and_closers(
    command: str,
) -> None:
    # Each is a push to `main` in bash with `git` shadowed. The heredoc ends on
    # the line that carries the `)`, so the quotes around it stay balanced.
    assert violation(command, OTHER).startswith(PUSH_REASON)
    assert violation(command, PROTECTED).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        # (a) a body substitution, a single-quoted double quote before it.
        'echo "$(echo \'"\' "$(cat <<EOF\n$(git push origin main)\nEOF)")"',
        # (b) the command after a heredoc closed by a glued `)`.
        'echo "$(cat <<EOF\nhi\nEOF)" ; git push origin main',
        'echo "$(cat <<EOF\nhi\nEOF)"\ngit push origin main',
        "echo \"$(cat <<'EOF'\nhi\nEOF)\" ; git push origin main",
        'echo "$(cat <<EOF\nit\'s\nEOF)" ; git push origin main',
        # (c) the unquoted form, which the guard has always missed.
        "x=$(cat <<EOF\nhi\nEOF); git push origin main",
        "x=$(cat <<EOF\nhi\nEOF)\ngit push origin main",
        "cat <(cat <<EOF\nhi\nEOF) ; git push origin main",
    ],
)
def test_violation_judges_what_follows_a_heredoc_closed_by_the_substitutions_paren(
    command: str,
) -> None:
    # Bash ends the heredoc on `EOF)`, closes the substitution there and runs
    # the rest of the line (checked with `git` shadowed).
    assert violation(command, OTHER).startswith(PUSH_REASON)
    assert violation(command, PROTECTED).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        'echo "$(cat <<EOF\nhi\nEOF)"; ls',
        "x=$(cat <<EOF\nhi\nEOF); git status",
        "x=$(cat <<EOF\nhi\nEOF)\ngit log -1",
        'echo "$(cat <<EOF\nit\'s\nEOF)" ; echo done',
    ],
)
def test_violation_allows_a_harmless_command_after_a_heredoc_closed_by_a_paren(
    command: str,
) -> None:
    assert violation(command, PROTECTED) == ""
    assert violation(command, OTHER) == ""


@pytest.mark.parametrize(
    "command",
    [
        # What may stand between the delimiter and the `)`, and after it.
        "x=$(cat <<EOF\nhi\nEOF ); git push origin main",
        "x=$(cat <<EOF\nhi\nEOF\t); git push origin main",
        "x=$(cat <<EOF\nhi\nEOF)x; git push origin main",
        "x=$(cat <<EOF\nhi\nEOFx); git push origin main",
        "x=$(cat <<EOF\nhi\nEOF\\\n); git push origin main",
        # The rest of the closing line is commands, and bash runs them.
        "x=$(cat <<EOF\nhi\nEOF git push origin main)",
        "x=$(cat <<EOF\nhi\nEOF `git push origin main`)",
        "x=$(cat <<EOF\nhi\nEOF $(git push origin main))",
        "x=$(cat <<EOF\nhi\nEOF (git push origin main))",
        # Delimiter forms, and the body's own substitutions.
        "x=$(cat <<-EOF\n\thi\n\tEOF); git push origin main",
        "x=$(cat <<'EOF'\n$(git status)\nEOF); git push origin main",
        'x=$(cat <<"EOF"\nhi\nEOF); git push origin main',
        "x=$(cat <<EOF\n$(git push origin main)\nEOF)",
        "x=$(cat <<EOF\n`git push origin main`\nEOF)",
        # Nesting, and the other substitution forms.
        "x=$(echo $(cat <<EOF\nhi\nEOF)); git push origin main",
        "x=$(echo $(cat <<EOF\n$(git push origin main)\nEOF))",
        "x=$( (cat <<EOF\nhi\nEOF) ); git push origin main",
        "x=`cat <<EOF\nhi\nEOF`; git push origin main",
        "x=`cat <<EOF\nhi\nEOF`x; git push origin main",
        "tee >(cat <<EOF\nhi\nEOF) </dev/null; git push origin main",
        'echo "${x:-$(cat <<EOF\nhi\nEOF)}"; git push origin main',
        "echo $(( $(cat <<EOF\n3\nEOF) + 1 )); git push origin main",
        # Two heredocs: the last one closes the substitution.
        "x=$(cat <<A <<B\n1\nA\n$(git push origin main)\nB); echo",
        "x=$(cat <<A <<B\n1\nA\n2\nB); git push origin main",
        # A comment after the delimiter, an empty body, a quote in the body.
        "x=$(cat <<EOF # c\nhi\nEOF); git push origin main",
        "x=$(cat <<EOF\nEOF); git push origin main",
        'x=$(cat <<EOF\n"\nEOF); git push origin main',
    ],
)
def test_violation_reads_a_closing_line_that_carries_the_substitutions_paren(
    command: str,
) -> None:
    # Each is a push to `main` in bash 5.2 with `git` shadowed.
    assert violation(command, OTHER).startswith(PUSH_REASON)
    assert violation(command, PROTECTED).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        # Not a closing line in bash, which is then a syntax error or a body.
        "x=$(cat <<EOF\nhi\n EOF); git push origin main",
        "x=$(cat <<EOF\nhi\nEOF;\n); git push origin main",
        "x=$(cat <<EOF\nhi\nEOF foo\n); git push origin main",
        # A top-level subshell does not take the rule; bash rejects the command.
        "(cat <<EOF\nhi\nEOF); git push origin main",
    ],
)
def test_violation_leaves_a_line_bash_does_not_close_on_as_body(command: str) -> None:
    # The delimiter line never arrives, so the rest is the body and nothing runs.
    assert violation(command, OTHER) == ""


def test_violation_reads_an_unterminated_heredoc_in_a_substitution_as_unreadable() -> (
    None
):
    # Bash rejects it ("unexpected EOF while looking for matching `)'") and runs
    # nothing; the guard no longer closes quotes for it, so it is unreadable.
    command = 'echo "$(cat <<A <<B\n$(git push origin main)\nA\n$(date)'
    assert "could not be read" in violation(command, PROTECTED)
    assert violation(command, OTHER) == ""


def test_violation_still_reads_the_body_that_follows_a_closing_paren_on_the_opener() -> (
    None
):
    # `$(cat <<EOF)` closes on the opener line; the body follows it (bash warns).
    command = "x=$(cat <<EOF)\n$(git push origin main)\nEOF\necho done"
    assert violation(command, OTHER).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        # Process substitution: the closing line, a body substitution, the
        # command on the closing line, and the line break before the `)`.
        "cat <(cat <<EOF\nhi\nEOF) ; git push origin main",
        "tee >(cat <<EOF\nhi\nEOF) </dev/null ; git push origin main",
        "cat <(cat <<EOF\n$(git push origin main)\nEOF)",
        "cat <(cat <<EOF\nhi\nEOF git push origin main)",
        "cat <(cat <<EOF\nhi\nEOF\n)\ngit push origin main",
        # A `${x:-$(...)}` default, quoted and not: the `)` closes the
        # substitution and the `}` after it closes the parameter.
        'echo "${x:-$(cat <<EOF\nhi\nEOF)}" ; git push origin main',
        "echo ${x:-$(cat <<EOF\nhi\nEOF)} ; git push origin main",
        'echo "${x:-$(cat <<EOF\n$(git push origin main)\nEOF)}"',
        'echo "${x:-$(cat <<EOF\nhi\nEOF git push origin main)}"',
        # A `)` inside quotes or a comment on the closing line does not close
        # the substitution in bash; a later line does, and the push runs. The
        # guard reads the first `)` it sees, which can only add refusals.
        'x=$(cat <<EOF\nhi\nEOF "a)b"\n); git push origin main',
        "x=$(cat <<EOF\nhi\nEOF # a)\n); git push origin main",
        "x=$(cat <<EOF\nhi\nEOF 'a)'\n); git push origin main",
        "x=$(cat <<EOF\nhi\nEOF\\)\n); git push origin main",
        # A `case` pattern's `)` on a line of its own is not the closer.
        "x=$(case a in a) cat <<EOF\nhi\nEOF\n;; esac) ; git push origin main",
        # A backtick pair and a nested `$( )` around the heredoc.
        "x=$(echo `cat <<EOF\nhi\nEOF`) ; git push origin main",
        "x=$(echo $(cat <<EOF\nhi\nEOF) ; git push origin main)",
        "x=$(echo $(cat <<EOF\nhi\nEOF) ; echo)  ; git push origin main",
        # Whatever follows the closing `)` is judged, whatever joins it.
        'x="$(cat <<EOF\nhi\nEOF)x"; git push origin main',
        'x="$(cat <<EOF\nhi\nEOF)#"; git push origin main',
        "x=$(cat <<EOF\nhi\nEOF)#; git push origin main",
        "x=$(cat <<EOF\nhi\nEOF) && git push origin main",
        "x=$(cat <<EOF\nhi\nEOF) | git push origin main",
        "x=$(cat <<EOF\nhi\nEOF) & git push origin main",
        "x=$(cat <<EOF\nhi\nEOF)\n\ngit push origin main",
        "x=$(cat <<EOF\nhi\nEOF\n) # c )\ngit push origin main",
        # A body full of quote characters does not unbalance the line.
        'echo "$(cat <<EOF\n"\nEOF)" ; git push origin main',
        'echo "$(cat <<EOF\n\'\nEOF)" ; git push origin main',
        'echo "$(cat <<EOF\n`\nEOF)" ; git push origin main',
        'echo "$(cat <<EOF\n\\\nEOF)" ; git push origin main',
    ],
)
def test_violation_reads_a_closing_line_in_every_kind_of_substitution(
    command: str,
) -> None:
    # Each runs `git push origin main` in bash 5.2 with `git` shadowed.
    assert violation(command, OTHER).startswith(PUSH_REASON)
    assert violation(command, PROTECTED).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        # A tab-stripped delimiter: one tab, several, and the rest of the line.
        "x=$(cat <<-EOF\n\thi\n\tEOF); git push origin main",
        "x=$(cat <<-EOF\n\t\thi\n\t\tEOF); git push origin main",
        "x=$(cat <<-EOF\n\thi\n\t\t\tEOF); git push origin main",
        "x=$(cat <<-EOF\n\thi\n\tEOF git push origin main)",
        "x=$(cat <<-EOF\n\thi\nEOF\t)\ngit push origin main",
        # A delimiter that is, or holds, a `)`.
        "x=$(cat <<\\)\nhi\n)\n); git push origin main",
        'x=$(cat <<")"\nhi\n)\n); git push origin main',
        "x=$(cat <<')'\nhi\n)\n); git push origin main",
        "x=$(cat <<'A)'\nhi\nA)\n); git push origin main",
        "x=$(cat <<'A)'\nhi\nA)\n)\ngit push origin main",
        "x=$(cat <<'A)'\nhi\nA))\ngit push origin main",
        "x=$(cat <<'A)'\nhi\nA)); git push origin main",
        'x=$(cat <<"E)"\nhi\nE)\n); git push origin main',
        # A body line that begins with the delimiter text ends the body in
        # bash too, so what is on it is a command.
        "x=$(cat <<EOF\nEOFish) git push origin main\nEOF\n)",
        "x=$(cat <<EOF\nEOFish\nEOF\n); git push origin main",
        # Two substitutions on one line, each with a heredoc.
        'echo "$(cat <<A\nx\nA\n)" "$(cat <<B\ny\nB\n)" ; git push origin main',
        'echo "$(cat <<A\nx\nA)" "$(cat <<B\ny\nB)" ; git push origin main',
        "echo $(cat <<A\nx\nA) $(cat <<B\ny\nB) ; git push origin main",
        "echo $(cat <<A\nx\nA) $(cat <<B\n$(git push origin main)\nB)",
        "echo $(cat <<A\n$(git push origin main)\nA) $(cat <<B\ny\nB)",
        'echo "$(cat <<EOF\nEOF)$(cat <<EOF\nEOF)" ; git push origin main',
        'echo "$(cat <<EOF\nEOF)$(cat <<EOF\nEOF)"\ngit push origin main',
        # Two heredocs in one substitution; the last one closes it.
        "echo $(cat <<A; cat <<B\nx\nA\ny\nB\n); git push origin main",
        "echo $(cat <<A; cat <<B\nx\nA\ny\nB); git push origin main",
        # A heredoc inside the body of another, one inside the other's `)`.
        'echo "$(cat <<EOF\n$(cat <<IN\nhi\nIN)\nEOF)" ; git push origin main',
    ],
)
def test_violation_reads_the_delimiter_shapes_a_closing_line_can_take(
    command: str,
) -> None:
    # Each runs `git push origin main` in bash 5.2 with `git` shadowed.
    assert violation(command, OTHER).startswith(PUSH_REASON)
    assert violation(command, PROTECTED).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        # `)` inside quotes or a comment on the closing line: bash does not
        # close there, the push is part of the substitution's text or a
        # comment, and the guard agrees.
        'x=$(cat <<EOF\nhi\nEOF "a)b" git push origin main\n)',
        "x=$(cat <<EOF\nhi\nEOF # git push origin main)\n)",
        'x=$(cat <<EOF\nhi\nEOF "a)b"\n)',
        # A comment after the closing `)` hides the push.
        "x=$(cat <<EOF\nhi\nEOF) # git push origin main",
        # Not a closing line: a leading space, a tab under plain `<<`, a
        # carriage return on every line of a CRLF script, a heredoc in the
        # body of an enclosing one that swallows the push.
        "x=$(cat <<EOF\nhi\n EOF); git push origin main",
        "x=$(cat <<EOF\nhi\n\tEOF); git push origin main",
        "x=$(cat <<-EOF\n\thi\n \tEOF); git push origin main",
        "x=$(cat <<EOF\r\nhi\r\nEOF)\r; git push origin main",
        "x=$(cat <<EOF\r\nhi\r\nEOF)\r\ngit push origin main",
        'echo "$(cat <<EOF\n$(cat <<IN\nhi\nIN) git push origin main\nEOF\n)"',
    ],
)
def test_violation_allows_what_bash_does_not_run_after_a_closing_line(
    command: str,
) -> None:
    # None of these runs a push in bash 5.2 with `git` shadowed.
    assert violation(command, OTHER) == ""
    assert violation(command, PROTECTED) == ""


def test_violation_reads_a_closing_paren_followed_by_a_carriage_return() -> None:
    # Only the line break after the `)` is a CRLF one: the delimiter line is
    # exact, the `)` closes, and `\r` on the next command is part of its word
    # end, not of the delimiter. Bash pushes `main`.
    command = "x=$(cat <<EOF\nhi\nEOF)\r\ngit push origin main"
    assert violation(command, OTHER).startswith(PUSH_REASON)
    assert violation(command, PROTECTED).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        # Bash rejects these ("unexpected EOF while looking for matching
        # `)'") and runs nothing; the guard reads the line as closing, or the
        # whole thing as a body, and over-refuses. A push either way.
        "x=$(cat <<')'\nhi\n))\n); git push origin main",
        "x=$(cat <<'A)'\nhi\nA)\nA)); git push origin main",
        "x=$(cat <<EOF\nEOFish)\nEOF\n); git push origin main",
        "x=$(cat <<EOF\nEOFish)\nEOF); git push origin main",
        "x=$(cat <<EOF\nEOF)\nEOF\n); git push origin main",
        "x=$(cat <<EOF\nEOF\n)); git push origin main",
        "x=$( (cat <<EOF\nhi\nEOF) ; git push origin main )",
        'echo "$(cat <<EOF\n$(cat <<IN\n$(git push origin main)\nIN)\nEOF)"',
    ],
)
def test_violation_over_refuses_a_closing_line_bash_rejects(command: str) -> None:
    # The liberal direction is the safe one: a line the guard reads as closing
    # and bash does not (or the reverse) is a syntax error in bash, never a
    # command that runs without the guard seeing it.
    assert violation(command, OTHER).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    ("command", "branch", "refused"),
    [
        # The `&&` chain before the substitution keeps its trust through the
        # closing line and into the commit after it.
        (
            'git checkout -b x && echo "$(cat <<EOF\nhi\nEOF)" && git commit -m x',
            PROTECTED,
            False,
        ),
        (
            "git checkout -b x && x=$(cat <<EOF\nhi\nEOF) && git commit -m x",
            PROTECTED,
            False,
        ),
        (
            "git checkout -b x &&\nx=$(cat <<EOF\nhi\nEOF) && git commit -m x",
            PROTECTED,
            False,
        ),
        (
            'echo "$(cat <<EOF\nhi\nEOF)" && git checkout -b x && git commit -m x',
            PROTECTED,
            False,
        ),
        # A `;` after the closing line is not a guarantee, so on `main` the
        # commit may land there (the A6 rule).
        (
            'git checkout -b x && echo "$(cat <<EOF\nhi\nEOF)" ; git commit -m x',
            PROTECTED,
            True,
        ),
        (
            'git checkout -b x && echo "$(cat <<EOF\nhi\nEOF)" ; git commit -m x',
            OTHER,
            False,
        ),
        # A switch to `main` after the substitution is still caught.
        (
            "git checkout main && x=$(cat <<EOF\nhi\nEOF) && git commit -m x",
            OTHER,
            True,
        ),
        (
            'git checkout -b x && echo "$(cat <<EOF\nhi\nEOF)" && git checkout main && git commit -m x',
            PROTECTED,
            True,
        ),
    ],
)
def test_violation_keeps_and_trust_across_a_heredoc_closing_line(
    command: str, branch: str, refused: bool
) -> None:
    # Outcomes match bash with `git` shadowed (the `;` case on `main` is the
    # deliberate over-refusal of the untrusted-switch rule).
    assert bool(violation(command, branch)) is refused


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m \"$(cat <<'EOF'\nmsg\nEOF\n)\"",
        "git commit -m \"$(cat <<'EOF'\nmsg)\nEOF\n)\"",
        'git commit -m "$(cat <<EOF\nmsg\nEOF\n)"',
        "git commit -m \"$(cat <<'EOF'\nmsg\nEOF)\"",
        "git commit -m \"$(cat <<'EOF'\nit's 1) done\nEOF\n)\"",
        "git commit -m \"$(cat <<'EOF'\nit's 1) done\nEOF)\"",
    ],
)
def test_violation_keeps_the_outcome_of_the_pipelines_commit_form(
    command: str,
) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)
    assert violation(command, OTHER) == ""
    assert violation("git checkout -b x && " + command, PROTECTED) == ""
    assert (
        violation(
            "git checkout -b x && " + command + " && git push -u origin x", PROTECTED
        )
        == ""
    )


def test_violation_judges_a_commit_in_a_body_of_nested_quoted_substitutions() -> None:
    command = 'echo "$(echo "$(cat <<EOF\n$(git commit -m x)\nEOF)")"'
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)
    assert violation(command, OTHER) == ""


@pytest.mark.parametrize(
    "command",
    [
        'echo "$(cat <<EOF\n$(git status)\nEOF)"',
        'echo "$(cat <<EOF\nhello\nEOF)"',
        'echo "$(echo "$(cat <<EOF\n$(date)\nEOF)")"',
        "echo \"$(cat <<'EOF'\n$(git push origin main)\nEOF)\"",
        "echo '$(cat <<EOF\n$(git push origin main)\nEOF)'",
    ],
)
def test_violation_allows_a_heredoc_in_a_quoted_substitution_that_runs_no_git(
    command: str,
) -> None:
    assert violation(command, PROTECTED) == ""
    assert violation(command, OTHER) == ""


def test_violation_keeps_an_unbalanced_quote_without_a_heredoc_unreadable() -> None:
    # Unreadable, refused on `main` only when it names a risky command, allowed
    # anywhere else.
    assert violation('echo "unbalanced', PROTECTED) == ""
    unreadable = 'echo "unbalanced; git push origin main'
    assert "could not be read" in violation(unreadable, PROTECTED)
    assert violation(unreadable, OTHER) == ""


def test_violation_still_treats_a_quoted_delimiter_body_as_data_in_a_quote() -> None:
    command = "echo \"$(cat <<'EOF' > f\n$(git push origin main)\nEOF)\""
    assert violation(command, OTHER) == ""


def test_violation_allows_a_commit_in_a_substitution_off_main() -> None:
    assert violation('echo "$(git commit -m x)"', OTHER) == ""
    assert violation("echo `git commit -m x`", OTHER) == ""


def test_segments_puts_a_quoted_substitution_before_the_command_around_it() -> None:
    assert segments('echo "$(git status)"') == [
        Segment(("git", "status"), "", 1),
        Segment(("echo", "_"), SUBSTITUTED, 0),
    ]


@pytest.mark.parametrize("separator", ["&&", ";", "|"])
def test_segments_gives_the_first_group_the_separator_of_its_command(
    separator: str,
) -> None:
    assert segments(f'ls {separator} echo "$(git status)"') == [
        Segment(("ls",), ""),
        Segment(("git", "status"), separator, 1),
        Segment(("echo", "_"), SUBSTITUTED, 0),
    ]


def test_segments_marks_a_second_group_substituted_too() -> None:
    assert segments('ls && echo "$(a)$(b)"') == [
        Segment(("ls",), ""),
        Segment(("a",), "&&", 1),
        Segment(("b",), SUBSTITUTED, 1),
        Segment(("echo", "__"), SUBSTITUTED, 0),
    ]


def test_segments_closes_two_levels_one_after_the_other() -> None:
    assert segments('echo "$($(git checkout main))" && ls') == [
        Segment(("git", "checkout", "main"), "", 2),
        Segment(("_",), SUBSTITUTED, 1),
        Segment(("echo", "_"), SUBSTITUTED, 0),
        Segment(("ls",), "&&", 0),
    ]


def test_segments_returns_to_an_operator_after_the_command_around_a_group() -> None:
    parsed = segments('echo "$(a)"; ls')

    assert parsed is not None
    assert parsed[-1] == Segment(("ls",), ";", 0)


def test_segments_keeps_a_newline_inside_a_group_out_of_the_outer_separator() -> None:
    command = "git commit -m \"$(cat <<'EOF'\nit's 1) done\nEOF\n)\""

    assert segments(command) == [
        Segment(("cat", "<<", "EOF"), "", 1),
        Segment(("git", "commit", "-m", "_"), SUBSTITUTED, 0),
    ]


def test_segments_two_argument_construction_is_depth_zero() -> None:
    assert Segment(("a",), "") == Segment(("a",), "", 0)
    assert SUBSTITUTED == "$("


def test_segments_blanks_group_marks_and_the_placeholder_it_was_given() -> None:
    assert segments("echo \x1dgit commit\x1e") == [
        Segment(("echo", "git", "commit"), "", 0)
    ]
    assert segments("echo \x1fa") == [Segment(("echo", "a"), "", 0)]


def test_violation_cannot_be_given_a_forged_group_to_hide_behind() -> None:
    # The marks are blanked on the way in, so the text is read as written.
    assert violation("echo \x1dgit commit -m x\x1e", PROTECTED) == ""
    assert violation("\x1egit commit -m x", PROTECTED).startswith(COMMIT_REASON)
    assert violation("git checkout -b feat/y \x1e&& git commit -m x", PROTECTED) == ""


def test_segments_leaves_an_unclosed_substitution_in_the_text() -> None:
    parsed = segments("echo $(git status")

    assert parsed is not None
    assert Segment(("git", "status"), "(", 0) in parsed


# --- backticks (A3, T3) ------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "echo `git commit -m x`",
        "x=`git commit -m x`",
        "echo ${x:-`git commit -m x`}",
        "echo 2>`git commit -m x`",
        "`git commit -m x`",
        "echo `echo \\`git commit -m x\\``",
        'echo "`git commit -m x`"',
    ],
)
def test_violation_refuses_a_commit_in_a_backtick_in_every_position(
    command: str,
) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_refuses_a_push_to_main_in_a_backtick_from_a_branch() -> None:
    assert violation("echo `git push origin main`", OTHER).startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        'git commit -m "a`nb"; git push origin main; git log --format="%h`t%s"',
        'git commit -m "a`nb"; git push origin main',
        'git commit -m "a`nb #1"; git push origin main',
        'git commit -m "Line`nSee #12"; git push origin main',
    ],
)
def test_violation_still_sees_a_push_after_a_powershell_escape(command: str) -> None:
    assert violation(command, OTHER).startswith(PUSH_REASON)


def test_violation_allows_a_powershell_message_with_escapes() -> None:
    assert violation('git commit -m "Title`n`nBody"', OTHER) == ""


def test_segments_keeps_a_double_quoted_backtick_in_the_text() -> None:
    assert segments('echo "a`b`c"') == [
        Segment(("b",), "", 1),
        Segment(("echo", "a`b`c"), SUBSTITUTED, 0),
    ]


def test_violation_reads_the_slot_right_after_an_unpaired_powershell_backtick() -> None:
    command = 'echo "a`n" && git checkout -b feat/y && git commit -m "$(git checkout -q main)x"'

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)
    parsed = segments(command)
    assert parsed is not None
    assert parsed[-2:] == [
        Segment(("git", "checkout", "-q", "main"), "&&", 1),
        Segment(("git", "commit", "-m", "_x"), SUBSTITUTED, 0),
    ]


def test_violation_is_no_worse_than_before_for_a_backtick_between_commands() -> None:
    assert violation('echo "a`n"; echo `date`; git push origin main', OTHER).startswith(
        PUSH_REASON
    )


# --- process substitution (A4, T4) -------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "diff <(git commit -m x) /dev/null",
        "tee >(git commit -m x) </dev/null",
        "cat <(git commit -m x)",
        "cat <(case x in x) git commit -m y;; esac)",
    ],
)
def test_violation_refuses_a_commit_in_a_process_substitution(command: str) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_segments_replaces_a_whole_process_substitution_with_the_placeholder() -> None:
    assert segments("diff <(git status) /dev/null") == [
        Segment(("git", "status"), "", 1),
        Segment(("diff", "_", "/dev/null"), SUBSTITUTED, 0),
    ]
    assert segments("tee >(cat) /dev/null") == [
        Segment(("cat",), "", 1),
        Segment(("tee", "_", "/dev/null"), SUBSTITUTED, 0),
    ]


# --- a substitution runs before its command (A5, T5) --------------------------


@pytest.mark.parametrize(
    "command",
    [
        'git commit -m "$(git checkout -q main)x"',
        "git commit -m $(git checkout -q main)x",
        "git commit -F - <<EOF\n$(git checkout -q main)\nEOF",
        'echo "$($(git checkout main))" && git commit -m x',
        'if ($?) { git commit -m "$(git checkout main)" }',
    ],
)
def test_violation_runs_a_substitution_before_the_command_around_it(
    command: str,
) -> None:
    assert violation(command, OTHER).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        'git checkout -b feat/y && out="$(git commit -m y)"',
        'git checkout -b feat/y && git commit -m "$(date)"',
        'git checkout -b feat/y && echo "$(date)$(git commit -m y)"',
        'git checkout -b feat/y &&\necho "$(git commit -m y)"',
        'git checkout -b feat/y && echo "$(git status)" && git commit -m y',
        'echo "$(git checkout -b feat/y && git commit -m y)"',
        'git checkout -b "$(echo feat/y)" && git commit -m x',
        'git checkout -b feat/y && git commit -m "$( )x"',
        'git checkout -b feat/y && git commit -m "Use ``foo`` here"',
    ],
)
def test_violation_carries_and_trust_into_and_through_a_substitution(
    command: str,
) -> None:
    assert violation(command, PROTECTED) == ""


@pytest.mark.parametrize(
    "command",
    [
        'echo "$(git checkout -b feat/y; git commit -m y)"',
        'echo "$(git checkout -b feat/y)" && git commit -m y',
    ],
)
def test_violation_does_not_trust_a_switch_a_substitution_may_not_have_made(
    command: str,
) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        'out="$(git checkout -b feat/y)" && git commit -m y',
        'git commit -m "$(git checkout -b feat/y)x"',
    ],
)
def test_violation_deliberately_over_refuses_a_switch_inside_a_substitution(
    command: str,
) -> None:
    # Bash commits on feat/y here. The guard widens the command's branches by
    # what the substitution switched to, so `main` stays in them: the safe side.
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_orders_groups_as_they_are_written() -> None:
    command = 'git commit -m "$(git checkout -q main)$(git checkout -q feat/y)"'

    assert segments(command) == [
        Segment(("git", "checkout", "-q", "main"), "", 1),
        Segment(("git", "checkout", "-q", "feat/y"), SUBSTITUTED, 1),
        Segment(("git", "commit", "-m", "__"), SUBSTITUTED, 0),
    ]
    assert violation(command, OTHER).startswith(COMMIT_REASON)


def test_violation_does_not_follow_a_switch_aimed_at_another_repository() -> None:
    assert violation('git commit -m "$(git -C ../o checkout main)x"', OTHER) == ""


# --- main among the branches it could be (A6, T6) -----------------------------


@pytest.mark.parametrize(
    "command",
    [
        "git checkout main; git commit -m x",
        "git checkout main\ngit commit -m x",
        "(git checkout main) && git commit -m x",
        "x=$(git checkout main) && git commit -m x",
        'x="$(git checkout main)" && git commit -m x',
        "git checkout main & git commit -m x",
        "git checkout main | git commit -m x",
        "x=$(git checkout main); git commit -m x",
    ],
)
def test_violation_refuses_a_commit_when_main_is_any_branch_it_could_land_on(
    command: str,
) -> None:
    assert violation(command, OTHER).startswith(COMMIT_REASON)


def test_violation_refuses_a_push_after_a_switch_to_main_that_may_have_failed() -> None:
    assert violation("git switch main || true; git push", OTHER).startswith(PUSH_REASON)


def test_violation_allows_a_commit_after_an_untrusted_switch_to_another_branch() -> (
    None
):
    assert violation("git checkout feat/y; git commit -m x", OTHER) == ""
    assert violation("git checkout feat/y\ngit commit -m x", OTHER) == ""


def test_violation_still_refuses_after_an_untrusted_switch_away_from_main() -> None:
    assert violation("git checkout -b feat/x; git commit -m x", PROTECTED).startswith(
        COMMIT_REASON
    )


@pytest.mark.parametrize(
    ("command", "branch", "expected"),
    [
        ("git checkout -; git commit -m x", PROTECTED, COMMIT_REASON),
        ("git checkout -; git commit -m x", OTHER, UNRESOLVED_REASON),
        ("git checkout - ; git push origin main", OTHER, PUSH_REASON),
        ("git checkout -; git push", OTHER, UNRESOLVED_REASON),
    ],
)
def test_violation_gives_the_commit_reason_then_push_then_unresolved(
    command: str, branch: str, expected: str
) -> None:
    assert violation(command, branch).startswith(expected)


# --- a switch target a substitution makes ------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        'git checkout "$(echo main)" && git commit -m x',
        "git checkout $(echo main) && git commit -m x",
        'git switch "$(echo main)" && git commit -m x',
        'git checkout -B "$(echo main)" && git commit -m x',
        'git switch -C "$(echo main)" && git commit -m x',
        'git checkout "$(echo ma)in" && git commit -m x',
        "git checkout `echo main` && git commit -m x",
    ],
)
def test_violation_cannot_resolve_a_switch_target_a_substitution_made(
    command: str,
) -> None:
    assert violation(command, OTHER).startswith(UNRESOLVED_REASON)


@pytest.mark.parametrize("option", ["-b", "-c"])
def test_violation_reads_a_new_branch_named_by_a_substitution_as_a_switch_away(
    option: str,
) -> None:
    command = f'git checkout {option} "$(echo feat/y)" && git commit -m x'

    assert violation(command, PROTECTED) == ""


def test_switch_target_marks_a_placeholder_target_unresolved() -> None:
    assert switch_target("checkout", ("\x1f",)) == UNRESOLVED
    assert switch_target("checkout", ("-B", "\x1f")) == UNRESOLVED
    assert switch_target("switch", ("-C", "feat/\x1f")) == UNRESOLVED
    assert switch_target("checkout", ("-b", "\x1f")) == "\x1f"
    assert switch_target("checkout", ("--", "\x1f")) == ""


def test_violation_allows_a_harmless_command_after_a_substituted_switch_target() -> (
    None
):
    assert violation('git checkout "$(echo main)" && git status', OTHER) == ""


# --- bash 5.3 funsub (A7, T7) ------------------------------------------------

FUNSUBS = [
    "echo ${ git commit -m x; }",
    "echo ${| git commit -m x; }",
    "echo ${\tgit commit -m x; }",
    "echo ${\ngit commit -m x; }",
    'echo "${ git commit -m x; }"',
    'echo "${| git push; }"',
]


@pytest.mark.parametrize("command", FUNSUBS)
def test_violation_plays_safe_on_every_funsub_opener(command: str) -> None:
    reason = violation(command, PROTECTED)

    assert reason.startswith(UNMODELLED_REASON)
    assert "${ cmd; }" in reason


@pytest.mark.parametrize("command", FUNSUBS)
def test_violation_allows_a_funsub_off_main(command: str) -> None:
    assert violation(command, OTHER) == ""


def test_violation_allows_a_funsub_on_main_that_names_neither_commit_nor_push() -> None:
    assert violation("echo ${ ls; }", PROTECTED) == ""
    assert violation('echo "${ ls; }"', PROTECTED) == ""


def test_violation_does_not_mistake_a_parameter_expansion_for_a_funsub() -> None:
    assert violation('echo "${x:-a}" ${y} ${#z}; git status', PROTECTED) == ""


# --- harmless and literal substitutions (A8, T8) ------------------------------


@pytest.mark.parametrize(
    "command",
    [
        'echo "$(git status)"',
        'v="$(git rev-parse HEAD)"',
        "echo `date`",
        'echo "$(git log -1 --format=%s)" | grep commit',
        'echo "<(git commit -m x)"',
        "echo '$(git commit -m x)'",
        'echo "\\$(git commit -m x)"',
        'echo "\\`git commit -m x\\`"',
        "echo \"$(echo '$(git commit -m x)')\"",
        "echo '\"$(git commit -m x)\"'",
        'echo $((1 + 2)) "$((3 * 4))"',
        'echo "$( )" "``" "$(# nothing\n)"',
    ],
)
def test_violation_leaves_harmless_and_literal_substitutions_alone(
    command: str,
) -> None:
    assert violation(command, PROTECTED) == ""


PIPELINE_COMMIT = "git commit -m \"$(cat <<'EOF'\nTitle\n\nBody\nEOF\n)\""
PIPELINE_COMMIT_AWKWARD = "git commit -m \"$(cat <<'EOF'\nit's 1) done\nEOF\n)\""


@pytest.mark.parametrize("command", [PIPELINE_COMMIT, PIPELINE_COMMIT_AWKWARD])
def test_violation_reads_the_pipelines_own_commit_form(command: str) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)
    assert violation(command, OTHER) == ""
    assert violation("git checkout -b x && " + command, PROTECTED) == ""
    assert violation("git checkout -b x &&\n" + command, PROTECTED) == ""


def test_violation_reads_a_quote_inside_a_double_quote_around_a_substitution() -> None:
    assert violation("echo \"'$(git commit -m x)'\"", PROTECTED).startswith(
        COMMIT_REASON
    )


def test_violation_flags_ansi_c_quoting_around_a_substitution_on_main_only() -> None:
    command = "echo $'$(git commit -m x)'"

    assert violation(command, PROTECTED).startswith(UNMODELLED_REASON)
    assert violation(command, OTHER) == ""


# --- a `case` pattern's `)` inside a substitution ----------------------------


@pytest.mark.parametrize(
    "command",
    [
        "echo $(case a in a) git commit -m x;; esac)",
        'echo "$(case a in a) git commit -m x;; esac)"',
        'echo "$(case x in x) git commit -m y;; esac)"',
        'echo "$(case x in (x) git commit -m y;; esac)"',
        'echo "$(case x in a|x) git commit -m y;; esac)"',
        'echo "$(echo hi; case x in x) git commit -m y;; esac)"',
        'echo "$( (case x in x) git commit -m y;; esac) )"',
        'echo "$(case b in a) echo hi;; b) git commit -m y;; esac)"',
        'echo "$(case a in a) case b in b) git commit -m y;; esac;; esac)"',
        "echo `case x in x) git commit -m y;; esac`",
        "cat <<EOF\n$(case x in x) git commit -m y;; esac)\nEOF",
        'echo "$(if true; then case x in x) git commit -m y;; esac; fi)"',
    ],
)
def test_violation_refuses_a_commit_after_a_case_pattern_inside_a_substitution(
    command: str,
) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_closes_a_substitution_at_its_own_paren_after_a_case() -> None:
    command = 'echo "$(case a in a) echo hi;; esac)" && git commit -m x'

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)
    assert violation("git checkout -b feat/y && " + command, PROTECTED) == ""


def test_violation_reads_case_as_a_word_only_where_a_command_could_start() -> None:
    # `case` as an argument opens nothing, so its substitution still ends at its
    # own `)` and the one after it is still found.
    command = 'echo "$(echo case) $(git commit -m x)"'

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)
    assert segments(command) == [
        Segment(("echo", "case"), "", 1),
        Segment(("git", "commit", "-m", "x"), SUBSTITUTED, 1),
        Segment(("echo", "_ _"), SUBSTITUTED, 0),
    ]


def test_segments_keeps_a_case_pattern_paren_inside_the_group() -> None:
    parsed = segments('echo "$(case a in a) git commit -m x;; esac)"')

    assert parsed is not None
    assert parsed[-1] == Segment(("echo", "_"), SUBSTITUTED, 0)
    assert any(s.tokens[:2] == ("git", "commit") and s.depth == 1 for s in parsed)


@pytest.mark.parametrize(
    "command",
    [
        "case a in a) git commit -m x;; esac",
        "(case a in a) git commit -m x;; esac)",
        "case a in\n  a) git commit -m x;;\nesac",
    ],
)
def test_violation_still_reads_a_case_statement_outside_any_substitution(
    command: str,
) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)
    assert violation(command, OTHER) == ""


# --- substitutions inside arithmetic ----------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        'echo "$(( $(git commit -m x) + 1 ))"',
        'echo "$(( `git commit -m x` ))"',
        'x="$(( $(git commit -m x) ))"',
        '(( "$(git commit -m x)" ))',
        "echo $(( $(git commit -m x) ))",
        "(( $(git commit -m x) ))",
        'echo "$(( 1 + $(( $(git commit -m x) )) ))"',
        'echo "$(( "$(git commit -m x)" ))"',
        "echo $(( `git commit -m x` ))",
    ],
)
def test_violation_refuses_a_commit_inside_an_arithmetic_expansion(
    command: str,
) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_refuses_a_push_inside_arithmetic_from_a_branch() -> None:
    command = 'echo "$(( $(git push origin main) ))"'

    assert violation(command, OTHER).startswith(PUSH_REASON)


def test_segments_puts_an_arithmetic_substitution_before_its_command() -> None:
    assert segments('echo "$(( $(git status) + 1 ))"') == [
        Segment(("git", "status"), "", 1),
        Segment(("echo", "_"), SUBSTITUTED, 0),
    ]


@pytest.mark.parametrize(
    "command",
    [
        "echo $((1<<2)); git status",
        "x=1; (( x <<= 1 )); git status",
        'echo "$((1 + 2))" $((3 * 4))',
    ],
)
def test_violation_leaves_plain_arithmetic_alone(command: str) -> None:
    assert violation(command, PROTECTED) == ""


def test_segments_extracts_nothing_from_plain_arithmetic() -> None:
    parsed = segments('echo $((1 + 2)) "$((3 * 4))"')

    assert parsed is not None
    assert all(segment.depth == 0 for segment in parsed)
    assert all(segment.separator != SUBSTITUTED for segment in parsed)


# --- an empty substitution -----------------------------------------------------


def test_segments_gives_an_empty_group_no_say_in_the_separator() -> None:
    assert segments('a && b "$( )"') == [
        Segment(("a",), ""),
        Segment(("b", "_"), "&&"),
    ]
    assert segments("a ; b `` c") == [
        Segment(("a",), ""),
        Segment(("b", "_", "c"), ";"),
    ]


@pytest.mark.parametrize("empty", ['"$( )"', '"$(# only a comment\n)"', "``", '"$(;)"'])
def test_segments_ignores_a_group_that_ran_nothing(empty: str) -> None:
    parsed = segments(f"git checkout -b feat/y && git commit -m {empty}x")

    assert parsed is not None
    assert [s.separator for s in parsed] == ["", "&&"]
    assert all(s.depth == 0 for s in parsed)


# --- a command that cannot be read in time, or at all -------------------------


def test_violation_survives_a_deeply_nested_heredoc_body_substitution() -> None:
    body = "$(" * 1500 + "git commit -m x" + ")" * 1500
    command = f"cat <<EOF\n{body}\nEOF\n"

    assert violation(command, PROTECTED) != ""
    assert violation(command.replace("commit -m x", "push origin main"), OTHER) != ""


def test_violation_stays_fast_with_thousands_of_unclosed_openers() -> None:
    import time

    command = "echo " + "$(" * 6000 + " git commit -m x"
    started = time.monotonic()

    reason = violation(command, PROTECTED)

    assert time.monotonic() - started < 5
    assert reason.startswith(UNMODELLED_REASON)
    assert violation(command, OTHER) == ""


@pytest.mark.parametrize("opener", ["$((", "(", "`", "<(", "${"])
def test_violation_stays_fast_and_plays_safe_on_a_hostile_run_of_openers(
    opener: str,
) -> None:
    import time

    command = "echo " + opener * 6000 + " git commit -m x"
    started = time.monotonic()

    violation(command, PROTECTED)
    violation(command, OTHER)

    assert time.monotonic() - started < 10


def test_violation_refuses_what_it_cannot_finish_reading_on_main() -> None:
    command = 'echo "$(' * 6000 + "git commit -m x" + ')"' * 6000

    assert violation(command, PROTECTED) != ""


def test_prepare_gives_up_in_time_and_says_so() -> None:
    text, unmodelled = guard_git._prepare("echo " + "$((" * 6000)

    assert unmodelled
    assert text.startswith("echo $((")


@pytest.mark.parametrize("depth", [29, 30])
def test_violation_judges_a_push_up_to_the_nesting_limit(depth: int) -> None:
    command = 'echo "$(' * depth + "git push origin main" + ')"' * depth

    assert violation(command, OTHER).startswith(PUSH_REASON)


def test_violation_does_not_judge_substitutions_nested_past_the_limit_off_main() -> (
    None
):
    # Recorded, not endorsed: past `_MAX_NESTING` the text is left unread. On
    # `main` the same command plays safe instead.
    push = 'echo "$(' * 31 + "git push origin main" + ')"' * 31
    commit = push.replace("push origin main", "commit -m x")

    assert violation(push, OTHER) == ""
    assert violation(commit, PROTECTED).startswith(UNMODELLED_REASON)


def test_violation_refuses_on_main_when_the_guard_itself_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(command: str) -> tuple[str, bool]:
        raise RuntimeError(command)

    monkeypatch.setattr(guard_git, "_prepare", explode)

    assert violation("git commit -m x", PROTECTED).startswith(UNREADABLE_REASON)
    assert violation("git status", PROTECTED) == ""
    assert violation("git commit -m x", OTHER) == ""


def test_main_exits_2_when_the_guard_fails_on_main(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def explode(command: str) -> tuple[str, bool]:
        raise RecursionError(command)

    monkeypatch.setattr(guard_git, "_prepare", explode)
    monkeypatch.setattr(guard_git, "current_branch", lambda _project: PROTECTED)
    payload = {"tool_input": {"command": "git commit -m x"}}

    assert run_hook(monkeypatch, payload) == 2
    assert "could not be read" in capsys.readouterr().err


# --- recorded misses (deliberate, pinned so changing them is a decision) -----


@pytest.mark.parametrize(
    "command",
    [
        "echo \"${x:-'$(git commit -m x)'}\"",
        'echo "${x:-\'}" "$(git commit -m x)" "\'}"',
    ],
)
def test_violation_misses_a_substitution_after_a_quote_inside_a_quoted_parameter(
    command: str,
) -> None:
    # In bash the single quote inside `"${...}"` is literal and the substitution
    # runs; the `${ }` frame reads it as quoting and hides the text. Recorded.
    assert violation(command, PROTECTED) == ""


# --- switches inside a substitution, and a detached HEAD ---------------------


def test_violation_cannot_resolve_a_switch_inside_a_substitution() -> None:
    command = 'git commit -m "$(git checkout -)x"'

    assert violation(command, OTHER).startswith(UNRESOLVED_REASON)


def test_violation_judges_a_substitution_in_a_detached_head() -> None:
    assert violation('echo "$(git push origin HEAD:main)"', "").startswith(PUSH_REASON)
    assert violation('echo "$(git commit -m x)"', "") == ""


# --- reserved words that take a command next ---------------------------------


def test_violation_refuses_a_commit_after_if_on_main() -> None:
    command = "if git commit -m x; then echo ok; fi"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "if git diff --quiet; then :; else git commit -am x; fi",
        "if false; then :; elif git commit -m x; then :; fi",
        "if true; then git commit -m x; fi",
        "while git commit -m x; do break; done",
        "until git commit -m x; do :; done",
        "! git commit -m x",
        "! ! git commit -m x",
        "if ! git commit -m x; then :; fi",
        "time ! git commit -m x",
        "time -p git commit -m x",
        "coproc git commit -m x",
        "for ((i=0;i<1;i++)); do git commit -m x; done",
        "true && if true; then git commit -m x; fi",
        "false || if true; then git commit -m x; fi",
        "ls | if true; then git commit -m x; fi",
        "sleep 0 & ! git commit -m x",
        "true\nif true\nthen git commit -m x\nfi",
        "true\nwhile git commit -m x; do break; done",
        "x=$(if true; then git commit -m x; fi)",
        'echo "$(! git commit -m x)"',
        "echo `! git commit -m x`",
        "cat <(until git commit -m x; do :; done)",
        "(if true; then git commit -m x; fi)",
        "{ ! git commit -m x; }",
        "cat <<EOF\n$(if true; then git commit -m x; fi)\nEOF",
        "then GIT_EDITOR=true git commit -m x",
        "else >log git commit -m x",
    ],
)
def test_violation_refuses_a_commit_after_every_reserved_word_on_main(
    command: str,
) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_allows_a_commit_in_a_quoted_heredoc_body_after_a_reserved_word() -> (
    None
):
    command = "cat <<'EOF'\nif git commit -m x; then :; fi\nEOF"

    assert violation(command, PROTECTED) == ""


def test_violation_refuses_a_push_after_a_reserved_word_from_a_branch() -> None:
    command = "for b in a; do git push origin main; done"

    assert violation(command, OTHER).startswith(PUSH_REASON)
    assert violation(command, PROTECTED).startswith(PUSH_REASON)


def test_violation_resolves_head_after_a_reserved_word_against_the_branch() -> None:
    command = "if true; then git push origin HEAD; fi"

    assert violation(command, PROTECTED).startswith(PUSH_REASON)
    assert violation(command, OTHER) == ""


@pytest.mark.parametrize(
    "command",
    [
        "if true; then git checkout main; fi; git commit -m x",
        "for i in 1; do git checkout main; done && git commit -m x",
        "! git checkout main; git commit -m x",
        'if true; then echo "$(git checkout main)"; fi; git commit -m x',
        "if true; then git checkout feat/z; fi; git checkout main; git commit -m x",
    ],
)
def test_violation_counts_a_switch_after_a_reserved_word(command: str) -> None:
    assert violation(command, OTHER).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "if true; then git checkout feat/z; fi; git commit -m x",
        "if true; then git -C ../o checkout main; fi; git commit -m x",
        "if true; then git commit -m then; fi",
    ],
)
def test_violation_allows_what_a_reserved_word_does_not_make_a_risk(
    command: str,
) -> None:
    assert violation(command, OTHER) == ""


@pytest.mark.parametrize(
    "command",
    [
        "if true; then git checkout main; fi; git commit -m x",
        "for i in 1 2; do git commit -m x; git checkout main; done",
        "! git checkout main; git commit -m x",
    ],
)
def test_violation_counts_a_hidden_switch_on_a_detached_head(command: str) -> None:
    assert violation(command, "").startswith(COMMIT_REASON)


# --- trust: `!` and `coproc` --------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "! git checkout -b feat/x && git commit -m x",
        "if ! git checkout -b feat/x; then git commit -m x; fi",
        "coproc git checkout -b feat/x && git commit -m x",
        "time ! git checkout -b feat/x && git commit -m x",
        "! time git checkout -b feat/x && git commit -m x",
        "time -p ! git checkout -b feat/x && git commit -m x",
        "! ! git checkout -b feat/x && git commit -m x",
    ],
)
def test_violation_does_not_trust_a_switch_a_bang_or_coproc_leads(
    command: str,
) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_does_not_trust_a_negated_push_target_either() -> None:
    command = "! git checkout -b feat/x && git push origin HEAD"

    assert violation(command, PROTECTED).startswith(PUSH_REASON)


def test_violation_does_not_trust_a_negated_switch_to_main_from_a_branch() -> None:
    assert violation("! git checkout main && git commit -m x", OTHER).startswith(
        COMMIT_REASON
    )


@pytest.mark.parametrize(
    "command",
    [
        "! true | git checkout -b feat/x && git commit -m x",
        "! true | cat | git checkout -b feat/x && git commit -m x",
        "! (git checkout -b feat/x)&&git commit -m x",
        "! (git checkout -b feat/x) && git commit -m x",
        "! { git checkout -b feat/x; } && git commit -m x",
        "coproc (git checkout -b feat/x)&&git commit -m x",
        "coproc { git checkout -b feat/x; } && git commit -m x",
        "! (true; git checkout -b feat/x)&&git commit -m x",
    ],
)
def test_violation_does_not_trust_a_switch_inside_a_negated_pipeline_or_group(
    command: str,
) -> None:
    # Bash: with `feat/x` already existing the checkout fails, `!` turns that
    # into success, and the commit runs on `main`.
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "git checkout -b feat/x && git commit -m x",
        "git checkout -b feat/x && ! git diff --cached --quiet && git commit -m x",
        "git checkout -b feat/x && time git commit -m x",
        "git checkout -b feat/x && time -p git commit -m x",
        "time git checkout -b feat/x && git commit -m x",
        "git checkout -b feat/x && ! git commit -m x",
        "git checkout -b feat/x && time ! git diff --quiet && git commit -m x",
        "git checkout -b feat/x && coproc true && git commit -m x",
        "! git diff --quiet && git checkout -b feat/x && git commit -m x",
        "! true | cat; git checkout -b feat/x && git commit -m x",
    ],
)
def test_violation_keeps_and_trust_where_no_bang_or_coproc_leads_the_switch(
    command: str,
) -> None:
    assert violation(command, PROTECTED) == ""


def test_violation_widens_a_negated_switch_only_from_what_the_chain_trusts() -> None:
    # `ok | {target}`, not `possible | {target}`: `main` must not return.
    command = "git checkout -b feat/x && ! git checkout -b feat/z && git commit -m x"

    assert violation(command, PROTECTED) == ""


def test_violation_orders_the_unresolved_reason_after_a_negated_switch() -> None:
    assert violation(
        "! git checkout - && git push origin feat/topic", OTHER
    ).startswith(UNRESOLVED_REASON)
    assert violation(
        "git checkout -; if true; then git commit -m x; fi", PROTECTED
    ).startswith(COMMIT_REASON)
    assert violation(
        "git checkout -; if true; then git commit -m x; fi", OTHER
    ).startswith(UNRESOLVED_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "if git checkout -b feat/x; then git commit -m x; fi",
        "while git checkout -b feat/x; do git commit -m x; break; done",
        "if true; git checkout -b feat/x; then git commit -m x; fi",
    ],
)
def test_violation_pins_the_accepted_cost_of_a_switch_in_a_condition(
    command: str,
) -> None:
    # Bash commits on `feat/x`. Refused on `main` because `then` and `do` follow
    # `;` and so every branch is in play: the accepted cost of playing safe.
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)
    assert violation(command, OTHER) == ""


@pytest.mark.parametrize(
    "command",
    [
        "git checkout -b feat/x && if true; then :; fi && git commit -m x",
        "git checkout -b feat/x && for f in a; do git add $f; done && git commit -m x",
        'git checkout -b feat/x && echo "$(if true; then git commit -m x; fi)"',
    ],
)
def test_violation_pins_the_refusal_after_a_trusted_compound_command(
    command: str,
) -> None:
    # Bash commits on `feat/x`. A compound command's `fi` or `done` follows `;`,
    # so the chain's trust ends there: a deliberate over-refusal.
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "\\! git commit -m x",
        "x=1 if git commit -m x",
        ">/dev/null ! git commit -m x",
        "sudo -n ! git commit -m x",
    ],
)
def test_violation_pins_a_quoted_or_misplaced_leader_as_an_over_refusal(
    command: str,
) -> None:
    # Bash reads none of these as a reserved word and runs no git; the walk
    # steps over a leader wherever it sits in the prefix, after the quotes are
    # gone. Recorded so changing it is a decision. (A quoted `'if'` or `"!"` is
    # no longer here: round 5 reads a quoted word as a word.)
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


# --- leaders that are only arguments -----------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        'echo "$(echo if case; git commit -m x)"',
        'echo "$(echo while case; git commit -m x)"',
        'echo "$(echo coproc case; git commit -m x)"',
        'echo "$(echo then case; git commit -m x)"',
        'echo "$(echo do case; git commit -m x)"',
        'echo "$(echo ! case; git commit -m x)"',
    ],
)
def test_violation_does_not_open_a_case_after_a_leader_used_as_an_argument(
    command: str,
) -> None:
    # `case` after `echo if` is an argument, so the `)` that closes the
    # substitution is not a pattern's and the commit inside it runs.
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_still_opens_a_case_after_a_leader_at_a_command_position() -> None:
    command = 'echo "$(if true; then case a in a) git commit -m x;; esac; fi)"'

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


# --- words that are not commands stay words ----------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "echo if git commit",
        "echo then git commit",
        "for git in commit; do :; done",
        "select git in commit; do break; done",
        "case git in commit) :;; esac",
        "IF git commit -m x",
        "Then git commit -m x",
    ],
)
def test_violation_keeps_words_that_are_not_commands_as_words(command: str) -> None:
    assert violation(command, PROTECTED) == ""


@pytest.mark.parametrize(
    "command",
    [
        "{ git commit -m x; }",
        "time git commit -m x",
        "case a in a) git commit -m x;; esac",
        "f() { git commit -m x; }",
        "function f { git commit -m x; }",
    ],
)
def test_violation_keeps_the_outcome_of_forms_that_were_already_read(
    command: str,
) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command", ["!", "if", "! ; git status", "done", "then", "! !"]
)
def test_violation_allows_a_reserved_word_with_no_command_behind_it(
    command: str,
) -> None:
    assert violation(command, PROTECTED) == ""


# --- loops -------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "for i in 1 2; do git commit -m x; git checkout main; done",
        "while true; do git commit -m x; git checkout main; break; done",
        "until false; do git commit -m x; git checkout main; break; done",
        "select b in a; do git commit -m x; git checkout main; break; done",
        'while [ -n "$(git commit -m x)" ]; do git checkout main; done',
        "for i in 1; do for j in 1; do git commit -m x; done; git checkout main; done",
        "for a in 1 2; do git commit -m x; for b in 1; do :; done; git checkout main; done",
        "x=$(for i in 1 2; do git commit -m x; git checkout main; done)",
        "for i in 1 2; do git commit -m x; git checkout main",
        "foreach ($b in 1,2) { git commit -m x; git checkout main }",
        "do { git commit -m x; git checkout main } while ($x)",
    ],
)
def test_violation_counts_a_switch_anywhere_in_a_loop_for_the_whole_loop(
    command: str,
) -> None:
    assert violation(command, OTHER).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "ForEach ($b in 1,2) { git commit -m x; git checkout main }",
        "FOREACH ($b in 1,2) { git commit -m x; git checkout main }",
        "Do { git commit -m x; git checkout main } While ($x)",
        "DO { git commit -m x; git checkout main } WHILE ($x)",
        "While ($true) { git commit -m x; git checkout main }",
        "For ($i=0; $i -lt 2; $i++) { git commit -m x; git checkout main }",
        "for ($i=0; $i -lt 2; $i++) { git commit -m x; git checkout main }",
        "foreach ($b in 1,2) { git commit -m x; git checkout main }",
    ],
)
def test_violation_reads_powershell_loop_keywords_in_any_case(command: str) -> None:
    assert violation(command, OTHER).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "for i in 1 2; do git commit -m x; done; git checkout main",
        "git commit -m x; for i in 1; do git checkout main; done",
        "done; git commit -m x; git checkout main",
        "for i in 1 2; do git commit -m x; git checkout feat/z; done",
        "for i in 1 2; do git commit -m x; git -C ../o checkout main; done",
        "for i in 1; do { :; }; done; git commit -m x; git checkout main",
        "for i in 1; do { git commit -m x; }; done; git checkout main",
    ],
)
def test_violation_bounds_a_loops_widening_to_the_loop(command: str) -> None:
    assert violation(command, OTHER) == ""


@pytest.mark.parametrize(
    "command",
    [
        "for i in 1 2; do case $i in x|done) :;; esac; git commit -m x; git checkout main; done",
        "for i in 1 2; do case $i in done) :;; esac; git commit -m x; git checkout main; done",
        "for i in 1 2; do case $i in x) :;; done) :;; esac; git commit -m x; git checkout main; done",
        'for i in 1 2; do "done" 2>/dev/null; git commit -m x; git checkout main; done',
        "for i in 1 2; do \\done 2>/dev/null; git commit -m x; git checkout main; done",
        "for i in 1 2; do 'done'; git commit -m x; git checkout main; done",
        'for i in 1 2; do d"on"e; git commit -m x; git checkout main; done',
    ],
)
def test_violation_does_not_close_a_loop_on_a_done_that_is_not_the_reserved_word(
    command: str,
) -> None:
    assert violation(command, OTHER).startswith(COMMIT_REASON)


def test_violation_closes_a_loop_on_a_done_in_every_place_bash_reads_one() -> None:
    for command in (
        "for i in 1; do :; done; git commit -m x; git checkout main",
        "for i in 1; do :; done\ngit commit -m x; git checkout main",
        "for i in 1; do : & done; git commit -m x; git checkout main",
        "for i in 1; do :; done && git commit -m x; git checkout main",
    ):
        assert violation(command, OTHER) == "", command


def test_violation_pins_a_loop_in_a_subshell_as_running_on() -> None:
    # Bash closes the loop at `done`. The `)` after it makes the next command's
    # separator `)`, which is also what a case pattern leaves, so the guard does
    # not close the loop: a deliberate over-refusal.
    command = "(for i in 1; do :; done); git commit -m x; git checkout main"

    assert violation(command, OTHER).startswith(COMMIT_REASON)


def test_violation_keeps_a_loop_open_through_a_stray_done() -> None:
    assert violation("done; git commit -m x; git checkout main", OTHER) == ""
    assert violation(
        "for i in 1 2; do git commit -m x; git checkout main; done; done", OTHER
    ).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "if true; then git checkout main; fi; git commit -m x",
        "for i in 1 2; do git commit -m x; git checkout main; done",
        "do { git commit -m x; git checkout main } while ($x)",
    ],
)
def test_violation_is_the_same_for_a_repeated_call(command: str) -> None:
    assert violation(command, OTHER) == violation(command, OTHER)


# --- git_subcommand after reserved words -------------------------------------


@pytest.mark.parametrize(
    "leader", ["if", "then", "else", "elif", "while", "until", "do", "!", "coproc"]
)
def test_git_subcommand_steps_over_each_reserved_word(leader: str) -> None:
    assert git_subcommand((leader, "git", "commit", "-m", "x")) == (
        "commit",
        ("-m", "x"),
    )


@pytest.mark.parametrize(
    "tokens",
    [
        ("if", "git", "commit"),
        ("!", "!", "git", "commit"),
        ("time", "!", "git", "commit"),
        ("time", "-p", "git", "commit"),
        ("time", "-p", "!", "git", "commit"),
        ("!", "time", "-p", "git", "commit"),
        ("then", "time", "-p", "!", "git", "commit"),
        ("elif", "then", "do", "git", "commit"),
        ("do", "GIT_EDITOR=true", "git", "commit"),
        ("else", ">", "log", "git", "commit"),
        ("elif", "/usr/bin/git", "commit"),
    ],
)
def test_git_subcommand_steps_over_chained_reserved_words_and_wrappers(
    tokens: tuple[str, ...],
) -> None:
    assert git_subcommand(tokens) == ("commit", ())


def test_git_subcommand_returns_a_switch_after_a_reserved_word_with_its_arguments() -> (
    None
):
    assert git_subcommand(("then", "git", "checkout", "main")) == (
        "checkout",
        ("main",),
    )
    assert git_subcommand(("!", "git", "checkout", "-b", "feat/x")) == (
        "checkout",
        ("-b", "feat/x"),
    )
    assert git_subcommand(("coproc", "git", "push")) == ("push", ())


@pytest.mark.parametrize(
    "tokens",
    [
        ("for", "git", "in", "commit"),
        ("select", "git", "in", "commit"),
        ("case", "git", "in"),
        ("function", "git"),
        ("in", "git", "commit"),
        ("fi", "git", "commit"),
        ("done", "git", "commit"),
        ("esac", "git", "commit"),
        ("time", "for", "git", "in", "commit"),
        ("IF", "git", "commit"),
        ("Then", "git", "commit"),
        ("!git", "commit"),
        ("echo", "if", "git", "commit"),
    ],
)
def test_git_subcommand_does_not_step_over_words_that_are_not_leaders(
    tokens: tuple[str, ...],
) -> None:
    assert git_subcommand(tokens) == ("", ())


@pytest.mark.parametrize(
    "tokens",
    [(), ("then",), ("!", "!"), ("time", "-p", "!"), ("if", "!"), ("coproc",)],
)
def test_git_subcommand_is_empty_when_only_reserved_words_are_given(
    tokens: tuple[str, ...],
) -> None:
    assert git_subcommand(tokens) == ("", ())


def test_git_subcommand_reads_a_reserved_word_after_git_as_an_argument() -> None:
    assert git_subcommand(("git", "commit", "-m", "then")) == (
        "commit",
        ("-m", "then"),
    )
    assert git_subcommand(("if", "git")) == ("", ())


def test_git_subcommand_leaves_a_redirected_git_after_a_leader_to_violation() -> None:
    assert git_subcommand(("then", "git", "-C", "../o", "checkout", "main")) == (
        "checkout",
        ("main",),
    )


# --- round 4: trust after `||` -----------------------------------------------


def test_violation_refuses_a_commit_after_an_or_switch_on_main() -> None:
    command = "git status || git checkout -b x && git commit -m x"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


# Each form below was run in bash 5.2 with `git` shadowed by a function that keeps
# HEAD in a file, and `branches` holding main, feat/y and feat/x: the refused ones
# land a commit or push on `main`, the allowed ones do not.

OR_OPERAND_FORMS = [
    # A later pipeline stage, and what can stand before the switch.
    "true || echo a | git checkout -b x && git commit -m x",
    "true || echo a |& git checkout -b x && git commit -m x",
    "true || time git checkout -b x && git commit -m x",
    "true || sudo git checkout -b x && git commit -m x",
    "true || nohup git checkout -b x && git commit -m x",
    "true || GIT_X=1 git checkout -b x && git commit -m x",
    "true || git checkout -b x 2>/dev/null && git commit -m x",
    'true || git checkout -b x "$(echo)" && git commit -m x',
    # Chained `||`, and an `||` after an `&&` chain.
    "false || true || git checkout -b x && git commit -m x",
    "git status || git rev-parse || git checkout -b x && git commit -m x",
    "true && true || git checkout -b x && git commit -m x",
    "coproc true || git checkout -b x && git commit -m x",
    # The rest of the chain, in every place the commit can sit.
    "true || git checkout -b x <<EOF && git commit -m x\nhi\nEOF",
    "true || git checkout -b x &&\ngit commit -m x",
    "true || git checkout -b x && true && git commit -m x",
    'true || git checkout -b x && echo "$(git commit -m x)"',
    "true || git checkout -b x && echo $(git commit -m x)",
    "true || git checkout -b x && git push origin HEAD",
    # The whole of it inside a group, a substitution or a condition.
    "{ true || git checkout -b x && git commit -m x; }",
    'echo "$(true || git checkout -b x && git commit -m x)"',
    "if true || git checkout -b x && git commit -m x; then :; fi",
    # A group glued to the operators.
    "true || (git checkout -b x)&&git commit -m x",
    "true ||(git checkout -b x) && git commit -m x",
    "true||(git checkout -b x)&&git commit -m x",
    "(true)||git checkout -b x&&git commit -m x",
    # A trailing space before a newline after the `||`.
    "true || \ngit checkout -b x && git commit -m x",
    # A body substitution of a heredoc on the switch is another list's.
    "true || git checkout -b x <<EOF && git commit -m x\n$(true && true)\nEOF",
]


@pytest.mark.parametrize("command", OR_OPERAND_FORMS)
def test_violation_refuses_a_commit_after_every_or_operand_form(command: str) -> None:
    assert violation(command, PROTECTED).startswith((COMMIT_REASON, PUSH_REASON))


def test_violation_refuses_a_push_of_head_after_an_or_switch_on_main() -> None:
    command = "true || git checkout -b x && git push origin HEAD"

    assert violation(command, PROTECTED).startswith(PUSH_REASON)


def test_violation_refuses_a_named_or_switch_that_may_not_have_run_from_a_branch() -> (
    None
):
    command = "git checkout main || git checkout feat/x && git commit -m x"

    assert violation(command, "feat/y").startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "git checkout main && true || git checkout -b x && git commit -m x",
        "git checkout main || git checkout -b x && git commit -m x",
    ],
)
def test_violation_refuses_an_or_switch_after_a_switch_to_main_from_a_branch(
    command: str,
) -> None:
    assert violation(command, "feat/y").startswith(COMMIT_REASON)


def test_violation_refuses_a_push_of_head_after_a_switch_to_main_from_a_branch() -> (
    None
):
    command = "git checkout main || git checkout -b x && git push origin HEAD"

    assert violation(command, "feat/y").startswith(PUSH_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "true ||\n\ngit checkout -b x && git commit -m x",
        "true || # note\ngit checkout -b x && git commit -m x",
        "true \\\n|| git checkout -b x && git commit -m x",
        "true || echo a |\n git checkout -b x && git commit -m x",
    ],
)
def test_violation_refuses_an_or_switch_across_line_forms(command: str) -> None:
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "git checkout -b feat/x || git checkout main && git commit -m x",
        "git checkout -b feat/x || true && git commit -m x",
    ],
)
def test_violation_refuses_an_or_whose_left_switch_may_have_failed(
    command: str,
) -> None:
    # `feat/x` exists, so the left side fails and the right side runs.
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "git checkout -b y && true || git checkout -b x && git commit -m x",
        "git checkout -b x || git checkout y && git commit -m x",
        "true && git checkout -b x || git checkout -b y && git commit -m x",
        "git checkout -b x || git checkout -b y && git commit -m x",
        "git checkout -b feat/z || git switch feat/z && git commit -m x",
    ],
)
def test_violation_unions_both_sides_of_an_or_for_the_and_after_it(
    command: str,
) -> None:
    assert violation(command, PROTECTED) == ""


def test_violation_closes_an_or_operand_when_its_substitution_ends() -> None:
    refused_command = 'echo "$(true || git checkout -b x)" && git commit -m x'
    allowed_command = (
        'git checkout -b y && echo "$(true || git checkout -b x)" && git commit -m x'
    )

    assert violation(refused_command, PROTECTED).startswith(COMMIT_REASON)
    assert violation(allowed_command, PROTECTED) == ""


@pytest.mark.parametrize("separator", [";", "\n"])
def test_violation_closes_an_or_operand_at_a_list_end(separator: str) -> None:
    command = (
        f"true || git checkout -b y{separator}git checkout -b x && git commit -m x"
    )

    assert violation(command, PROTECTED) == ""


def test_violation_closes_an_or_operand_when_its_group_closes() -> None:
    command = "( true || git checkout -b y ); git checkout -b x && git commit -m x"

    assert violation(command, PROTECTED) == ""


def test_violation_keeps_an_or_operand_in_a_heredoc_body_as_data() -> None:
    command = "cat <<'EOF'\ntrue ||\nEOF\ngit checkout -b x && git commit -m x"

    assert violation(command, PROTECTED) == ""


@pytest.mark.parametrize(
    "command",
    [
        "git status || git checkout -b x && git commit -m x",
        "true || git checkout -b x && git push origin HEAD",
    ],
)
def test_violation_leaves_the_or_rule_alone_off_main(command: str) -> None:
    assert violation(command, "feat/y") == ""
    assert violation(command, "") == ""  # a detached HEAD


@pytest.mark.parametrize("command", ["||", "true ||", "true || git checkout -b x &&"])
def test_violation_allows_a_dangling_or(command: str) -> None:
    # bash rejects each as a syntax error, and none runs a commit.
    assert violation(command, PROTECTED) == ""


def test_violation_refuses_a_leading_or_that_names_a_commit() -> None:
    # A syntax error in bash; the guard reads the commit and plays safe.
    assert violation("|| git commit -m x", PROTECTED).startswith(COMMIT_REASON)


def test_violation_refuses_an_or_switch_in_a_deep_chain_quickly() -> None:
    import time

    chain = "true || " * 5000 + "git checkout -b x && git commit -m x"
    groups = "{ " * 2000 + "true || git checkout -b x && git commit -m x"
    started = time.monotonic()

    reasons = [violation(chain, PROTECTED), violation(groups, PROTECTED)]

    assert time.monotonic() - started < 5
    assert all(reason.startswith(COMMIT_REASON) for reason in reasons)


# --- round 4: the `!`/`coproc` scope is not ended by a substitution ----------

NEGATION_LEAKS = [
    '! true | git checkout -b feat/x "$(true && true)" && git commit -m x',
    '! true | git checkout -b feat/x "$(true; true)" && git commit -m x',
    "! true | git checkout -b feat/x `true && true` && git commit -m x",
    "! true | git checkout -b feat/x `true; true` && git commit -m x",
    'coproc git checkout -b feat/x "$(true && true)" && git commit -m x',
    'true || git checkout -b x "$(true && true)" && git commit -m x',
    '! true | git checkout -b feat/x "$(true; ! true; true)" && git commit -m x',
    '! true | git checkout -b feat/x "$(true || true)" && git commit -m x',
    "! true | \ngit checkout -b feat/x && git commit -m x",
]


@pytest.mark.parametrize("command", NEGATION_LEAKS)
def test_violation_keeps_a_negation_through_the_substitutions_inside_it(
    command: str,
) -> None:
    # `feat/x` exists, so the checkout fails, `!` turns that into success and the
    # `&&` commits on `main`.
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        "! git diff --quiet || { git checkout -b feat/z && git commit -m x; }",
        "! git diff --quiet; git checkout -b x && git commit -m x",
    ],
)
def test_violation_ends_a_negation_at_a_list_end_of_its_own(command: str) -> None:
    assert violation(command, PROTECTED) == ""


def test_violation_ends_a_negation_at_an_or_of_its_own() -> None:
    command = "! git diff --quiet || git checkout -b x && git commit -m x"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


# --- round 4: what stays allowed ---------------------------------------------

OR_ALLOWED = [
    "git checkout -b feat/z || git checkout feat/z && git commit -m x",
    "git switch -c feat/z || git switch feat/z && git commit -m x",
    "git fetch || true && git checkout -b x && git commit -m x",
    "true || false && git checkout -b x && git commit -m x",
    "true || { git checkout -b x && git commit -m x; }",
    "git checkout -b feat/z && ! git diff --cached --quiet && git commit -m x",
    'echo "$(! true)"; git checkout -b x && git commit -m x',
    'echo "$(true || git checkout -b y)"; git checkout -b x && echo "$(true && git commit -m x)"',
]


@pytest.mark.parametrize("command", OR_ALLOWED)
def test_violation_still_allows_a_switch_that_certainly_ran(command: str) -> None:
    assert violation(command, PROTECTED) == ""


# --- round 4: a substitution opening with a group, siblings, case clauses -----

SUBSTITUTION_OPENS_WITH_GROUP = [
    'true || git checkout -b x "$( (true) )" && git commit -m x',
    'true || git checkout -b x "$( { true; } )" && git commit -m x',
    "true || git checkout -b x `(true)` && git commit -m x",
    'echo "$(true || git checkout -b x "$( (true) )" && git commit -m x)"',
    '! true | git checkout -b feat/x "$( (true) )" && git commit -m x',
]


@pytest.mark.parametrize("command", SUBSTITUTION_OPENS_WITH_GROUP)
def test_violation_reads_a_group_opened_inside_a_substitution_as_its_own(
    command: str,
) -> None:
    # The group belongs to the substitution: it is closed again before the `&&`.
    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        'echo "$(true || git checkout -b y)" "$(git checkout -b x && git commit -m x)"',
        'echo "$(! true)" "$(git checkout -b x && git commit -m x)"',
    ],
)
def test_violation_does_not_carry_state_into_a_sibling_substitution(
    command: str,
) -> None:
    assert violation(command, PROTECTED) == ""


@pytest.mark.parametrize("terminator", [";;", ";&", ";;&"])
@pytest.mark.parametrize(
    "scope", ["true || git checkout -b y", "! true | git checkout -b y"]
)
def test_violation_ends_a_scope_at_a_case_clause_terminator(
    scope: str, terminator: str
) -> None:
    command = (
        f"case $v in a) {scope} {terminator} "
        "b) git checkout -b x && git commit -m x ;; esac"
    )

    assert violation(command, PROTECTED) == ""


def test_violation_pins_a_group_after_a_negation_ended_by_a_newline_as_refused() -> (
    None
):
    # Accepted over-refusal, the same as at 43eeea3: bash commits on `x`, but a
    # newline between a `!` list and a `{` is not told from one inside it.
    command = "! true\n{ git checkout -b x && git commit -m x; }"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


# --- round 4: the runs `_segments` hands to `_judge` --------------------------

RUN_PINS = [
    ("true || { git a; }", [(), ((0, "||"), (0, "{"))]),
    ("a; } && b", [(), ((0, ";"), (0, "}"), (0, "&&"))]),
    ("(a)&&b", [((0, "("),), ((0, ")"), (0, "&&"))]),
    ("a ||(b)", [(), ((0, "||"), (0, "("))]),
    ("a);b", [(), ((0, ")"), (0, ";"))]),
    ("a ; ( ) b", [(), ((0, ";"), (0, "("), (0, ")"))]),
    ("a ||\n b", [(), ((0, "||"), (0, "\n"))]),
    ("a |\n b", [(), ((0, "|"), (0, "\n"))]),
    ("a\n\n b", [(), ((0, "\n"), (0, "\n"))]),
    (
        "case x in a) b ;; c) d ;; esac",
        [(), ((0, ")"),), ((0, ";;"),), ((0, ")"),), ((0, ";;"),)],
    ),
    # An empty group runs nothing, and leaves the run it would have followed.
    ("()", []),
    (
        'true || git checkout -b x "$(\n)" && git commit -m x',
        [(), ((0, "||"),), ((0, "&&"),)],
    ),
    # A substitution's first segment inherits the run at the outer depth and
    # carries what is written inside before its command at the inner one; the
    # close is marked at the front of what follows.
    (
        'true || git checkout -b x "$( (true) )" && git commit -m x',
        [(), ((0, "||"), (1, "(")), ((1, "$)"),), ((0, "&&"),)],
    ),
    ('a || echo "$(b && c)" d', [(), ((0, "||"),), ((1, "&&"),), ((1, "$)"),)]),
    ('echo "$(a)" && b', [(), ((1, "$)"),), ((0, "&&"),)]),
    # Operators written before a close are dropped; sibling substitutions each
    # get the close marker of the one before.
    ('echo "$(a; )" b', [(), ((1, "$)"),)]),
    ('echo "$(a)" "$(b)"', [(), ((1, "$)"),), ((1, "$)"),)]),
    ('echo "$( (a) )"', [((1, "("),), ((1, "$)"),)]),
]


@pytest.mark.parametrize(("command", "expected"), RUN_PINS)
def test_segments_hands_out_each_run_as_written(
    command: str, expected: list[tuple[tuple[int, str], ...]]
) -> None:
    runs: list[tuple[tuple[int, str], ...]] = []

    guard_git._segments(command, runs=runs)

    assert runs == expected


@pytest.mark.parametrize(
    "command",
    [
        "",
        "||",
        "git status",
        "git status || git checkout -b x && git commit -m x",
        "true || (git checkout -b x)&&git commit -m x",
        'true || git checkout -b x "$( (true) )" && git commit -m x',
        'echo "$(a)" "$(b)"',
        "cat <<EOF && a\n$(b)\nEOF",
        "true || `(a)` && b",
        "a\n\n b",
        "echo 'unbalanced",
    ],
)
def test_segments_gives_the_same_segments_with_and_without_runs(command: str) -> None:
    runs: list[tuple[tuple[int, str], ...]] = []

    with_runs = guard_git._segments(command, runs=runs)

    assert with_runs == guard_git._segments(command)
    assert with_runs is None or len(runs) == len(with_runs)


# --- round 5: quoted words are never operators --------------------------------


def test_violation_refuses_an_or_switch_after_a_quoted_separator_word() -> None:
    command = 'true || echo ";" | git checkout -b x && git commit -m x'

    reason = violation(command, PROTECTED)

    assert reason.startswith(COMMIT_REASON)


@pytest.mark.parametrize("command", ["'if' git commit -m x", '"!" git commit -m x'])
def test_violation_allows_a_quoted_leader_on_main(command: str) -> None:
    # Rewritten from round 3's over-refusal pins: bash reads a quoted word as a
    # word, so no git runs.
    assert violation(command, PROTECTED) == ""


def test_violation_refuses_a_commit_after_an_and_and_carriage_return() -> None:
    # Rewritten from round 2's allowed pin: `&&\r` runs a command named `\r` in
    # bash, so the switch before it is not trusted.
    command = 'git checkout -b feat/y &&\r\ngit commit -m "$(date)"\r\n'

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


# --- round 5, step 5: the readers' cases and the edge-case suite ---------------
#
# Every bash claim below was run in bash 5.2 with `git` shadowed by a function
# that keeps HEAD in a file (an empty checkout argument fails, PATH=/usr/bin:/bin,
# stdin closed, a timeout), the oracle shown live first by a plain `git commit`
# printing `COMMIT on main`. A row marked "no oracle" is PowerShell-only or
# needs a real `sudo`/`env`; the guard is asserted to play safe there.

REASONS = {"C": COMMIT_REASON, "P": PUSH_REASON, "U": UNRESOLVED_REASON, "A": ""}


def assert_judged(command: str, branch: str, kind: str) -> None:
    reason = violation(command, branch)
    if kind == "A":
        assert reason == "", command
    else:
        assert reason.startswith(REASONS[kind]), command


QUOTED_OPERATOR_WORDS = [
    ('";"', ";"),
    ('"&&"', "&&"),
    ("'&'", "&"),
    ("'|'", "|"),
    ("'||'", "||"),
    ("'('", "("),
    ("')'", ")"),
    ("'{'", "{"),
    ("'}'", "}"),
    ("'<'", "<"),
    ("'>'", ">"),
    ('";"";"', ";;"),
    ("a';'", "a;"),
    ('"a\nb"', "a\nb"),
    ("'a\nb'", "a\nb"),
    ('"a\r\nb"', "a\r\nb"),
    ('"a b;c"', "a b;c"),
    ('"it\'s ;"', "it's ;"),
    ("'say \"a|b\"'", 'say "a|b"'),
    ('a";"b', "a;b"),
    ('"$(echo ";")"', "_"),
]


@pytest.mark.parametrize(("source", "text"), QUOTED_OPERATOR_WORDS)
def test_segments_keeps_a_quoted_operator_word_in_one_invocation(
    source: str, text: str
) -> None:
    parsed = segments(f"echo {source} x")

    assert parsed is not None
    assert [segment.tokens for segment in parsed if segment.depth == 0] == [
        ("echo", text, "x")
    ]
    assert not any(segment.separator == ";" for segment in parsed if segment.depth == 0)


# Both shells read an operator character inside an unquoted `${...}` as part of one word.
PARAMETER_WORDS: list[str] = [
    "${x:-;}",
    "${x:-&}",
    "${x:-|}",
    "${x:-)}",
    "${x:-(}",
    "${x:-<}",
    "${x:->}",
    "${x:-{}",
    "${x:-a\nb}",
    "${x:-a;b|c&&d}",
]


@pytest.mark.parametrize("word", PARAMETER_WORDS)
def test_segments_keeps_an_operator_inside_an_unquoted_parameter_in_its_word(
    word: str,
) -> None:
    assert segments(f"echo {word} x") == [Segment(("echo", word, "x"), "")]


BASH_WORD_TOKENS = [
    (r"\;", ";"),
    (r"\&", "&"),
    (r"\|", "|"),
    (r"\(", "("),
    (r"\)", ")"),
    (r"\{", "{"),
    (r"\<", "<"),
    (r"\>", ">"),
    (r"a\;b", "a;b"),
    ("{", "{"),
    ("}", "}"),
    ("{}", "{}"),
    ("}}", "}}"),
    ("x\ry", "x\ry"),
    ("x\r", "x\r"),
]


@pytest.mark.parametrize(("source", "text"), BASH_WORD_TOKENS)
def test_segments_returns_the_bash_reading_of_the_shell_dependent_tokens(
    source: str, text: str
) -> None:
    # The public output is bash's reading: an escaped operator character, a
    # brace argument and a carriage return are word characters. `violation`
    # also reads each the way PowerShell does.
    assert segments(f"echo {source} x") == [Segment(("echo", text, "x"), "")]


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ('echo ";" ; echo x', [("echo", ";"), ("echo", "x")]),
        ('echo ";";echo x', [("echo", ";"), ("echo", "x")]),
        ('echo "a" && echo ";"', [("echo", "a"), ("echo", ";")]),
        ("echo '|' | cat", [("echo", "|"), ("cat",)]),
        ('echo "";"" x', [("echo", ""), ("", "x")]),
        ('echo \\"; echo x', [("echo", '"'), ("echo", "x")]),
        ("echo '\\'; echo x", [("echo", "\\"), ("echo", "x")]),
        ('echo "\\\\"; echo x', [("echo", "\\"), ("echo", "x")]),
    ],
)
def test_segments_still_splits_on_a_real_operator_next_to_a_quoted_one(
    command: str, expected: list[tuple[str, ...]]
) -> None:
    parsed = segments(command)

    assert parsed is not None
    assert [segment.tokens for segment in parsed] == expected


def test_segments_labels_the_real_separator_next_to_a_quoted_operator() -> None:
    parsed = segments('echo ";" && echo x')

    assert parsed == [
        Segment(("echo", ";"), ""),
        Segment(("echo", "x"), "&&"),
    ]


def test_segments_keeps_the_quote_state_through_a_substitution() -> None:
    parsed = segments("echo \"$(echo ';' ; echo x)\"")

    assert parsed == [
        Segment(("echo", ";"), "", 1),
        Segment(("echo", "x"), ";", 1),
        Segment(("echo", "_"), SUBSTITUTED, 0),
    ]


def test_segments_still_splits_inside_a_double_quoted_substitution() -> None:
    parsed = segments('echo "$(a; b)"')

    assert parsed == [
        Segment(("a",), "", 1),
        Segment(("b",), ";", 1),
        Segment(("echo", "_"), SUBSTITUTED, 0),
    ]


@pytest.mark.parametrize("delimiter", ["';'", '";"', r"\;"])
def test_segments_reads_a_quoted_heredoc_delimiter_as_one_word(delimiter: str) -> None:
    parsed = segments(f"cat <<{delimiter}\nbody\n;\ngit commit -m x")

    assert parsed == [
        Segment(("cat", "<<", ";"), ""),
        Segment(("git", "commit", "-m", "x"), "\n"),
    ]


@pytest.mark.parametrize(
    "command",
    [
        'echo "a;',
        "echo 'a;",
        "echo a\\",
        'echo "a" ";',
        'true || echo "a;b | git checkout -b x',
    ],
)
def test_segments_is_none_for_an_unbalanced_quote_around_an_operator(
    command: str,
) -> None:
    assert segments(command) is None


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("{ a; }", [Segment(("a",), "{")]),
        ("do { a }", [Segment(("do",), ""), Segment(("a", "}"), "{")]),
        ("! { echo; }", [Segment(("!",), ""), Segment(("echo",), "{")]),
        ("time { echo; }", [Segment(("time",), ""), Segment(("echo",), "{")]),
        ("then { a; }", [Segment(("then",), ""), Segment(("a",), "{")]),
        ("coproc C { a; }", [Segment(("coproc", "C"), ""), Segment(("a",), "{")]),
        (
            "function f { a; }",
            [Segment(("function", "f"), ""), Segment(("a",), "{")],
        ),
        ('"do" { a }', [Segment(("do", "{", "a", "}"), "")]),
        # The `{` is an argument, so the `}` after the `;` closes nothing.
        ("echo { a; }", [Segment(("echo", "{", "a"), "")]),
        ("a }}", [Segment(("a", "}}"), "")]),
        ("a {}; b", [Segment(("a", "{}"), ""), Segment(("b",), ";")]),
    ],
)
def test_segments_reads_a_brace_as_a_group_only_where_bash_does(
    command: str, expected: list[Segment]
) -> None:
    assert segments(command) == expected


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("a\r\nb", [Segment(("a\r",), ""), Segment(("b",), "\n")]),
        (
            "a &&\r\nb",
            [Segment(("a",), ""), Segment(("\r",), "&&"), Segment(("b",), "\n")],
        ),
        ("a && b\r\n", [Segment(("a",), ""), Segment(("b\r",), "&&")]),
        ("a\rb", [Segment(("a\rb",), "")]),
        ("\r", [Segment(("\r",), "")]),
        ("echo x\r y", [Segment(("echo", "x\r", "y"), "")]),
    ],
)
def test_segments_reads_a_carriage_return_as_a_word_character(
    command: str, expected: list[Segment]
) -> None:
    # bash runs `$'\r'` as a word: it neither ends a command nor starts a comment.
    assert segments(command) == expected


PRIVATE_SAMPLES = [
    "echo ';' x",
    'echo "&&" "a|b" x',
    "echo a';'b",
    "'if' \"git\" x",
    r"echo \; \& \( x",
    "echo { } x",
    "echo ${x:-;} ${y:-a|b}",
    "echo x\r y",
    "echo a\r\nb",
    "echo \"$(echo ';')\" x",
    "cat <<';'\nbody\n;\nx",
    'x="a;b" git status',
    "git commit -m 'a; b'",
    'git commit -m "a | b"\r\n',
]


@pytest.mark.parametrize("command", PRIVATE_SAMPLES)
def test_segments_never_shows_a_stand_in_or_a_quote_mark(command: str) -> None:
    parsed = segments(command)

    assert parsed is not None
    for segment in parsed:
        text = segment.separator + "".join(segment.tokens)
        assert not any(char in text for char in guard_git._PRIVATE), command


@pytest.mark.parametrize("char", guard_git._PRIVATE)
def test_segments_blanks_a_forged_private_character(char: str) -> None:
    assert segments(f"echo a{char}b") == [Segment(("echo", "a", "b"), "")]


@pytest.mark.parametrize("char", guard_git._PRIVATE)
def test_violation_sees_through_a_forged_private_character(char: str) -> None:
    assert violation(f"{char}if git commit -m x", PROTECTED).startswith(COMMIT_REASON)
    assert violation(f"git{char} commit -m x", PROTECTED).startswith(COMMIT_REASON)
    assert violation(f"git push -o x{char} origin main", OTHER).startswith(PUSH_REASON)
    assert violation(f"echo{char};{char}git commit -m x", PROTECTED).startswith(
        COMMIT_REASON
    )


# Words that hold an operator character in quotes, or inside a `${...}`: none of them ends a list.
QUOTED_OPERATOR_SOURCES: list[str] = [
    '";"',
    '"&&"',
    "'&'",
    "'|'",
    "'||'",
    "'('",
    "')'",
    "'{'",
    "'}'",
    "'<'",
    "'>'",
    '";"";"',
    "a';'",
    '"a\nb"',
    "${x:-;}",
    "${x:-&}",
    "${x:-|}",
    "${x:-)}",
    "${x:-(}",
    "${x:-a\nb}",
    "${x:-<}",
    "${x:->}",
    "${x:-{}",
    '"a b;c"',
    "'a&&b'",
    '""";"',
]


@pytest.mark.parametrize("word", QUOTED_OPERATOR_SOURCES)
def test_violation_refuses_an_or_switch_after_any_quoted_operator_word(
    word: str,
) -> None:
    command = f"true || echo {word} | git checkout -b x && git commit -m x"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize("word", QUOTED_OPERATOR_SOURCES)
def test_violation_refuses_a_negated_switch_after_any_quoted_operator_word(
    word: str,
) -> None:
    # `feat/x` exists, so the checkout fails and the commit lands on `main`.
    command = f"! true | echo {word} | git checkout -b feat/x && git commit -m x"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize("word", QUOTED_OPERATOR_SOURCES)
def test_violation_allows_the_same_forms_when_main_is_not_checked_out(
    word: str,
) -> None:
    command = f"true || echo {word} | git checkout -b x && git commit -m x"

    assert violation(command, OTHER) == ""


def test_violation_refuses_the_group_form_of_the_reproduction() -> None:
    command = "{ true || echo } | git checkout -b x && git commit -m x; }"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


# A real `;` or `&&` ends the `||` operand even when a quoted operator sits beside it: nothing refused that bash does not land.
REAL_OPERATOR_ENDS_THE_OPERAND: list[tuple[str, str, str]] = [
    ('true || echo ";"; git checkout -b x && git commit -m x', PROTECTED, "A"),
    ("true || echo ; git checkout -b x && git commit -m x", PROTECTED, "A"),
    ('true || echo "a" ; git checkout -b x && git commit -m x', PROTECTED, "A"),
    ('true || echo ";" ; git checkout -b x && git commit -m x', PROTECTED, "A"),
    ('true || echo ";" && git checkout -b x && git commit -m x', PROTECTED, "A"),
]


@pytest.mark.parametrize(("command", "branch", "kind"), REAL_OPERATOR_ENDS_THE_OPERAND)
def test_violation_still_ends_an_or_operand_at_a_real_operator(
    command: str, branch: str, kind: str
) -> None:
    assert_judged(command, branch, kind)


# Read one way by bash and another by PowerShell; each reading is judged and a refusal from either stands.
SHELL_DEPENDENT_TOKENS: list[str] = [
    "\\;",
    "\\&",
    "\\|",
    "\\(",
    "\\)",
    "\\{",
    "\\<",
    "{",
    "}",
    "{}",
    "}}",
    "{ }",
]


@pytest.mark.parametrize("token", SHELL_DEPENDENT_TOKENS)
def test_violation_distrusts_a_switch_after_a_shell_dependent_token(token: str) -> None:
    # bash: the token is an argument of `echo`, so the checkout is `echo`'s
    # neighbour and runs after it; the old tokenizer trusted the `&&` anyway.
    command = f"echo {token} git checkout -b x && git commit -m x"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


@pytest.mark.parametrize("token", SHELL_DEPENDENT_TOKENS)
def test_violation_refuses_an_or_switch_after_a_shell_dependent_token(
    token: str,
) -> None:
    command = f"true || echo {token} | git checkout -b x && git commit -m x"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


# The readers' cases, each refused on the branch given: a switch hidden behind a shell-dependent token, a split
# through git's own argument list, a brace after `coproc NAME`, `time -p`, `function NAME` or a cased `DO`.
HIDDEN_SWITCH_FORMS: list[tuple[str, str, str]] = [
    ("true || echo ${x:-a\nb} | git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("true || echo \\; | git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("true || echo \\& | git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("true || echo { | git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("echo a\\;git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("echo -exec true \\; git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("echo x\r git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("true || echo \\; | git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("true || echo \\& | git checkout -b x && git commit -m x", PROTECTED, "C"),
    (
        "true || echo -exec true \\; | git checkout -b x && git commit -m x",
        PROTECTED,
        "C",
    ),
    ("true || echo { | git checkout -b x && git commit -m x", PROTECTED, "C"),
    (
        "true || echo { true || echo } | git checkout -b x && git commit -m x",
        PROTECTED,
        "C",
    ),
    ("{ true || echo \\; } | git checkout -b x && git commit -m x; }", PROTECTED, "C"),
    ("true || echo \\; { | git checkout -b x && git commit -m x", PROTECTED, "C"),
    (
        "{ true || echo ${x:-)} | git checkout -b x && git commit -m x; }",
        PROTECTED,
        "C",
    ),
    ("true || echo ${x:-a\nb} | git checkout -b x && git commit -m x", PROTECTED, "C"),
    (
        "true || coproc C { true; } | git checkout -b x && git commit -m x",
        PROTECTED,
        "C",
    ),
    ("! time -p { true; } | git checkout -b feat/x && git commit -m x", PROTECTED, "C"),
    (
        "true || time -p { true; } | git checkout -b x && git commit -m x",
        PROTECTED,
        "C",
    ),
    (
        "true || function f { true; } | git checkout -b x && git commit -m x",
        PROTECTED,
        "C",
    ),
    ("true || DO { | git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("echo { true || echo } | git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("git -c user.name=a\\;b commit -m x", PROTECTED, "C"),
    ("git push -o x\\; origin main", OTHER, "P"),
    ("git push -o { origin main", OTHER, "P"),
]


@pytest.mark.parametrize(("command", "branch", "kind"), HIDDEN_SWITCH_FORMS)
def test_violation_refuses_what_a_shell_dependent_token_could_hide(
    command: str, branch: str, kind: str
) -> None:
    assert_judged(command, branch, kind)


# Pinned on purpose: bash lands nothing here, but PowerShell reads the token differently (or the guard does not
# model a command that fails), so the command is refused. Changing one of these is a decision.
BOTH_SHELL_OVER_REFUSALS: list[tuple[str, str, str]] = [
    ("git checkout -b x \\; && git commit -m x", PROTECTED, "C"),
    ("git checkout -b x ; \\; && git commit -m x", PROTECTED, "C"),
    ("'!' git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("\\! git commit -m x", PROTECTED, "C"),
    ("x=1 if git commit -m x", PROTECTED, "C"),
    (">/dev/null ! git commit -m x", PROTECTED, "C"),
    ("sudo -n ! git commit -m x", PROTECTED, "C"),
    ('"GIT" commit -m x', PROTECTED, "C"),
    ('sudo "X=1" git commit -m x', PROTECTED, "C"),
    ("echo \\; git commit -m x", PROTECTED, "C"),
    ('true || echo ";" | git checkout main && git commit -m x', OTHER, "C"),
    ("git checkout -b feat/x2 && echo \\; && git commit -m x", PROTECTED, "C"),
    ("git checkout -b feat/x2 && echo { && git commit -m x", PROTECTED, "C"),
]


@pytest.mark.parametrize(("command", "branch", "kind"), BOTH_SHELL_OVER_REFUSALS)
def test_violation_pins_the_both_shell_over_refusals(
    command: str, branch: str, kind: str
) -> None:
    assert_judged(command, branch, kind)


# bash runs the `\r` after an `&&` as a command named `\r` that fails; PowerShell ends the line there.
# "A" rows: a quoted `\r`, a `\r` after the last command, nothing hidden.
CARRIAGE_RETURN_FORMS: list[tuple[str, str, str]] = [
    ("git checkout -b feat/x &&\r\ngit commit -m x", PROTECTED, "C"),
    ("git checkout -b feat/x &&\r\n\r\ngit commit -m x", PROTECTED, "C"),
    ("git checkout -b feat/x && \r\ngit commit -m x", PROTECTED, "C"),
    ("git checkout -b feat/y &&\r\ngit commit -m x", PROTECTED, "C"),
    ("git commit\r\n", PROTECTED, "C"),
    ("git push\r\n", PROTECTED, "P"),
    ("git push origin main\r\n", OTHER, "P"),
    ("git commit -m x\r\n", PROTECTED, "C"),
    ("git checkout -b feat/x && \\\r\ngit commit -m x", PROTECTED, "C"),
    ("git checkout -b feat/x &&\\\r\ngit commit -m x", PROTECTED, "C"),
]
CARRIAGE_RETURN_ALLOWED: list[tuple[str, str, str]] = [
    ("git checkout -b feat/x && git commit -m x\r\n", PROTECTED, "A"),
    ("git checkout -b feat/x && git commit -m 'x\r'", PROTECTED, "A"),
    ('git checkout -b feat/x && git commit -m "x\r"', PROTECTED, "A"),
    ('git checkout -b feat/x && git commit -m "a\r\nb"', PROTECTED, "A"),
]


@pytest.mark.parametrize(("command", "branch", "kind"), CARRIAGE_RETURN_FORMS)
def test_violation_does_not_trust_an_and_and_before_a_carriage_return(
    command: str, branch: str, kind: str
) -> None:
    assert_judged(command, branch, kind)


@pytest.mark.parametrize(("command", "branch", "kind"), CARRIAGE_RETURN_ALLOWED)
def test_violation_allows_a_quoted_carriage_return_and_one_after_the_last_command(
    command: str, branch: str, kind: str
) -> None:
    assert_judged(command, branch, kind)


@pytest.mark.parametrize("suffix", ["\r\n", "\r", "\n\r\n", " \r\n"])
@pytest.mark.parametrize(
    ("command", "branch", "reason"),
    [
        ("git commit -m x", PROTECTED, COMMIT_REASON),
        ("git push", PROTECTED, PUSH_REASON),
        ("git push origin main", OTHER, PUSH_REASON),
    ],
)
def test_violation_refuses_a_commit_or_push_ended_by_a_carriage_return(
    command: str, branch: str, reason: str, suffix: str
) -> None:
    assert violation(command + suffix, branch).startswith(reason)


def test_violation_refuses_a_commit_after_a_carriage_return_inside_a_word() -> None:
    assert violation(
        "echo x\r git checkout -b x && git commit -m x", PROTECTED
    ).startswith(COMMIT_REASON)


# A quoted word is not a leader, an assignment or a redirection: bash runs no git in any of these.
QUOTED_WORD_AT_COMMAND_POSITION: list[tuple[str, str, str]] = [
    ("'if' git commit -m x", PROTECTED, "A"),
    ("'!' git commit -m x", PROTECTED, "A"),
    ('"!" git commit -m x', PROTECTED, "A"),
    ('"X=1" git commit -m x', PROTECTED, "A"),
    ("'>' x git commit -m x", PROTECTED, "A"),
    ('echo ";" git commit -m x', PROTECTED, "A"),
    ('git checkout feat/y ";" git commit -m x', PROTECTED, "A"),
    ("''if git commit -m x", PROTECTED, "A"),
]
# A quoted program name, subcommand, option or ref is the word it spells; the escaped and unquoted leaders of
# round 3 stay refused. Rows needing a real `sudo`/`env` have no oracle; `'!' git checkout -b x && ...` is an
# accepted over-refusal (bash is safe only because a command named `!` fails).
QUOTED_NAMES_THAT_STILL_COUNT: list[tuple[str, str, str]] = [
    ("'!' git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("\\! git commit -m x", PROTECTED, "C"),
    ("x=1 if git commit -m x", PROTECTED, "C"),
    (">/dev/null ! git commit -m x", PROTECTED, "C"),
    ("sudo -n ! git commit -m x", PROTECTED, "C"),
    ('"git" commit -m x', PROTECTED, "C"),
    ("''git commit -m x", PROTECTED, "C"),
    ('"GIT" commit -m x', PROTECTED, "C"),
    ('git "commit" -m x', PROTECTED, "C"),
    ('"sudo" git commit -m x', PROTECTED, "C"),
    ('"time" git commit -m x', PROTECTED, "C"),
    ('sudo "-E" git commit -m x', PROTECTED, "C"),
    ('sudo "-n" git commit -m x', PROTECTED, "C"),
    ('time "-p" git commit -m x', PROTECTED, "C"),
    ('env "X=1" git commit -m x', PROTECTED, "C"),
    ('sudo "X=1" git commit -m x', PROTECTED, "C"),
    ('git "--no-pager" commit -m x', PROTECTED, "C"),
    ('git "-c" a=b commit -m x', PROTECTED, "C"),
    ('git checkout "main"; git commit -m x', OTHER, "C"),
    ('git push origin "refs/heads/main"', OTHER, "P"),
    ('git checkout "refs/heads/main" && git commit -m x', OTHER, "C"),
    ("git push origin 'HEAD:main'", PROTECTED, "P"),
    ('git push "origin" "HEAD:main"', OTHER, "P"),
    ('git push origin "+refs/heads/main"', OTHER, "P"),
    ('git checkout "-" && git commit -m x', OTHER, "U"),
    ("git checkout '@{-1}' && git commit -m x", OTHER, "U"),
    ('"/usr/bin/git" commit -m x', PROTECTED, "C"),
]


@pytest.mark.parametrize(("command", "branch", "kind"), QUOTED_WORD_AT_COMMAND_POSITION)
def test_violation_allows_a_quoted_word_at_command_position(
    command: str, branch: str, kind: str
) -> None:
    assert_judged(command, branch, kind)


@pytest.mark.parametrize(("command", "branch", "kind"), QUOTED_NAMES_THAT_STILL_COUNT)
def test_violation_still_reads_a_quoted_name_as_the_name_it_spells(
    command: str, branch: str, kind: str
) -> None:
    assert_judged(command, branch, kind)


@pytest.mark.parametrize(
    "command",
    [
        'git checkout -b "feat/x2" && git commit -m x',
        'git "checkout" "-b" "feat/x2" && git "commit" -m x',
        "git 'checkout' -b 'feat/x2' && git 'commit' -m 'x'",
        'git checkout -b feat/x2 && git commit -m "x"',
    ],
)
def test_violation_trusts_a_switch_written_with_quoted_words(command: str) -> None:
    assert violation(command, PROTECTED) == ""


MARK = guard_git._QUOTE_MARK


@pytest.mark.parametrize(
    "tokens",
    [
        (MARK + "if", "git", "commit"),
        (MARK + "!", "git", "commit"),
        (MARK + "X=1", "git", "commit"),
        (MARK + ">", "x", "git", "commit"),
        (MARK + "2", ">", "x", "git", "commit"),
        ("git", MARK),
        ("DO", "git", "commit"),
    ],
)
def test_git_subcommand_finds_no_git_behind_a_quoted_word_in_command_position(
    tokens: tuple[str, ...],
) -> None:
    assert git_subcommand(tokens) == ("", ())


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        (("!", "git", "commit", "-m", "x"), ("commit", ("-m", "x"))),
        (("if", "git", "commit"), ("commit", ())),
        (("X=1", "git", "commit"), ("commit", ())),
        ((">", "x", "git", "commit"), ("commit", ())),
        (("2", ">", "x", "git", "commit"), ("commit", ())),
        (("do", "git", "commit"), ("commit", ())),
        ((MARK + "git", "commit", "-m", "x"), ("commit", ("-m", "x"))),
        ((MARK + "/usr/bin/git", "commit"), ("commit", ())),
        (
            (
                MARK + "git",
                MARK + "-c",
                "a=b",
                MARK + "commit",
                MARK + "-m",
                MARK + "x",
            ),
            ("commit", ("-m", "x")),
        ),
        (("git", MARK + "--no-pager", "commit"), ("commit", ())),
        (("git", MARK + "-c", "a=b", "commit"), ("commit", ())),
        (("git", MARK + "-C", "d", "commit"), ("commit", ())),
        (("sudo", MARK + "-E", "git", "commit"), ("commit", ())),
        (("sudo", MARK + "-n", "!", "git", "commit"), ("commit", ())),
        ((MARK + "sudo", MARK + "-E", "git", "commit"), ("commit", ())),
        (("env", MARK + "X=1", "git", "commit"), ("commit", ())),
        ((MARK + "time", "git", "commit"), ("commit", ())),
        ((MARK + "time", MARK + "-p", "git", "commit"), ("commit", ())),
        (("git", "checkout", MARK + "main"), ("checkout", ("main",))),
    ],
)
def test_git_subcommand_returns_the_text_without_the_quote_mark(
    tokens: tuple[str, ...], expected: tuple[str, tuple[str, ...]]
) -> None:
    subcommand, args = git_subcommand(tokens)

    assert (subcommand, args) == expected
    assert MARK not in subcommand
    assert all(MARK not in arg for arg in args)


def test_git_subcommand_does_not_change_its_tokens() -> None:
    tokens = (MARK + "git", MARK + "-c", "a=b", "commit")

    git_subcommand(tokens)

    assert tokens == (MARK + "git", MARK + "-c", "a=b", "commit")


def test_git_subcommand_reads_the_quoted_leader_through_segments_as_plain_text() -> (
    None
):
    # `segments` strips the mark for display, so its tokens say nothing about
    # quoting; `violation` reads the marked tokens and allows this.
    parsed = segments("'if' git commit -m x")

    assert parsed is not None
    assert git_subcommand(parsed[0].tokens) == ("commit", ("-m", "x"))
    assert violation("'if' git commit -m x", PROTECTED) == ""


# Quote and escape state around an operator: an escaped quote, a backslash in single quotes, nesting through
# `$( )`, backticks and `${ }`, a quoted operator beside a refspec or a switch.
QUOTE_STATE_CASES: list[tuple[str, str, str]] = [
    ('echo \\"; git commit -m x', PROTECTED, "C"),
    ("echo '\\'; git commit -m x", PROTECTED, "C"),
    ('echo "\\\\"; git commit -m x', PROTECTED, "C"),
    ('echo "\\";" git commit -m x', PROTECTED, "A"),
    ("echo \\'; git commit -m x", PROTECTED, "C"),
    ('echo "it\'s ;" git commit -m x', PROTECTED, "A"),
    ("echo 'say \"a|b\"' git commit -m x", PROTECTED, "A"),
    ('echo "a" ";" "b" git commit -m x', PROTECTED, "A"),
    ('echo a";"b git commit -m x', PROTECTED, "A"),
    ('echo "$(echo ";")" git commit -m x', PROTECTED, "A"),
    ('echo "$(echo ";"; git commit -m x)"', PROTECTED, "C"),
    ('echo "`echo ";"`" git commit -m x', PROTECTED, "A"),
    ('echo "${x:-";"}" git commit -m x', PROTECTED, "A"),
    ('echo "${x:-a;b}" git commit -m x', PROTECTED, "A"),
    ('echo ${x:-";"} git commit -m x', PROTECTED, "A"),
    ("echo ${x:-\\;} git commit -m x", PROTECTED, "A"),
    ('echo $"a;b" git commit -m x', PROTECTED, "A"),
    ('true || echo $"a;b" | git checkout -b x && git commit -m x', PROTECTED, "C"),
    ('true || echo "a;" ";" | git checkout -b x && git commit -m x', PROTECTED, "C"),
    ("true || echo ';'';' | git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("true || echo \\;\\; | git checkout -b x && git commit -m x", PROTECTED, "C"),
    ('true || echo ";"; git checkout -b x && git commit -m x', PROTECTED, "A"),
    ("true || echo ; git checkout -b x && git commit -m x", PROTECTED, "A"),
    ('true || echo "a" ; git checkout -b x && git commit -m x', PROTECTED, "A"),
    ('true || echo ";" ; git checkout -b x && git commit -m x', PROTECTED, "A"),
    ('true || echo ";" && git checkout -b x && git commit -m x', PROTECTED, "A"),
    ('true || echo ";" | git checkout -b x && git commit -m x', OTHER, "A"),
    ("true || echo \\; | git checkout -b x && git commit -m x", OTHER, "A"),
    ("true || echo { | git checkout -b x && git commit -m x", OTHER, "A"),
    ("git checkout -b feat/x &&\r\ngit commit -m x", OTHER, "A"),
    ("true || echo '(' | git checkout -b x && git commit -m x", OTHER, "A"),
    ('true || echo ";" | git checkout main && git commit -m x', OTHER, "C"),
    ('echo ";" | git checkout main && git commit -m x', OTHER, "C"),
    ('git checkout main ";" git commit -m x', OTHER, "A"),
    ('git checkout main; echo ";"; git commit -m x', OTHER, "C"),
    ('git checkout main && echo ";" && git commit -m x', OTHER, "C"),
    ("git checkout main || echo ';' && git commit -m x", OTHER, "C"),
    ('git checkout -b feat/x2 && echo ";" && git commit -m x', PROTECTED, "A"),
    ("git checkout -b feat/x2 && echo \\; && git commit -m x", PROTECTED, "C"),
    ("git checkout -b feat/x2 && echo { && git commit -m x", PROTECTED, "C"),
    ("git checkout -b feat/x2 && echo x\\r && git commit -m x", PROTECTED, "A"),
    ('git push origin ";" main', OTHER, "P"),
    ('git push origin ";"; git push origin main', OTHER, "P"),
    ('git push origin main ";"', OTHER, "P"),
    ('git push origin "main;"', OTHER, "A"),
    ('git push -o ";" origin main', OTHER, "P"),
    ('git commit -m ";"', PROTECTED, "C"),
    ('git commit -m ";" && git push', PROTECTED, "C"),
    ("git commit -m \\; ", PROTECTED, "C"),
]


@pytest.mark.parametrize(("command", "branch", "kind"), QUOTE_STATE_CASES)
def test_violation_tracks_quoting_around_an_operator(
    command: str, branch: str, kind: str
) -> None:
    assert_judged(command, branch, kind)


# PowerShell only (no oracle): a bare `{` after a command word opens a scriptblock that runs. Refused today
# because the brace splits the command; round 5 must keep that.
POWERSHELL_SCRIPTBLOCKS: list[tuple[str, str, str]] = [
    ("Get-Item . | ForEach-Object { git commit -m x }", PROTECTED, "C"),
    ("Invoke-Command -ScriptBlock { git commit -m x }", PROTECTED, "C"),
    ("Start-Job { git push origin main }", OTHER, "P"),
    ("gci | % { git commit -m x }", PROTECTED, "C"),
    ("try { git commit -m x } catch { }", PROTECTED, "C"),
    ("Do { git checkout main } While ($x); git commit -m x", OTHER, "C"),
]


@pytest.mark.parametrize(("command", "branch", "kind"), POWERSHELL_SCRIPTBLOCKS)
def test_violation_refuses_a_git_command_inside_a_powershell_scriptblock(
    command: str, branch: str, kind: str
) -> None:
    assert_judged(command, branch, kind)


@pytest.mark.parametrize(
    "command",
    [
        "Get-Item . | ForEach-Object { git checkout main }; git commit -m x",
        "Do { git checkout main } While ($x); git commit -m x",
        "DO { git checkout main } WHILE ($x)\ngit commit -m x",
        "foreach ($i in 1..2) { git checkout main }; git commit -m x",
    ],
)
def test_violation_counts_a_switch_inside_a_powershell_block(command: str) -> None:
    assert violation(command, OTHER).startswith(COMMIT_REASON)


@pytest.mark.parametrize(
    "command",
    [
        'true || echo ";" | git checkout -b x && git commit -m x',
        "echo x\r git checkout -b x && git commit -m x",
        r"echo \; git checkout -b x && git commit -m x",
        "'if' git commit -m x",
        "git checkout -b feat/x2 &&\r\ngit commit -m x",
    ],
)
def test_violation_is_idempotent_for_the_round_5_forms(command: str) -> None:
    first = violation(command, PROTECTED)

    assert violation(command, PROTECTED) == first
    assert segments(command) == segments(command)


def test_violation_reads_a_long_run_of_quoted_operators_quickly() -> None:
    command = "echo " + '";" ' * 4000 + "&& git status"

    parsed = segments(command)

    assert parsed is not None
    assert len(parsed) == 2
    assert len(parsed[0].tokens) == 4001
    assert violation(command, PROTECTED) == ""


def test_violation_reads_a_long_run_of_escaped_operators_quickly() -> None:
    command = "echo " + r"\; " * 4000 + "&& git commit -m x"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_reads_a_long_or_chain_of_quoted_operators_quickly() -> None:
    command = "true" + ' || echo ";"' * 2000 + " | git checkout -b x && git commit -m x"

    assert violation(command, PROTECTED).startswith(COMMIT_REASON)


def test_violation_plays_safe_when_a_command_is_too_tangled_to_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def give_up(*_args: object, **_kwargs: object) -> object:
        raise guard_git._TooComplexError

    monkeypatch.setattr(guard_git, "_scan", give_up)
    command = 'true || echo ";" | git checkout -b x && git commit -m x'

    assert violation(command, PROTECTED).startswith(UNMODELLED_REASON)
    assert violation('echo ";" x', PROTECTED) == ""
    assert violation("git commit -m x\r\n", PROTECTED).startswith(UNMODELLED_REASON)
    assert violation(command, OTHER) == ""


# Cases the round did not set out to change, run through the same oracle: the
# commit-message, heredoc, substitution and `||` rules of rounds 1 to 4 and the
# `!` forms with a quoted operator, unchanged. `echo `;` and the `\r` before a push
# option have no oracle (PowerShell reads a backtick as an escape, and the
# shadow splits its output on `\r`).
REGRESSION_CASES: list[tuple[str, str, str]] = [
    ('! true | echo ";" | git checkout -b feat/x && git commit -m x', PROTECTED, "C"),
    ("! true | echo '|' | git checkout -b feat/x && git commit -m x", PROTECTED, "C"),
    (
        "! true | echo ${x:-;} | git checkout -b feat/x && git commit -m x",
        PROTECTED,
        "C",
    ),
    ("git push -o x\r origin main", OTHER, "P"),
    (
        'git checkout -b feat/x2 && git commit -m "a; b | c && d (e) {f}"',
        PROTECTED,
        "A",
    ),
    ('git commit -m "fix; done"', PROTECTED, "C"),
    ('echo "$(git commit -m x)"', PROTECTED, "C"),
    (
        "git checkout -b feat/x2 && git commit -m \"$(cat <<'EOF'\nTitle\n\nBody\nEOF\n)\"",
        PROTECTED,
        "A",
    ),
    ("cat <<';'\nbody\n;\ngit commit -m x", PROTECTED, "C"),
    ('cat <<";"\nbody\n;\ngit commit -m x', PROTECTED, "C"),
    ("cat <<\\;\nbody\n;\ngit commit -m x", PROTECTED, "C"),
    ("echo ${x:-\\}; git commit -m x}", PROTECTED, "A"),
    ("echo ${x:-a; git commit -m x; }", PROTECTED, "A"),
    ("echo ${x:-a; git commit -m x; }", OTHER, "A"),
    ("git status || git checkout -b x && git commit -m x", PROTECTED, "C"),
    ("git checkout -b x || git checkout feat/x && git commit -m x", PROTECTED, "A"),
    ("true || echo x | git checkout -b y && git commit -m x", PROTECTED, "C"),
    ("{ git commit -m x; }", PROTECTED, "C"),
    ("echo `;", PROTECTED, "A"),
]


@pytest.mark.parametrize(("command", "branch", "kind"), REGRESSION_CASES)
def test_violation_keeps_the_answers_of_rounds_1_to_4(
    command: str, branch: str, kind: str
) -> None:
    assert_judged(command, branch, kind)
