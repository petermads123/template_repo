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
docs/plans/             one folder per feature, one file per round: the pipeline's state
.claude/                Claude Code configuration: rules, skills, agents, hooks
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
| `main() -> None` | Showcase: a named greeting, the default, and a non-ASCII name, each with its input bound to a variable first. |

Runnable standalone: `python -m template_repo.hello_world`.

## Tests: `tests/`

### `tests/test_hello_world.py`

Covers `greet`. Demonstrates the edge-case standard from `.claude/rules/python.md`: default
value, explicit value, empty string, non-ASCII input, whitespace preservation, a very long
input, and a parametrized determinism check.

All tests live here and nowhere else — `testpaths = ["tests"]` in `pyproject.toml` means
`pytest` collects nothing outside this directory, and the stop gate blocks on a test file
found anywhere else.

## Plans: `docs/plans/`

One folder per feature, one numbered file per round inside it, created by `/feature` from
`TEMPLATE.md` and carried through all nine steps:

```
docs/plans/
  TEMPLATE.md                     copied for each new round; never itself active
  csv-export/
    01-csv-export.md              round 1
    02-streaming-writer.md        round 2, opened from a step 8 recommendation
```

Each file holds the concept and acceptance criteria, the plan, the verification and test
logs, the concept-check audit, the recommendations and the pull request. Every round of a
feature shares one branch and one pull request; a later round's **Builds on** section names
what the earlier rounds delivered, and its step 6 re-checks their acceptance criteria as a
regression pass.

The first line after the title is the workflow's state and is read by the hooks:

```
<!-- claude-plan step=3 status=active -->
```

`step` is 1 to 9; `status` is `active`, `done`, `parked` or `template`. Exactly one file
across the whole repo should be `active` — opening a round stands its predecessor down to
`done`. Plan files are committed: they are the record of why the code looks the way it is,
and `/create-pr` builds the pull request body from every round in the folder.

## Claude configuration: `.claude/`

| Path | Role |
|---|---|
| `settings.json` | Registers the four hooks; pre-approves ruff/mypy/pytest and read-only git |
| `rules/python.md` | Coding conventions, auto-loaded for `**/*.py` |
| `skills/feature/` | `/feature` — starts or resumes the pipeline |
| `skills/conceptualize/` | `/conceptualize` — step 1, agree the concept |
| `skills/plan/` | `/plan` — step 2, design it |
| `skills/implement/` | `/implement` — step 3, branch and build |
| `skills/verify/` | `/verify` — step 4, static verification |
| `skills/test/` | `/test` — step 5, edge-case suite |
| `skills/concept-check/` | `/concept-check` — step 6, audit against the concept |
| `skills/ship/` | `/ship` — step 7, commit and push |
| `skills/recommend/` | `/recommend` — step 8, ranked follow-ups |
| `skills/create-pr/` | `/create-pr` — step 9, draft pull request |
| `skills/small-change/` | `/small-change` — cosmetic edits, outside the pipeline |
| `agents/test-designer.md` | Read-only subagent that finds edge cases (feeds step 5) |
| `agents/structure-auditor.md` | Read-only subagent that reconciles this file (feeds steps 4 and 6) |

### `.claude/hooks/plan_state.py`

Shared by the other hooks: parses the `claude-plan` marker out of the plan files and
answers which plan is active, plus the small git helpers the hooks need. Importable by its
siblings because Python puts a script's own directory on `sys.path`. Stdlib only.

| Signature | Description |
|---|---|
| `Plan` | Frozen dataclass: `path`, `step`, `status`, `title`, `branch`, `feature`, `round_number`, plus `step_name` and `gated` properties. |
| `parse(path: Path) -> Plan \| None` | Parse one plan file, or None if it has no valid marker. |
| `all_plans(project_dir: Path) -> list[Plan]` | Every parseable plan in every feature folder, most recently modified first. |
| `active_plan(project_dir: Path) -> Plan \| None` | The plan the pipeline is working through. |
| `feature_rounds(project_dir: Path, feature: str) -> list[Plan]` | One feature's rounds, oldest first. |
| `git_lines(project_dir: Path, args: list[str]) -> list[str]` | Run git, return output lines. |
| `current_branch(project_dir: Path) -> str` | The checked-out branch, or `""`. |
| `main() -> None` | Showcase: prints the plans found, the active one and its sibling rounds. |

`GATE_FROM_STEP = 4` is the step at which the stop gate starts blocking.

### `.claude/hooks/session_brief.py`

`SessionStart` hook. Injects the active plan's step into a new session's context, plus what
any earlier rounds of the same feature delivered, so work resumes without the user having
to re-explain it. Silent when no plan is active. Stdlib only.

| Signature | Description |
|---|---|
| `brief(project_dir: Path, plan: Plan) -> str` | Describe one active plan's state. |
| `main() -> None` | Entry point: emit the brief as session context. |

### `.claude/hooks/guard_git.py`

`PreToolUse` hook on `Bash`. Refuses a `git commit` or `git push` that would land on
`main`, splitting compound commands so the second half of a `&&` chain is caught too.
Allows anything it cannot confidently parse. Stdlib only.

| Signature | Description |
|---|---|
| `segments(command: str) -> list[list[str]]` | Split a shell command into its invocations. |
| `git_subcommand(tokens: list[str]) -> tuple[str, list[str]]` | Identify the git subcommand and its arguments. |
| `push_targets_main(args: list[str], branch: str) -> bool` | Whether a push would update `main`. |
| `violation(command: str, branch: str) -> str` | The reason to refuse, or `""` to allow. |
| `main() -> None` | Entry point: allow or refuse the command. |

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

`Stop` hook. Reads the active plan's step to decide how strict to be: advisory through step
3, blocking from step 4 and whenever no plan is active. When it blocks it runs ruff, mypy
and pytest, cross-checks `STRUCTURE.md` against the modules on disk, and reports any test
file sitting outside `tests/` where `pytest` would silently never collect it. Bypass with
`.claude/.skip-gate`. Stdlib only.

| Signature | Description |
|---|---|
| `venv_tool(project_dir: Path, name: str) -> Path \| None` | Locate a tool in the project venv. |
| `capture(cmd: list[str], cwd: Path, timeout: int) -> CompletedProcess[str]` | Run a command, capturing output. |
| `changed_python_files(project_dir: Path) -> set[str]` | Python files changed in the tree or on this branch. |
| `tracked_python_files(project_dir: Path) -> set[str]` | All non-ignored Python files. |
| `structure_problems(project_dir: Path) -> list[str]` | File-level drift between this file and disk. |
| `stray_test_files(project_dir: Path) -> list[str]` | Test files outside `tests/`, which pytest never collects. |
| `gate_failures(project_dir: Path) -> list[str]` | Run the verification set, collect failures. |
| `advisory_notes(project_dir: Path, plan: Plan, changed: set[str]) -> list[str]` | Non-blocking observations for steps 1 to 3. |
| `notice(message: str) -> None` | Show the user a message without blocking. |
| `block(reason: str) -> None` | Emit the block decision and exit. |
| `enforce(project_dir: Path) -> None` | Run the verification set and block on failure. |
| `main() -> None` | Entry point: decide whether the turn may end. |
