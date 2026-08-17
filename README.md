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
8. Replace `<package_name>/hello_world.py` and `tests/test_hello_world.py` with real code.

Nothing else references the package name: `__init__.py` uses a relative import and
`[tool.setuptools.packages.find]` excludes `tests*` rather than naming the package.

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

### Troubleshooting

`Activate.ps1 cannot be loaded because running scripts is disabled` — allow local scripts
for your user:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

`python` not found right after `winget install` — open a new terminal so PATH is reloaded.
