---
name: implement
description: Step 3 of the feature pipeline. Write the production code from the plan, updating STRUCTURE.md in the same change, recording any deviation from the plan, and committing. Runs inside /build as a subagent; tests come later, in step 5.
argument-hint: [slug, if more than one plan exists]
model: sonnet
effort: max
---

# Step 3 — Implement

Transcribe the plan into working code. Production code only — the test suite is step 5, and
writing it now would blur the line the pipeline draws between "it exists" and "it works".
The one exception is a fix round's reproduction test, written first and run red, because a
fix does not "exist" until the reproduction fails; section 1a below.

This step runs unattended, as a subagent of `/build`. Nobody answers a question asked here.
What the plan settles, do; what it does not settle and section 1 does not either, halt on —
the rules are in `/build` and repeated in your brief. Do not guess.

## 1. Check the branch

The branch was created at step 1 and is named in the Branch row of the plan file. Confirm
it is checked out:

```bash
git branch --show-current
```

A mismatch is a halt, not something to fix by switching — the build is on the wrong branch,
and only the user knows which one is right. `.claude/hooks/guard_git.py` refuses commits on
`main` outright, so a missed branch is caught rather than discovered later.

## 1a. On a fix round, reproduce before you fix

Section 1 carries a filled **Defect** block — every round in a `fix/` folder, and a later
round opened on a bug report. Before touching production code:

1. Write the Reproduction row as **one** test in `tests/test_<module>.py`, named for the
   promise it proves — `test_violation_refuses_a_commit_whose_message_carries_punctuation`,
   not `test_bug`. No edge cases; those are step 5's. Read `.claude/rules/python.md`
   first, as for any `.py` file.
2. Run only that test:

   ```bash
   pytest tests/test_<module>.py -k <test_name>
   ```

   **It must fail**, and fail the way the Defect block's Observed row says. Paste the
   failure into section 3, verbatim: it is the evidence step 6 cites for the first
   criterion, and it is the only moment the bug is ever seen red.
3. Then fix, following the implementation guide, and run the same test green.

A reproduction that passes before the fix means the diagnosis is wrong or the test does not
reproduce the symptom — either way section 1 is wrong, and that is a **halt**, not a test to
adjust until it fails. A failure of a different shape from the one the Defect block
describes is the same halt. Step 5 extends this file and leaves this test as written.

## 2. Write the code

Follow the implementation guide in order. `.claude/rules/python.md` is not optional: full
annotations, Google docstrings, a `main()` showcase and `__main__` guard on every module,
private helpers prefixed with `_`. Read it before the first `.py` file — a subagent does not
get it loaded automatically.

The showcase has a required shape, and it is the part most often written carelessly: bind
every argument to a named variable, call on its own line, name the result, print it. Not
`print(f(1, 2))`. Where an argument takes one of a fixed set of values, list them in a
comment on the same line: `resolution = "daily"  # "daily", "weekly", "monthly"`. It is the
first thing anyone reads to learn how the module is used, so write it as the worked example
it is.

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

If a deviation invalidates an acceptance criterion, that is a step 1 problem: **halt**.
Report it with the criterion it breaks and what you would have needed decided.

## 5. Commit and push

The code, `STRUCTURE.md` and the plan file — and on a fix round the reproduction test — in
one commit unless the work genuinely separates. Subject in the imperative, under 72
characters, saying what changes rather than what you did — `Add CSV export for record
collections` — with the round file named in the body. Then push. The tree must be clean
when this step ends: a step that leaves work uncommitted leaves nothing for the next
session to resume from.

The tree does not have to be green yet. Step 4 runs the tools; the stop gate is advisory
through step 7 for exactly this reason.

## Stop here

1. Mark step 3 `done` and set the marker to `<!-- claude-plan step=4 status=active -->`.
   That edit goes in the commit above.
2. Report, in the `/build` contract: `STATUS`, and a `TRACE` with one or two lines per
   module, class and function added or changed — every one of them, named — plus what
   `STRUCTURE.md` gained and any deviation from the plan.
3. End. `/build` opens step 4; do not.
