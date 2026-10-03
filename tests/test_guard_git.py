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
