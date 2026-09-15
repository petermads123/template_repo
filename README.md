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

`docs/plans/` starts with only `TEMPLATE.md` in it. Leave that file alone — `/feature`
copies it into a new folder for each piece of work.

Nothing else references the package name: `__init__.py` uses a relative import,
`[tool.setuptools.packages.find]` excludes `tests*` rather than naming the package, and
everything under `.claude/` is package-name agnostic.

Avoid naming the package folder `lib`, `build`, `dist` or `sdist`: the `.gitignore`
inherited from GitHub's Python template ignores those, so the folder would be silently
untracked. `docs` is not ignored, but it is already taken by `docs/plans/`.

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

### The implementation pipeline

Anything that is not cosmetic goes through nine steps, with a hard stop after each one so
you decide when to move on. The state lives on disk rather than in the conversation, so a
feature survives closing the session and coming back tomorrow — one folder per feature, one
numbered file per round:

```
docs/plans/
  TEMPLATE.md
  csv-export/
    01-csv-export.md          round 1, shipped
    02-streaming-writer.md    round 2, in flight
```

| Step | Command | Produces |
|---|---|---|
| 1 | `/conceptualize` | The concept, agreed with you, and numbered acceptance criteria |
| 2 | `/plan` | Modules, full signatures, implementation guide, test intents |
| 3 | `/implement` | The branch and the production code |
| 4 | `/verify` | ruff, mypy, and a check that the code matches the plan |
| 5 | `/test` | The edge-case suite, and fixes for what it finds |
| 6 | `/concept-check` | An audit against step 1, criterion by criterion |
| 7 | `/ship` | Commit and push |
| 8 | `/recommend` | Ranked follow-ups, decided with you |
| 9 | `/create-pr` | A full re-verification of the whole branch, then a pull request to `main`, ready for review |

Start with `/feature <what to build>` — it creates the plan file and opens step 1. After
that, each step is opened by running its own command. A step never starts the next one on
its own.

Step 9 is not a formality. It is the only point where the branch is verified as a whole:
steps 4 and 7 each checked one round at one moment, so on a multi-round branch nothing has
yet proved that round 2 left round 1 working. It re-runs the full suite, every module
showcase and every round's plan against a clean tree and a current `main`.

Two things are worth knowing about the shape of it. **Step 6 audits against step 1, not
step 2**: a plan can drift from its concept a little at each step while passing every check
along the way, and this is where that gets caught. And **step 8 is where new scope belongs**
— ideas that turn up during steps 1 to 7 are a distraction, but with the finished feature in
front of you they are a decision. A recommendation you accept opens a new numbered file in
the same folder and goes back through steps 1 to 7 on the same branch, so one pull request
can carry several deliberate passes over one feature. Step 6 of a later round re-checks the
earlier rounds' acceptance criteria, so a follow-up cannot quietly regress what it builds on.

| Other commands | Use for |
|---|---|
| `/small-change` | Renames, wording, styling — anything cosmetic, no plan file |
| `/feature` with no argument | "Where did we get to?" |

### Hooks

Four run automatically:

- **Session start** — reports the active plan and its step, so a new session picks up where
  the last one stopped. Silent when nothing is in flight.
- **Before any shell command** — refuses a `git commit` or `git push` that would land on
  `main`, including inside a `&&` chain.
- **After every `.py` write** — Ruff formats and auto-fixes the file; only unfixable issues
  come back.
- **Before a turn ends** — the stop gate. During steps 1 to 3 it only reports; from step 4,
  and for any work with no plan file, it refuses to end the turn while ruff, mypy or pytest
  fail or `STRUCTURE.md` is out of sync. Create `.claude/.skip-gate` to bypass it.

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
