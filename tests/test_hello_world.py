from template_repo import greet


def test_greet_defaults_to_world() -> None:
    assert greet() == "Hello, World!"


def test_greet_uses_given_name() -> None:
    assert greet("Peter") == "Hello, Peter!"
