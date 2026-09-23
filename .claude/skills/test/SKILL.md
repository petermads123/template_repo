---
name: test
description: Step 5 of the feature pipeline. Turn the plan's test intents into a concrete pytest suite, hunting edge cases — empty, boundary, unicode, missing and malformed input — then fix what the tests expose and re-run the static checks. Runs inside /build as a subagent, after verification passes.
argument-hint: [slug, if more than one plan exists]
model: sonnet
effort: max
---

# Step 5 — Test

The dynamic half. Step 4 proved the code is well-formed and matches the plan; this step
proves it actually works, including when it is handed things it did not expect.

This step runs unattended, as a subagent of `/build`. Bugs are yours to fix. A case the
concept never decided is not — it is a halt, and the rules for both are in `/build` and in
your brief.

## 1. Find the cases

For each public function, delegate edge-case discovery rather than guessing at it — to two
designers at once, with different briefs, so the list is not one reader's blind spots:

```
Agent with subagent_type: "test-designer"   brief: input-space
Agent with subagent_type: "test-designer"   brief: contract
```

Both are read-only, so run them in parallel. Give each the signature, the docstring, the
body, the plan file's path, and its brief by name; ask each for at most fifteen cases — a
longer list is padding. On a fix round, also point both at the Defect block: its Class row
is the input-space designer's starting list, and its Expected row names the promise the
contract designer works from. The **input-space** designer works the parameters: limits,
either side of them, shapes the author did not imagine. The **contract** designer works
the promises: the docstring, the `Raises:`, the acceptance criteria that name the function,
and what its callers rely on. Each returns a ranked list of concrete inputs with expected
results, plus any contradiction it found between what the function promises and what it
does.

Merge the two lists: drop duplicates, keep the sharper of two cases that prove the same
thing, and keep every contradiction from either — a contradiction only one designer saw is
exactly why there are two. **You** write the test code — the agents are read-only, so the
suite stays in one voice.

Its findings go through this checklist, which is the repo's standard. Include every row
that applies to the function in front of you:

| Category | Probe |
|---|---|
| Empty | empty string, empty list or dict, zero |
| Boundaries | first, last, and one either side of every limit in the code |
| Numbers | negative, very large, float precision, division by zero |
| Missing | `None` wherever the type allows it, omitted defaults, absent keys |
| Malformed | wrong type, wrong shape, unparseable text, truncated input |
| Text | non-ASCII, leading and trailing whitespace, very long strings |
| Purity | the caller's arguments are not mutated |
| Idempotency | calling twice gives the same answer |
| Failure | every branch documented under `Raises:` |

Missing and malformed input deserve more weight than the rest. A function that returns a
plausible wrong answer for bad data is worse than one that raises, and the test suite is
where that gets decided rather than discovered.

## 2. Write the tests

`tests/test_<module>.py`, one per module. A test name says what it proves:
`test_export_preserves_unicode`, not `test_export_2`. Use `@pytest.mark.parametrize` where
one assertion holds across many inputs.

On a fix round, step 3 already added the reproduction test to this file, creating it if it
did not exist. Extend it and leave that test exactly as written: its red run is recorded
in section 3, and step 6 cites the pair. Every input the Scope row took from the class
gets a test of its own.

Every intent in the plan's Test intents table gets at least one test, and every acceptance
criterion ends up covered by at least one test. Record which tests cover which intent in
section 5 — that table is what step 6 reads as evidence.

### What a compliant test file looks like

For the `rolling_mean` module in `/implement`:

```python
import pytest

from my_package.statistics import rolling_mean


def test_rolling_mean_averages_each_window() -> None:
    assert rolling_mean([1, 2, 3, 4], "daily") == [1.0, 2.0, 3.0, 4.0]


def test_rolling_mean_returns_empty_for_no_samples() -> None:
    assert rolling_mean([], "daily") == []


def test_rolling_mean_returns_empty_when_window_exceeds_samples() -> None:
    assert rolling_mean([1, 2], "weekly") == []


@pytest.mark.parametrize("resolution", ["daily", "weekly", "monthly"])
def test_rolling_mean_accepts_every_resolution(resolution: str) -> None:
    rolling_mean([1, 2, 3], resolution)


def test_rolling_mean_rejects_an_unknown_resolution() -> None:
    with pytest.raises(ValueError, match="resolution must be one of"):
        rolling_mean([1, 2, 3], "hourly")


def test_rolling_mean_error_names_the_offending_resolution() -> None:
    with pytest.raises(ValueError, match="hourly"):
        rolling_mean([1, 2, 3], "hourly")


def test_rolling_mean_rejects_a_none_resolution() -> None:
    with pytest.raises(ValueError):
        rolling_mean([1, 2, 3], None)  # type: ignore[arg-type]  # untyped callers


def test_rolling_mean_does_not_mutate_its_input() -> None:
    samples = [1, 2, 3]
    rolling_mean(samples, "daily")
    assert samples == [1, 2, 3]


def test_rolling_mean_is_idempotent() -> None:
    assert rolling_mean([1, 2, 3], "daily") == rolling_mean([1, 2, 3], "daily")
```

Read what that covers against the checklist: the happy path, empty input, a boundary where
the window exceeds the samples, every value of the choice argument, two failure branches
including one that proves the message names the value, a malformed type with a narrowed
`# type: ignore` and its reason on the same line, purity and idempotency. Nine tests for one
function is not excessive — it is what "past the happy path" costs.

The package's own `tests/test_hello_world.py` is **not** the reference: it covers a
placeholder script and gets deleted with it.

## 3. Fix what the tests expose

A failing test means one of three things. Say which:

- **A bug in the code.** Fix the code. This is the normal case and the point of the step.
- **A wrong expectation.** Fix the test, and say why the first expectation was wrong.
- **A concept that was never settled.** Section 1 did not decide what should happen here,
  so nothing in the plan can. **Halt.** Report the case and the two answers it could have,
  rather than inventing one and burying it in an assertion.

Never weaken a test to make it pass, and never delete a case because it is inconvenient.
Both convert a real finding into a silent one.

## 4. Re-run the static checks

Fixing production code can break what step 4 proved, so close the loop here rather than
sending the work back a step:

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

If a signature changed while fixing a bug, update section 2's Public API table,
`STRUCTURE.md` and section 3's deviation list — all three, in this change.

## 5. Record, commit, push

Section 5 of the plan file: intent, the test names covering it, the result. Then list the
edge cases you considered and deliberately skipped, with the reason for each. A considered
omission is information; a silent one is a gap.

Commit the tests, the fixes and the plan file — subject `Test: <title>`, round file in the
body — and push. Clean tree, green tree.

## Stop here

1. Mark step 5 `done` and set the marker to `<!-- claude-plan step=6 status=active -->`.
   That edit goes in the commit above.
2. Report, in the `/build` contract: `STATUS`, and a `TRACE` with a line or two per test
   group — what it proves and how many cases — the pass count, every bug the tests found
   and how it was fixed, and anything skipped deliberately.
3. End. `/build` opens step 6; do not.
