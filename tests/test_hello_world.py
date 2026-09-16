import pytest

from template_repo.hello_world import main


def test_main_prints_hello_world(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    assert capsys.readouterr().out == "Hello, World!\n"


def test_main_prints_exactly_one_line(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    assert capsys.readouterr().out.count("\n") == 1


def test_main_writes_nothing_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    assert capsys.readouterr().err == ""


def test_main_is_repeatable(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    first = capsys.readouterr().out
    main()
    assert capsys.readouterr().out == first
