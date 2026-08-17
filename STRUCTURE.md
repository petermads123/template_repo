# Structure

Map of everything in this repo. Loaded into context at the start of every session via the
`@STRUCTURE.md` import in `CLAUDE.md`, so it is what Claude uses to find things without
searching.

## Keeping this file current

Update it **in the same change** that causes any of the following:

- a module is added, deleted, renamed or moved
- a public function or class is added or removed
- a public signature changes (parameters, defaults, return type)
- a module's purpose changes

Private helpers (names starting with `_`) are intentionally left out. They are
implementation detail, and listing them is what makes a file like this rot.

The stop gate (`.claude/hooks/stop_gate.py`) cross-checks the module paths named here
against the `.py` files on disk and blocks on a mismatch. It only sees file-level drift —
signature drift is on you, or run the `structure-auditor` subagent.

## Growth

While the package is flat, keep everything here. Once it has subpackages, keep the tree and
one line per subpackage in this file, and move per-subpackage detail into
`.claude/rules/structure-<subpackage>.md` with `paths: ["<subpackage>/**"]` so it loads only
when Claude works in that subpackage. Split rather than delete — there is no length limit
here, but everything in this file is in context every session.

## Tree

```
template_repo/          the package itself (rename this to <package_name>)
tests/                  pytest suite, one test_<module>.py per module
.claude/                Claude Code configuration: rules, skills, agents, hooks, workflows
.vscode/                editor config (Ruff as formatter, format on save)
pyproject.toml          packaging, Ruff, mypy and pytest configuration
README.md               human setup guide
CLAUDE.md               routing map for Claude
STRUCTURE.md            this file
```

## Package: `template_repo/`

### `template_repo/__init__.py`

Package entry point. Re-exports the public API so callers can `from template_repo import X`
rather than reaching into modules. Uses relative imports so it survives renaming the
package folder.

| Public name | Source |
|---|---|
| `greet` | `template_repo.hello_world` |

### `template_repo/hello_world.py`

Example module, present to demonstrate the conventions. Replace it with real code.

| Signature | Description |
|---|---|
| `greet(name: str = "World") -> str` | Build a greeting for `name`. |
| `main() -> None` | Showcase: prints a default, a named and a non-ASCII greeting. |

Runnable standalone: `python -m template_repo.hello_world`.

## Tests: `tests/`

### `tests/test_hello_world.py`

Covers `greet`. Demonstrates the edge-case standard from `.claude/rules/python.md`: default
value, explicit value, empty string, non-ASCII input, whitespace preservation, a very long
input, and a parametrized determinism check.

## Claude configuration: `.claude/`

| Path | Role |
|---|---|
| `settings.json` | Registers the two hooks; pre-approves ruff/mypy/pytest |
| `rules/python.md` | Coding conventions, auto-loaded for `**/*.py` |
| `skills/conventions/` | `/conventions` — long-form reference with examples |
| `skills/small-change/` | `/small-change` — cosmetic edits |
| `skills/implement-feature/` | `/implement-feature` — full feature path |
| `skills/create-pr/` | `/create-pr` — gated PR creation |
| `agents/test-designer.md` | Read-only subagent that finds edge cases |
| `agents/structure-auditor.md` | Read-only subagent that reconciles this file |
| `workflows/implement-feature.js` | Design fan-out, judge, adversarial verify |

### `.claude/hooks/lint_py.py`

`PostToolUse` hook. Runs `ruff format` and `ruff check --fix` on any `.py` file Claude
writes or edits, and reports unfixable issues back via exit code 2. Stdlib only.

| Signature | Description |
|---|---|
| `find_ruff(project_dir: Path) -> Path \| None` | Locate Ruff in the project venv. |
| `run(ruff: Path, args: list[str]) -> CompletedProcess[str]` | Run Ruff, capturing output. |
| `target_file(payload: dict[str, object], project_dir: Path) -> Path \| None` | Extract the edited `.py` file from the hook payload. |
| `main() -> None` | Entry point: format, fix, report. |

### `.claude/hooks/stop_gate.py`

`Stop` hook. If Python files changed, runs ruff, mypy and pytest and cross-checks this file
against the modules on disk, blocking the turn from ending on failure. Bypass with
`.claude/.skip-gate`. Stdlib only.

| Signature | Description |
|---|---|
| `venv_tool(project_dir: Path, name: str) -> Path \| None` | Locate a tool in the project venv. |
| `capture(cmd: list[str], cwd: Path, timeout: int) -> CompletedProcess[str]` | Run a command, capturing output. |
| `git_lines(project_dir: Path, args: list[str]) -> list[str]` | Run git, return output lines. |
| `changed_python_files(project_dir: Path) -> set[str]` | Python files changed in the tree or on this branch. |
| `tracked_python_files(project_dir: Path) -> set[str]` | All non-ignored Python files. |
| `structure_problems(project_dir: Path) -> list[str]` | File-level drift between this file and disk. |
| `gate_failures(project_dir: Path) -> list[str]` | Run the verification set, collect failures. |
| `block(reason: str) -> None` | Emit the block decision and exit. |
| `main() -> None` | Entry point: decide whether the turn may end. |
