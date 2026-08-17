# template_repo

Repo description.

## Install as a dependency

```powershell
pip install git+https://github.com/<repo_owner>/<repo_name>.git@main
```

Or in `dependencies` in `pyproject.toml`:

```toml
"<repo_name> @ git+https://github.com/<repo_owner>/<repo_name>.git@main"
```

## Creating a new repo from this template

1. Rename the folder `template_repo/` to `<package_name>`.
2. `pyproject.toml`: set `[project] name` to `<package_name>`.
3. `pyproject.toml`: set `[project] description`.
4. `pyproject.toml`: set `[tool.mypy] files` to `["<package_name>", "tests"]`.
5. `README.md`: update the title, the description and the two install URLs above.
6. `pyproject.toml`: add runtime dependencies to `[project] dependencies`.
7. `tests/test_hello_world.py`: change the import to `from <package_name> import greet`.
8. `STRUCTURE.md`: update the tree and the module paths to the new package name.
9. `README.md`: this checklist mentions the package name too.
10. Replace `<package_name>/hello_world.py` and `tests/test_hello_world.py` with real code,
    updating `STRUCTURE.md` as you go.

Nothing else references the package name: `__init__.py` uses a relative import,
`[tool.setuptools.packages.find]` excludes `tests*` rather than naming the package, and
everything under `.claude/` is package-name agnostic.

Avoid naming the package folder `lib`, `build`, `dist` or `docs`: the `.gitignore` inherited
from GitHub's Python template ignores those, so the folder would be silently untracked.

## Development

### Prerequisites

All installable from PowerShell — no website visits needed:

```powershell
winget install --id Git.Git --source winget
winget install --id Python.Python.3.13 --source winget
code --install-extension ms-python.python
code --install-extension charliermarsh.ruff
```

The Python version must satisfy `requires-python` in `pyproject.toml`. To install a
different one, replace the version in the package id, e.g. `Python.Python.3.14`.

`winget` does not update the PATH of the shell it ran in. Open a new terminal before
continuing, then check with `python --version`.

### Create the environment

From the repo root:

```powershell
python -m venv .venv
```

```powershell
.\.venv\Scripts\Activate.ps1
```

```powershell
python -m pip install --upgrade pip
```

```powershell
pip install -e ".[dev]"
```

The `[dev]` part installs Ruff, mypy and pytest. Without it you get the package only.

In VS Code the environment activates automatically in new terminals once the interpreter is
selected. If it is not picked up, use `CTRL + Shift + P` -> `Python: Select Interpreter` and
choose the one in `.venv`.

### Verify

All four must pass on a fresh clone:

```powershell
ruff check .
```

```powershell
ruff format --check .
```

```powershell
mypy
```

```powershell
pytest
```

### Editor

`.vscode/settings.json` is checked in, so format-on-save, import sorting and Ruff as the
Python formatter are already configured for this repo. Installing the Ruff extension (see
Prerequisites) is all that is required.

## Working with Claude Code

This repo ships a Claude Code configuration under `.claude/`, plus `CLAUDE.md` (a routing
map, loaded every session) and `STRUCTURE.md` (a map of what lives where, imported by
`CLAUDE.md`).

| Command | Use for |
|---|---|
| `/small-change` | Renames, wording, styling — anything cosmetic |
| `/implement-feature` | New modules, new public functions, behavior changes |
| `/create-pr` | Verifies the tree, then opens a draft PR after you confirm |
| `/conventions` | The coding conventions, with worked examples |

Two hooks run automatically: Ruff formats and fixes every `.py` file Claude edits, and a
stop gate refuses to end a turn while ruff, mypy or pytest fail or `STRUCTURE.md` is out of
sync. Create `.claude/.skip-gate` to bypass the gate deliberately.

Three caveats worth knowing:

- **Hooks are read at session start.** Editing anything under `.claude/hooks/` or
  `.claude/settings.json` needs a Claude Code restart. Skills and rules hot-reload.
- **The first session prompts for workspace trust**, because `.claude/settings.json`
  registers hooks. Accept it or the hooks stay inactive.
- The hooks call `python` from your PATH and only use the standard library; they locate
  `ruff`, `mypy` and `pytest` inside `.venv` themselves.

### Troubleshooting

`Activate.ps1 cannot be loaded because running scripts is disabled` — allow local scripts
for your user:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

`python` not found right after `winget install` — open a new terminal so PATH is reloaded.
