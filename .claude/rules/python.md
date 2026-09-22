---
paths:
  - "**/*.py"
---

# Python conventions

These are non-negotiable.

## Tooling

- `pyproject.toml` is the authority for Ruff, mypy and pytest. Do not add per-file config.
- `ruff check .` and `ruff format --check .` must pass. Never add a bare `# noqa` — if one
  is genuinely needed, use the specific code and put the reason on the same line:
  `# noqa: ARG001 - signature fixed by the callback protocol`.
- `mypy` must pass. No bare `Any`. No `# type: ignore` without a narrowing code and a
  reason: `# type: ignore[arg-type]  # upstream stub is wrong, see issue 12`.

## Style

- Full type annotations on every signature, including `-> None`.
- Google-convention docstrings on every public module, class and function, with `Args:`,
  `Returns:` and `Raises:` where they apply. Ruff's `D` rules enforce this.
- Private helpers start with `_` and stay out of `STRUCTURE.md`.
- Every package directory under `src/` has an `__init__.py`, including every subpackage. A
  directory of modules without one is not a package: it will not install, and imports from
  it resolve only by accident of the working directory.
- Error messages name the offending value: `f"window must be positive, got {window}"`.

## Every module has a `main()`

Every module defines a showcase and ends with the guard:

```python
def main() -> None:
    """Showcase this module's functionality."""
    ...


if __name__ == "__main__":
    main()
```

- For a **library module**, `main()` is a **showcase, not a test**: a worked example of
  how the module is used, in the form below, printed so a reader can see what it does. No
  assertions, no exhaustive cases.
- For an **executable script** (anything under `.claude/hooks/`, or a module whose whole
  purpose is to be run), `main()` is simply the entry point. The guard is the same; the
  showcase rule does not apply, because there is nothing to showcase.
- A library module's `main()` must run standalone: `python -m <package>.<module>`.
- **Exempt**: `__init__.py`, everything under `tests/`, and `conftest.py`.

### The showcase form

A showcase is a worked example a reader can follow top to bottom and **edit in place**.
Bind every argument to a named variable, call on its own line, bind the result, print it:

```python
def main() -> None:
    """Showcase this module's functionality."""
    samples = [1, 2, 3, 4]
    window = 2

    means = rolling_mean(samples, window)

    print(f"rolling mean over {window}: {means}")
```

Three phases separated by blank lines — **inputs**, **call**, **output**. The reader sees
what goes in without parsing a call, and can change `window` to `5` and re-run without
untangling nested literals.

- One named variable per argument, each holding a literal. No literals inside the call.
- The result gets a name too, even when it is printed on the next line.
- Two or three cases: the normal one first, then something that teaches — an edge, a
  default, an input that reveals behaviour worth knowing.
- Label each print when there is more than one case, so the output says which is which.
- **When an argument only accepts a fixed set of values, list them in a comment on the same
  line.** The reader sees the options without opening the docstring, and swaps one in by
  editing the string:

  ```python
  resolution = "daily"  # "daily", "weekly", "monthly"
  fill = "forward"  # "forward", "backward", "none"
  ```

  It applies to enum members too: `period = Period.DAILY  # DAILY, WEEKLY, MONTHLY`.

  List the ones worth knowing rather than exhaustively. If there are twenty, name the three
  that matter and point at the rest: `# "daily", "weekly", "monthly", ... see RESOLUTIONS`.

  Booleans do not need it — `strict = True  # True, False` tells the reader nothing the
  type has not already told them.

**Bad** — the arguments are buried in the call. This is the most common failure, and it
looks fine until you try to change something:

```python
def main() -> None:
    """Showcase this module's functionality."""
    print(rolling_mean([1, 2, 3, 4], window=2))
    print(rolling_mean([1, 2], window=5))
```

**Bad** — a test suite wearing a showcase costume. Assertions belong in `tests/`:

```python
def main() -> None:
    """Showcase this module's functionality."""
    assert rolling_mean([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]
```

**Bad** — proves nothing a reader can see:

```python
def main() -> None:
    """Showcase this module's functionality."""
    rolling_mean([1, 2, 3], 2)
```

The same shape works for a class: build the arguments, construct it, call the method,
print the result. The question the showcase answers is *how would I use this?*, and a
constructor with five inline literals answers it no better than a function call does.

The test: could someone run `python -m package.module` and understand what the module does
from the output alone? If not, the showcase is not doing its job. `/implement` carries a
full worked module and `/test` a full worked test file — this rule is the short form.

Because the package lives under `src/`, `python -m` only resolves once the package is
installed — `pip install -e ".[dev]"`, which the setup guide does anyway. On a fresh clone
with no install it fails with `No module named ...`, which means the environment is not set
up rather than the module being broken.

If a module is also re-exported from `__init__.py`, `python -m` prints a `RuntimeWarning`
about the module already being in `sys.modules`. That is expected and harmless — it is the
normal consequence of a package re-exporting its own submodule. Do not "fix" it by removing
the re-export; check the output and exit code instead.

## Every public function has tests

Tests live in `tests/`, one `test_<module>.py` per module. Go past the happy path — work
through this checklist and include the ones that apply:

| Category | Probe |
|---|---|
| Empty | empty string, empty list/dict, zero |
| Boundaries | first, last, off-by-one either side of a limit |
| Numbers | negative, very large, float precision, division by zero |
| Missing | `None` where the type allows it, omitted defaults, absent keys |
| Malformed | wrong type, wrong shape, unparseable text, truncated input |
| Text | non-ASCII, leading/trailing whitespace, very long strings |
| Purity | arguments are not mutated |
| Idempotency | calling twice gives the same result |
| Failure | every branch documented under `Raises:` |

Use `@pytest.mark.parametrize` when the same assertion holds across many inputs. A test
name should say what it proves: `test_rolling_mean_returns_empty_for_no_samples`, not
`test_rolling_mean_2`.

Never weaken a test to make it pass and never delete an inconvenient case. Both turn a real
finding into a silent one.
