"""Example module. Replace with real code."""


def greet(name: str = "World") -> str:
    """Build a greeting.

    Args:
        name: Who to greet.

    Returns:
        The greeting.
    """
    return f"Hello, {name}!"


def main() -> None:
    """Showcase this module's functionality."""
    print(greet())
    print(greet("Peter"))
    print(greet("Ærø"))


if __name__ == "__main__":
    main()
