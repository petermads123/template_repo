import os
import subprocess
from pathlib import Path

import plan_state
import pytest
from plan_state import (
    GATE_FROM_STEP,
    Plan,
    active_plan,
    all_plans,
    current_branch,
    feature_rounds,
    git_lines,
    parse,
)

MARKER = "<!-- claude-plan step={step} status={status} -->"


def write_plan(
    root: Path,
    relative: str,
    *,
    step: int = 3,
    status: str = "active",
    title: str | None = "A feature",
    branch: str | None = "feat/topic",
) -> Path:
    path = root / "development" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if title is not None:
        lines.append(f"# {title}\n")
    lines.append(MARKER.format(step=step, status=status) + "\n")
    if branch is not None:
        lines.append("| Field | Value |\n|---|---|\n")
        lines.append(f"| Branch | `{branch}` |\n")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "seed.txt").write_text("seed", encoding="utf-8")
    git(tmp_path, "add", "seed.txt")
    git(tmp_path, "commit", "-m", "seed")
    return tmp_path


# --- Plan properties ---------------------------------------------------------


@pytest.mark.parametrize(
    ("step", "expected"),
    [(1, "Conceptualize"), (4, "Verify"), (10, "Review")],
)
def test_step_name_names_each_step(step: int, expected: str) -> None:
    plan = Plan(Path("p.md"), step, "active", "t", "", "f", 1)
    assert plan.step_name == expected


def test_step_name_is_unknown_for_a_step_out_of_range() -> None:
    plan = Plan(Path("p.md"), 99, "active", "t", "", "f", 1)
    assert plan.step_name == "unknown"


@pytest.mark.parametrize(
    ("step", "gated"),
    [(GATE_FROM_STEP - 1, False), (GATE_FROM_STEP, True), (GATE_FROM_STEP + 1, True)],
)
def test_gated_turns_on_at_the_gate_step(step: int, gated: bool) -> None:
    plan = Plan(Path("p.md"), step, "active", "t", "", "f", 1)
    assert plan.gated is gated


# --- parse -------------------------------------------------------------------


def test_parse_reads_a_complete_marker(tmp_path: Path) -> None:
    path = write_plan(tmp_path, "csv-export/01-csv-export.md", step=3, status="active")

    plan = parse(path)

    assert plan is not None
    assert (plan.step, plan.status, plan.title) == (3, "active", "A feature")
    assert (plan.branch, plan.feature, plan.round_number) == (
        "feat/topic",
        "csv-export",
        1,
    )


