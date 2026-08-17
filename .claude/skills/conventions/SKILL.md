---
name: conventions
description: The long-form coding conventions reference for this repo, with worked examples of a compliant module, good vs. bad main() showcases, and the edge-case catalogue for tests. Use when discussing, explaining or auditing the conventions themselves, or when a convention question comes up that the always-on rule does not answer.
---

# Conventions reference

The enforceable rules live in `.claude/rules/python.md` and are already in context whenever
a `.py` file is open. This file is the explanation and the examples.

## A fully compliant module

```python
"""Compute running statistics over a stream of samples."""

from collections.abc import Iterable


def rolling_mean(samples: Iterable[float], window: int) -> list[float]:
    """Compute the rolling mean of a sample stream.

    Args:
        samples: The values to average over.
        window: Number of samples per window. Must be positive.

    Returns:
        One mean per complete window, in order. Empty if there are fewer
        samples than `window`.

    Raises:
        ValueError: If `window` is not positive.
    """
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")
    values = list(samples)
    return [
        sum(values[i : i + window]) / window for i in range(len(values) - window + 1)
    ]


def main() -> None:
    """Showcase this module's functionality."""
    print(rolling_mean([1, 2, 3, 4], window=2))
    print(rolling_mean([1, 2], window=5))


if __name__ == "__main__":
    main()
```

Note what makes it compliant: module docstring, full annotations, Google sections including
`Raises:`, an error message that includes the offending value, and a `main()` that shows the
normal case *and* an interesting edge (fewer samples than the window).

## `main()`: good vs. bad

**Good** — a few representative calls, printed, readable at a glance:

```python
def main() -> None:
    """Showcase this module's functionality."""
    print(rolling_mean([1, 2, 3, 4], window=2))
    print(rolling_mean([1, 2], window=5))
```

**Bad** — this is a test suite wearing a showcase costume. Assertions belong in `tests/`:

```python
def main() -> None:
    """Showcase this module's functionality."""
    assert rolling_mean([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]
    for window in range(1, 100):
        ...
```

**Also bad** — proves nothing a reader can see:

```python
def main() -> None:
    """Showcase this module's functionality."""
    rolling_mean([1, 2, 3], 2)
```

The test: could someone run `python -m package.module` and understand what the module does
from the output alone? If not, the showcase is not doing its job.

## Edge cases, with examples

The checklist in the rule, made concrete. For `rolling_mean(samples, window)`:

| Category | Concrete case | Expectation |
|---|---|---|
| Empty | `rolling_mean([], 3)` | `[]`, not a crash |
| Boundaries | `window == len(samples)` | exactly one result |
| Boundaries | `window == len(samples) + 1` | `[]` |
| Numbers | `window=0`, `window=-1` | `ValueError` |
| Numbers | very large values | no overflow, precision documented |
| Purity | pass a list, then check it | caller's list unchanged |
| Idempotency | call twice with the same input | identical results |
| Failure | every `Raises:` branch | the documented exception type |

When you want this done for you, hand the function to the `test-designer` subagent — it
returns a ranked list of cases with concrete inputs and expected results, and you write
them up.

## Running the tools

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

`ruff format` (no `--check`) rewrites files. The `PostToolUse` hook already runs it on every
`.py` file Claude edits, so formatting failures should not reach you.
