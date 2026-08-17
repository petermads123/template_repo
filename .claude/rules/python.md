---
paths:
  - "**/*.py"
---

# Python conventions

These are non-negotiable. `/conventions` has the worked examples.

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

## Every module has a `main()`

Every module defines a showcase and ends with the guard:

```python
def main() -> None:
    """Showcase this module's functionality."""
    ...


if __name__ == "__main__":
    main()
```

- For a **library module**, `main()` is a **showcase, not a test**: a handful of
  representative calls that print their results so a reader can see what the module does.
  No assertions, no exhaustive cases.
- For an **executable script** (anything under `.claude/hooks/`, or a module whose whole
  purpose is to be run), `main()` is simply the entry point. The guard is the same; the
  showcase rule does not apply, because there is nothing to showcase.
- A library module's `main()` must run standalone: `python -m <package>.<module>`.
- **Exempt**: `__init__.py`, everything under `tests/`, and `conftest.py`.

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
| Optional | `None` where the type allows it, missing defaults |
| Text | non-ASCII, leading/trailing whitespace, very long strings |
| Purity | arguments are not mutated |
| Idempotency | calling twice gives the same result |
| Failure | every branch documented under `Raises:` |

Use `@pytest.mark.parametrize` when the same assertion holds across many inputs. A test
name should say what it proves: `test_greet_preserves_unicode`, not `test_greet_2`.
