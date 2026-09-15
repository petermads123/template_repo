"""Example module. Replace with real code."""

# Private, so it stays out of STRUCTURE.md: the styles are reachable through
# greet(), and listing an implementation detail there is what makes it rot.
_GREETINGS = {
    "friendly": "Hello, {name}!",
    "formal": "Good day, {name}.",
    "casual": "Hey {name}!",
}


def greet(name: str = "World", style: str = "friendly") -> str:
    """Build a greeting.

    Args:
        name: Who to greet.
        style: Which wording to use. One of "friendly", "formal" or "casual".

    Returns:
        The greeting.

    Raises:
        ValueError: If `style` is not one of the known styles.
    """
    if style not in _GREETINGS:
        known = ", ".join(repr(known_style) for known_style in sorted(_GREETINGS))
        raise ValueError(f"style must be one of {known}, got {style!r}")
    return _GREETINGS[style].format(name=name)


def main() -> None:
    """Showcase this module's functionality."""
    # The normal case: a name and a style.
    name = "Peter"
    style = "friendly"  # "friendly", "formal", "casual"

    greeting = greet(name, style)

    print(f"friendly:  {greeting}")

    # The same name, a different style.
    style = "formal"

    greeting = greet(name, style)

    print(f"formal:    {greeting}")

    # The default style, and non-ASCII text returned exactly as given.
    name = "Ærø"

    greeting = greet(name)

    print(f"default:   {greeting}")


if __name__ == "__main__":
    main()
