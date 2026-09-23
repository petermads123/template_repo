import io
import json
import subprocess
from pathlib import Path

import guard_git
import pytest
from guard_git import (
    PROTECTED,
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


def test_violation_does_not_carry_an_unresolvable_switch_across_a_weak_join() -> None:
    # `;` does not guarantee the switch ran, so the branch is the real one.
    assert not refused('git checkout - ; git commit -m "m"', OTHER)


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
