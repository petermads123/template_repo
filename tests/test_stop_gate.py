import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
import stop_gate
from plan_state import Plan
from stop_gate import (
    advisory_notes,
    block,
    capture,
    changed_python_files,
    gate_failures,
    missing_init_files,
    notice,
    stray_test_files,
    structure_problems,
    tracked_python_files,
    venv_tool,
)


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


def plan_at(step: int, *, branch: str = "") -> Plan:
    return Plan(
        Path("development/f/01-x.md"), step, "active", "A feature", branch, "f", 1
    )


# --- venv_tool ---------------------------------------------------------------


def test_venv_tool_finds_the_posix_layout(tmp_path: Path) -> None:
    tool = tmp_path / ".venv" / "bin" / "ruff"
    tool.parent.mkdir(parents=True)
    tool.touch()

    assert venv_tool(tmp_path, "ruff") == tool


def test_venv_tool_finds_the_windows_layout(tmp_path: Path) -> None:
    tool = tmp_path / ".venv" / "Scripts" / "ruff.exe"
    tool.parent.mkdir(parents=True)
    tool.touch()

    assert venv_tool(tmp_path, "ruff") == tool


def test_venv_tool_prefers_windows_when_both_exist(tmp_path: Path) -> None:
    windows = tmp_path / ".venv" / "Scripts" / "ruff.exe"
    windows.parent.mkdir(parents=True)
    windows.touch()
    posix = tmp_path / ".venv" / "bin" / "ruff"
    posix.parent.mkdir(parents=True)
    posix.touch()

    assert venv_tool(tmp_path, "ruff") == windows


def test_venv_tool_is_none_without_a_venv(tmp_path: Path) -> None:
    assert venv_tool(tmp_path, "ruff") is None


def test_venv_tool_is_none_for_a_tool_the_venv_lacks(tmp_path: Path) -> None:
    (tmp_path / ".venv" / "bin").mkdir(parents=True)

    assert venv_tool(tmp_path, "ruff") is None


# --- capture -----------------------------------------------------------------


def test_capture_returns_stdout_as_text(tmp_path: Path) -> None:
    result = capture([sys.executable, "-c", "print('hi')"], tmp_path, 30)

    assert result.returncode == 0
    assert result.stdout.strip() == "hi"


def test_capture_reports_a_failing_command(tmp_path: Path) -> None:
    result = capture([sys.executable, "-c", "raise SystemExit(3)"], tmp_path, 30)

    assert result.returncode == 3


def test_capture_raises_when_the_timeout_expires(tmp_path: Path) -> None:
    with pytest.raises(subprocess.TimeoutExpired):
        capture([sys.executable, "-c", "import time; time.sleep(30)"], tmp_path, 1)


# --- changed_python_files and tracked_python_files ---------------------------


def test_changed_python_files_sees_an_untracked_module(repo: Path) -> None:
    (repo / "new.py").write_text("x = 1\n", encoding="utf-8")

    assert changed_python_files(repo) == {"new.py"}


def test_changed_python_files_ignores_other_extensions(repo: Path) -> None:
    (repo / "notes.md").write_text("prose\n", encoding="utf-8")

    assert changed_python_files(repo) == set()


def test_changed_python_files_follows_a_rename(repo: Path) -> None:
    (repo / "before.py").write_text("x = 1\n", encoding="utf-8")
    git(repo, "add", "before.py")
    git(repo, "commit", "-m", "add")
    git(repo, "mv", "before.py", "after.py")

    assert "after.py" in changed_python_files(repo)


def test_changed_python_files_includes_commits_made_on_a_branch(repo: Path) -> None:
    git(repo, "checkout", "-b", "feat/topic")
    (repo / "committed.py").write_text("x = 1\n", encoding="utf-8")
    git(repo, "add", "committed.py")
    git(repo, "commit", "-m", "work")

    assert changed_python_files(repo) == {"committed.py"}


def test_changed_python_files_is_empty_on_a_clean_main(repo: Path) -> None:
    assert changed_python_files(repo) == set()


def test_tracked_python_files_lists_committed_and_untracked(repo: Path) -> None:
    (repo / "tracked.py").write_text("x = 1\n", encoding="utf-8")
    git(repo, "add", "tracked.py")
    git(repo, "commit", "-m", "add")
    (repo / "loose.py").write_text("y = 2\n", encoding="utf-8")

    assert tracked_python_files(repo) == {"tracked.py", "loose.py"}


