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


@pytest.mark.parametrize(
    ("style", "expected"),
    [
        ("friendly", "Hello, Peter!"),
        ("formal", "Good day, Peter."),
        ("casual", "Hey Peter!"),
    ],
)
def test_greet_applies_each_style(style: str, expected: str) -> None:
    assert greet("Peter", style) == expected


def test_greet_defaults_to_the_friendly_style() -> None:
    assert greet("Peter") == greet("Peter", "friendly")


def test_greet_rejects_an_unknown_style() -> None:
    with pytest.raises(ValueError, match="style must be one of"):
        greet("Peter", "enthusiastic")


def test_greet_error_names_the_offending_style() -> None:
    with pytest.raises(ValueError, match="enthusiastic"):
        greet("Peter", "enthusiastic")


def test_greet_style_is_case_sensitive() -> None:
    with pytest.raises(ValueError):
        greet("Peter", "Friendly")


def test_greet_rejects_an_empty_style() -> None:
    with pytest.raises(ValueError):
        greet("Peter", "")


def test_greet_rejects_a_none_style() -> None:
    with pytest.raises(ValueError):
        greet("Peter", None)  # type: ignore[arg-type]  # untyped callers reach this


def test_greet_styles_are_independent_of_name() -> None:
    assert greet("", "formal") == "Good day, ."
    assert greet("Ærø", "casual") == "Hey Ærø!"
