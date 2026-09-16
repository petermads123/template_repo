---
name: implement
description: Step 3 of the feature pipeline. Create the branch and write the production code from the plan, updating STRUCTURE.md in the same change and recording any deviation from the plan. Use once the plan is agreed; tests come later, in step 5.
argument-hint: [slug, if more than one plan exists]
model: sonnet
effort: max
---

# Step 3 — Implement

Transcribe the plan into working code. Production code only — the test suite is step 5, and
writing it now would blur the line the pipeline draws between "it exists" and "it works".

## 1. Branch

The plan file names no branch yet. Choose one now that the scope is settled, using the
convention in `CLAUDE.md` — `feat/`, `fix/`, `refactor/`, `docs/`, `test/` or `chore/` plus
a kebab-case topic:

```bash
git checkout -b feat/<topic>
```

Branch from `main` unless a plan-related branch is already checked out, in which case stay
on it. Write the name into the Branch row of the plan file — the session brief and the stop
gate both read it, and a mismatch is reported at the start of every session.

`.claude/hooks/guard_git.py` refuses commits on `main` outright, so a missed branch is
caught rather than discovered later.

## 2. Write the code

Follow the implementation guide in order. `.claude/rules/python.md` is already in context
whenever a `.py` file is open, and it is not optional: full annotations, Google docstrings,
a `main()` showcase and `__main__` guard on every module, private helpers prefixed with `_`.

The showcase has a required shape, and it is the part most often written carelessly: bind
every argument to a named variable, call on its own line, name the result, print it. Not
`print(f(1, 2))`. Where an argument takes one of a fixed set of values, list them in a
comment on the same line: `resolution = "daily"  # "daily", "weekly", "monthly"`. It is the first thing anyone reads to learn how the module is used, so
write it as the worked example it is.

Match the Public API table exactly — signature, parameter names, defaults, return type.
Step 4 compares them literally.

### What a compliant module looks like

```python
"""Compute running statistics over a stream of samples."""

from collections.abc import Iterable

_RESOLUTIONS = {"daily": 1, "weekly": 7, "monthly": 30}


def rolling_mean(samples: Iterable[float], resolution: str = "daily") -> list[float]:
    """Compute the rolling mean of a sample stream.

    Args:
        samples: The values to average over.
        resolution: Window size by name. One of "daily", "weekly" or "monthly".

    Returns:
        One mean per complete window, in order. Empty if there are fewer
        samples than the window.

    Raises:
        ValueError: If `resolution` is not a known resolution.
    """
    if resolution not in _RESOLUTIONS:
        known = ", ".join(repr(name) for name in sorted(_RESOLUTIONS))
        raise ValueError(f"resolution must be one of {known}, got {resolution!r}")
    window = _RESOLUTIONS[resolution]
    values = list(samples)
    return [
        sum(values[i : i + window]) / window for i in range(len(values) - window + 1)
    ]


def main() -> None:
    """Showcase this module's functionality."""
    samples = [1, 2, 3, 4]
    resolution = "daily"  # "daily", "weekly", "monthly"

    means = rolling_mean(samples, resolution)

    print(f"{resolution}: {means}")

    # Fewer samples than the window, so no complete window and no results.
    resolution = "weekly"

    means = rolling_mean(samples, resolution)

    print(f"{resolution}: {means}")


if __name__ == "__main__":
    main()
```

Everything the conventions ask for is in there: module docstring, full annotations, Google
sections including `Raises:`, an error message naming the offending value, a private
constant kept out of `STRUCTURE.md`, and a showcase whose inputs are named, whose choice
argument lists its values, and whose second case teaches something the first does not.

The package's own files are **not** the reference — `src/<package>/hello_world.py` is a
placeholder to delete, not an example to copy.

Do not hand-format. `.claude/hooks/lint_py.py` runs `ruff format` and `ruff check --fix` on
every file you write, and reports back only what it could not fix.

## 3. Update STRUCTURE.md

In this change, not later. Add the module section, amend the signature table, fix the entry
for anything moved or deleted. The stop gate blocks on a module missing from the file, but
it cannot see a stale signature — that part is yours.

## 4. Record the deviations

Section 3 of the plan file. Only what departed from the plan, each with its reason:

> The plan gave `export(records, path)`. Writing it showed the caller always has an open
> file handle, so the signature became `export(records, stream)` and the path-opening moved
> to `export_to_path`. The Public API table has been corrected to match.

Discovering the plan was wrong is a normal outcome of implementing it. Silently diverging
from it is not — step 4 will find the difference and will not know whether it was a
decision or a slip. **Correct the Public API table in section 2 when you deviate**, so the
plan stays the description of the code rather than a historical artefact.

If a deviation invalidates an acceptance criterion, stop and say so. That is a step 1
problem, not something to absorb here.

## 5. Do not commit

Step 7 commits, once the work has been verified, tested and checked against the concept.
Leave the tree dirty.

## Stop here

1. Mark step 3 `done` and set the marker to `<!-- claude-plan step=4 status=active -->`.
2. Report: the branch, the files added or changed, any deviation from the plan, and what
   `STRUCTURE.md` gained.
3. End the turn.

The stop gate is advisory through step 3, so a tree that does not yet pass everything can
end the turn here. From step 4 it blocks. The user opens step 4 with `/verify`.