def test_tracked_python_files_honours_gitignore(repo: Path) -> None:
    (repo / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (repo / "ignored.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "kept.py").write_text("y = 2\n", encoding="utf-8")

    assert tracked_python_files(repo) == {"kept.py"}


# --- structure_problems ------------------------------------------------------


def test_structure_problems_reports_a_missing_structure_file(repo: Path) -> None:
    problems = structure_problems(repo)

    assert problems == ["STRUCTURE.md is missing from the repo root."]


def test_structure_problems_reports_a_module_not_mentioned(repo: Path) -> None:
    (repo / "STRUCTURE.md").write_text("# Structure\n", encoding="utf-8")
    (repo / "orphan.py").write_text("x = 1\n", encoding="utf-8")

    problems = structure_problems(repo)

    assert any("orphan.py" in p and "exists on disk" in p for p in problems)


def test_structure_problems_reports_a_mention_of_a_deleted_file(repo: Path) -> None:
    (repo / "STRUCTURE.md").write_text(
        "# Structure\n\nSee `src/pkg/gone.py` for details.\n", encoding="utf-8"
    )

    problems = structure_problems(repo)

    assert any("src/pkg/gone.py" in p and "no longer exists" in p for p in problems)


def test_structure_problems_ignores_placeholder_paths(repo: Path) -> None:
    (repo / "STRUCTURE.md").write_text(
        "# Structure\n\nRun `src/<package>/module.py` standalone.\n", encoding="utf-8"
    )

    assert structure_problems(repo) == []


def test_structure_problems_is_empty_when_the_two_agree(repo: Path) -> None:
    (repo / "real.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "STRUCTURE.md").write_text(
        "# Structure\n\nThe module `real.py` does the work.\n", encoding="utf-8"
    )

    assert structure_problems(repo) == []


# --- stray_test_files --------------------------------------------------------


def test_stray_test_files_reports_a_test_outside_the_test_directory(repo: Path) -> None:
    (repo / "test_loose.py").write_text("x = 1\n", encoding="utf-8")

    problems = stray_test_files(repo)

    assert any("test_loose.py" in p for p in problems)


def test_stray_test_files_reports_the_suffix_form(repo: Path) -> None:
    (repo / "thing_test.py").write_text("x = 1\n", encoding="utf-8")

    problems = stray_test_files(repo)

    assert any("thing_test.py" in p for p in problems)


def test_stray_test_files_accepts_a_test_inside_the_test_directory(repo: Path) -> None:
    (repo / "tests").mkdir()
    (repo / "tests" / "test_fine.py").write_text("x = 1\n", encoding="utf-8")

    assert stray_test_files(repo) == []


def test_stray_test_files_ignores_a_module_that_merely_mentions_test(
    repo: Path,
) -> None:
    (repo / "latest.py").write_text("x = 1\n", encoding="utf-8")

    assert stray_test_files(repo) == []


# --- missing_init_files ------------------------------------------------------


def test_missing_init_files_reports_a_package_without_one(repo: Path) -> None:
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "src" / "pkg" / "module.py").write_text("x = 1\n", encoding="utf-8")

    problems = missing_init_files(repo)

    assert any("src/pkg" in p for p in problems)


def test_missing_init_files_accepts_a_package_with_one(repo: Path) -> None:
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "src" / "pkg" / "module.py").write_text("x = 1\n", encoding="utf-8")

    assert missing_init_files(repo) == []


def test_missing_init_files_ignores_directories_outside_src(repo: Path) -> None:
    (repo / "scripts").mkdir()
    (repo / "scripts" / "tool.py").write_text("x = 1\n", encoding="utf-8")

    assert missing_init_files(repo) == []


# --- gate_failures -----------------------------------------------------------


def test_gate_failures_reports_a_tool_the_venv_lacks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stop_gate, "venv_tool", lambda *_: None)

    failures = gate_failures(tmp_path)

    assert len(failures) == 4
    assert all("is not installed" in failure for failure in failures)


def test_gate_failures_is_empty_when_every_tool_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stop_gate, "venv_tool", lambda _project, name: Path(name))
    monkeypatch.setattr(
        stop_gate,
        "capture",
        lambda cmd, *_: subprocess.CompletedProcess(cmd, 0, "", ""),
    )

    assert gate_failures(tmp_path) == []


def test_gate_failures_includes_the_output_of_a_failing_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stop_gate, "venv_tool", lambda _project, name: Path(name))
    monkeypatch.setattr(
        stop_gate,
        "capture",
        lambda cmd, *_: subprocess.CompletedProcess(cmd, 1, "boom", ""),
    )

    failures = gate_failures(tmp_path)

    assert len(failures) == 4
    assert all("boom" in failure for failure in failures)


def test_gate_failures_survives_a_tool_that_cannot_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*_: object) -> None:
        raise OSError("no such executable")

    monkeypatch.setattr(stop_gate, "venv_tool", lambda _project, name: Path(name))
    monkeypatch.setattr(stop_gate, "capture", explode)

    failures = gate_failures(tmp_path)

    assert all("could not be run" in failure for failure in failures)


# --- advisory_notes ----------------------------------------------------------


def test_advisory_notes_always_names_the_step_and_the_gate(repo: Path) -> None:
    notes = advisory_notes(repo, plan_at(2), set())

    assert "step 2" in notes[0]
    assert "gate starts at step" in notes[0]


def test_advisory_notes_flags_python_changed_while_planning(repo: Path) -> None:
    notes = advisory_notes(repo, plan_at(2), {"a.py"})

    assert any("changed during a planning step" in note for note in notes)