def test_parse_returns_none_without_a_marker(tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("# No marker here\n", encoding="utf-8")

    assert parse(path) is None


@pytest.mark.parametrize("step", [0, 11, 99])
def test_parse_rejects_a_step_outside_the_pipeline(tmp_path: Path, step: int) -> None:
    path = write_plan(tmp_path, f"f/{step}-x.md", step=step)

    assert parse(path) is None


def test_parse_lowercases_the_status(tmp_path: Path) -> None:
    path = write_plan(tmp_path, "f/01-x.md", status="ACTIVE")

    plan = parse(path)

    assert plan is not None
    assert plan.status == "active"


def test_parse_leaves_the_branch_empty_when_no_row_names_one(tmp_path: Path) -> None:
    path = write_plan(tmp_path, "f/01-x.md", branch=None)

    plan = parse(path)

    assert plan is not None
    assert plan.branch == ""


def test_parse_falls_back_to_the_filename_without_a_title(tmp_path: Path) -> None:
    path = write_plan(tmp_path, "f/01-untitled.md", title=None)

    plan = parse(path)

    assert plan is not None
    assert plan.title == "01-untitled"


def test_parse_reads_a_nested_feature_folder_as_a_relative_path(
    tmp_path: Path,
) -> None:
    path = write_plan(tmp_path, "feat/csv-export/02-streaming.md")

    plan = parse(path)

    assert plan is not None
    assert (plan.feature, plan.round_number) == ("feat/csv-export", 2)


def test_parse_falls_back_to_the_parent_name_outside_the_plans_directory(
    tmp_path: Path,
) -> None:
    path = tmp_path / "elsewhere" / "01-x.md"
    path.parent.mkdir()
    path.write_text(
        "# T\n\n<!-- claude-plan step=1 status=active -->\n", encoding="utf-8"
    )

    plan = parse(path)

    assert plan is not None
    assert plan.feature == "elsewhere"


def test_parse_reads_zero_rounds_from_an_unprefixed_filename(tmp_path: Path) -> None:
    path = write_plan(tmp_path, "TEMPLATE.md", status="template")

    plan = parse(path)

    assert plan is not None
    assert plan.round_number == 0
    assert plan.feature == ""


def test_parse_returns_none_for_an_unreadable_path(tmp_path: Path) -> None:
    assert parse(tmp_path) is None


# --- all_plans ---------------------------------------------------------------


def test_all_plans_is_empty_without_a_plans_directory(tmp_path: Path) -> None:
    assert all_plans(tmp_path) == []


def test_all_plans_recurses_into_feature_folders(tmp_path: Path) -> None:
    write_plan(tmp_path, "one/01-one.md")
    write_plan(tmp_path, "two/01-two.md")
    write_plan(tmp_path, "TEMPLATE.md", status="template")

    found = {plan.path.name for plan in all_plans(tmp_path)}

    assert found == {"01-one.md", "01-two.md", "TEMPLATE.md"}


def test_all_plans_orders_most_recently_modified_first(tmp_path: Path) -> None:
    old = write_plan(tmp_path, "f/01-old.md")
    new = write_plan(tmp_path, "f/02-new.md")
    os.utime(old, (1_000_000, 1_000_000))
    os.utime(new, (2_000_000, 2_000_000))

    assert [plan.path.name for plan in all_plans(tmp_path)] == [
        "02-new.md",
        "01-old.md",
    ]


def test_all_plans_skips_files_without_a_marker(tmp_path: Path) -> None:
    write_plan(tmp_path, "f/01-real.md")
    (tmp_path / "development" / "README.md").write_text("prose", encoding="utf-8")

    assert [plan.path.name for plan in all_plans(tmp_path)] == ["01-real.md"]


def test_all_plans_reports_paths_relative_to_the_project(tmp_path: Path) -> None:
    write_plan(tmp_path, "f/01-x.md")

    (plan,) = all_plans(tmp_path)

    assert plan.path == Path("development/f/01-x.md")


# --- active_plan -------------------------------------------------------------


def test_active_plan_is_none_when_nothing_is_active(tmp_path: Path) -> None:
    write_plan(tmp_path, "f/01-x.md", status="done")
    write_plan(tmp_path, "TEMPLATE.md", status="template")

    assert active_plan(tmp_path) is None


def test_active_plan_finds_the_one_active_file(tmp_path: Path) -> None:
    write_plan(tmp_path, "f/01-done.md", status="done")
    write_plan(tmp_path, "f/02-live.md", status="active")

    plan = active_plan(tmp_path)

    assert plan is not None
    assert plan.path.name == "02-live.md"


def test_active_plan_prefers_the_most_recent_of_several_active(tmp_path: Path) -> None:
    older = write_plan(tmp_path, "f/01-older.md", status="active")
    newer = write_plan(tmp_path, "g/01-newer.md", status="active")
    os.utime(older, (1_000_000, 1_000_000))
    os.utime(newer, (2_000_000, 2_000_000))

    plan = active_plan(tmp_path)

    assert plan is not None
    assert plan.path.name == "01-newer.md"


# --- feature_rounds ----------------------------------------------------------


def test_feature_rounds_orders_oldest_first(tmp_path: Path) -> None:
    third = write_plan(tmp_path, "csv/03-third.md")
    first = write_plan(tmp_path, "csv/01-first.md")
    write_plan(tmp_path, "csv/02-second.md")
    os.utime(third, (2_000_000, 2_000_000))
    os.utime(first, (1_000_000, 1_000_000))

    rounds = feature_rounds(tmp_path, "csv")

    assert [plan.round_number for plan in rounds] == [1, 2, 3]


def test_feature_rounds_matches_a_nested_feature_folder(tmp_path: Path) -> None:
    write_plan(tmp_path, "feat/csv/01-x.md")
    write_plan(tmp_path, "feat/csv/02-y.md")
    write_plan(tmp_path, "fix/csv/01-z.md")

    rounds = feature_rounds(tmp_path, "feat/csv")

    assert [plan.path.name for plan in rounds] == ["01-x.md", "02-y.md"]


def test_feature_rounds_excludes_other_features(tmp_path: Path) -> None:
    write_plan(tmp_path, "csv/01-x.md")
    write_plan(tmp_path, "other/01-y.md")

    rounds = feature_rounds(tmp_path, "csv")

    assert [plan.path.name for plan in rounds] == ["01-x.md"]


def test_feature_rounds_is_empty_for_an_unknown_feature(tmp_path: Path) -> None:
    write_plan(tmp_path, "csv/01-x.md")

    assert feature_rounds(tmp_path, "nope") == []


# --- git_lines and current_branch --------------------------------------------


def test_git_lines_returns_output_lines(repo: Path) -> None:
    assert git_lines(repo, ["branch", "--show-current"]) == ["main"]


def test_git_lines_drops_blank_lines(repo: Path) -> None:
    lines = git_lines(repo, ["log", "--format=%n%s%n"])

    assert lines == ["seed"]


def test_git_lines_is_empty_when_git_fails(repo: Path) -> None:
    assert git_lines(repo, ["rev-parse", "does-not-exist"]) == []


def test_git_lines_is_empty_outside_a_repository(tmp_path: Path) -> None:
    assert git_lines(tmp_path, ["branch", "--show-current"]) == []


def test_current_branch_names_the_checked_out_branch(repo: Path) -> None:
    assert current_branch(repo) == "main"


def test_current_branch_follows_a_switch(repo: Path) -> None:
    git(repo, "checkout", "-b", "feat/topic")

    assert current_branch(repo) == "feat/topic"


def test_current_branch_is_empty_on_a_detached_head(repo: Path) -> None:
    git(repo, "checkout", "--detach", "HEAD")

    assert current_branch(repo) == ""


def test_current_branch_is_empty_outside_a_repository(tmp_path: Path) -> None:
    assert current_branch(tmp_path) == ""


# --- main --------------------------------------------------------------------


def test_main_reports_the_plans_it_finds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_plan(tmp_path, "csv-export/01-csv-export.md", status="active")
    monkeypatch.chdir(tmp_path)

    plan_state.main()

    output = capsys.readouterr().out
    assert "01-csv-export.md" in output
    assert "active" in output
    assert f"the stop gate blocks from step {GATE_FROM_STEP}" in output


def test_main_is_quiet_about_rounds_when_nothing_is_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_plan(tmp_path, "csv-export/01-csv-export.md", status="done")
    monkeypatch.chdir(tmp_path)

    plan_state.main()

    output = capsys.readouterr().out
    assert "active: None" in output
    assert "rounds of" not in output
