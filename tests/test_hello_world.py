import pytest

from template_repo import greet


def test_greet_defaults_to_world() -> None:
    assert greet() == "Hello, World!"


def test_greet_uses_given_name() -> None:
    assert greet("Peter") == "Hello, Peter!"


def test_greet_accepts_empty_string() -> None:
    assert greet("") == "Hello, !"


def test_greet_preserves_unicode() -> None:
    assert greet("Ærø") == "Hello, Ærø!"


def test_greet_preserves_surrounding_whitespace() -> None:
    assert greet("  Peter  ") == "Hello,   Peter  !"


def test_greet_handles_long_input() -> None:
    name = "a" * 10_000
    assert greet(name) == f"Hello, {name}!"


@pytest.mark.parametrize("name", ["Peter", "", "Ærø", "123"])
def test_greet_is_deterministic(name: str) -> None:
    assert greet(name) == greet(name)