def test_advisory_notes_stays_quiet_about_python_after_planning(repo: Path) -> None:
    notes = advisory_notes(repo, plan_at(3), {"a.py"})

    assert not any("planning step" in note for note in notes)


def test_advisory_notes_flags_a_branch_mismatch(repo: Path) -> None:
    notes = advisory_notes(repo, plan_at(3, branch="feat/other"), set())

    assert any("feat/other" in note and "main" in note for note in notes)


def test_advisory_notes_is_quiet_when_the_branch_matches(repo: Path) -> None:
    notes = advisory_notes(repo, plan_at(3, branch="main"), set())

    assert not any("is checked out" in note for note in notes)


# --- notice and block --------------------------------------------------------


def test_notice_emits_a_system_message_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        notice("look at this")

    assert exit_info.value.code == 0
    assert json.loads(capsys.readouterr().out) == {"systemMessage": "look at this"}


def test_block_emits_a_block_decision_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        block("not yet")

    assert exit_info.value.code == 0
    assert json.loads(capsys.readouterr().out) == {
        "decision": "block",
        "reason": "not yet",
    }


# --- enforce -----------------------------------------------------------------


def test_enforce_blocks_when_a_check_reports_a_problem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(stop_gate, "gate_failures", lambda _project: ["ruff failed"])
    monkeypatch.setattr(stop_gate, "structure_problems", lambda _project: [])
    monkeypatch.setattr(stop_gate, "stray_test_files", lambda _project: [])
    monkeypatch.setattr(stop_gate, "missing_init_files", lambda _project: [])

    with pytest.raises(SystemExit) as exit_info:
        stop_gate.enforce(tmp_path)

    assert exit_info.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "ruff failed" in payload["reason"]


def test_enforce_gathers_problems_from_every_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(stop_gate, "gate_failures", lambda _project: ["a"])
    monkeypatch.setattr(stop_gate, "structure_problems", lambda _project: ["b"])
    monkeypatch.setattr(stop_gate, "stray_test_files", lambda _project: ["c"])
    monkeypatch.setattr(stop_gate, "missing_init_files", lambda _project: ["d"])

    with pytest.raises(SystemExit):
        stop_gate.enforce(tmp_path)

    reason = json.loads(capsys.readouterr().out)["reason"]
    assert all(problem in reason for problem in "abcd")


def test_enforce_returns_quietly_when_everything_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in (
        "gate_failures",
        "structure_problems",
        "stray_test_files",
        "missing_init_files",
    ):
        monkeypatch.setattr(stop_gate, name, lambda _project: [])

    stop_gate.enforce(tmp_path)

    assert capsys.readouterr().out == ""


# --- main --------------------------------------------------------------------


def feed(monkeypatch: pytest.MonkeyPatch, payload: str) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))


def test_main_exits_zero_on_an_unreadable_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed(monkeypatch, "{not json")

    with pytest.raises(SystemExit) as exit_info:
        stop_gate.main()

    assert exit_info.value.code == 0


def test_main_does_not_loop_when_already_blocked_once(
    monkeypatch: pytest.MonkeyPatch, repo: Path
) -> None:
    called = False

    def record(_project: Path) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(stop_gate, "enforce", record)
    feed(monkeypatch, json.dumps({"stop_hook_active": True, "cwd": str(repo)}))

    with pytest.raises(SystemExit):
        stop_gate.main()

    assert called is False


def test_main_respects_the_skip_gate_file(
    monkeypatch: pytest.MonkeyPatch, repo: Path
) -> None:
    (repo / ".claude").mkdir()
    (repo / ".claude" / ".skip-gate").touch()
    called = False

    def record(_project: Path) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(stop_gate, "enforce", record)
    feed(monkeypatch, json.dumps({"cwd": str(repo)}))

    with pytest.raises(SystemExit):
        stop_gate.main()

    assert called is False


def test_main_enforces_with_no_plan_and_python_changed(
    monkeypatch: pytest.MonkeyPatch, repo: Path
) -> None:
    (repo / "new.py").write_text("x = 1\n", encoding="utf-8")
    called = False

    def record(_project: Path) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(stop_gate, "enforce", record)
    feed(monkeypatch, json.dumps({"cwd": str(repo)}))

    with pytest.raises(SystemExit):
        stop_gate.main()

    assert called is True


def test_main_is_advisory_below_the_gate_step(
    monkeypatch: pytest.MonkeyPatch, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plans = repo / "development" / "f"
    plans.mkdir(parents=True)
    (plans / "01-x.md").write_text(
        "# A feature\n\n<!-- claude-plan step=2 status=active -->\n", encoding="utf-8"
    )
    feed(monkeypatch, json.dumps({"cwd": str(repo)}))

    with pytest.raises(SystemExit) as exit_info:
        stop_gate.main()

    assert exit_info.value.code == 0
    assert "systemMessage" in json.loads(capsys.readouterr().out)
