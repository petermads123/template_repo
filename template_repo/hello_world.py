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
    # The normal case: greet someone by name.
    name = "Peter"

    greeting = greet(name)

    print(f"named:     {greeting}")

    # No argument, so the default applies.
    default_greeting = greet()

    print(f"default:   {default_greeting}")

    # Non-ASCII input, returned exactly as given.
    name = "Ærø"

    greeting = greet(name)

    print(f"non-ASCII: {greeting}")


if __name__ == "__main__":
    main()
