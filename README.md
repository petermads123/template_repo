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

**Open Claude Code and let it run `/repo-setup`.** It is referenced from `CLAUDE.md`, so the
first conversation in a fresh clone starts with it. It asks what the repo is for, writes that
into this README, renames the package to match the repo, updates every file that names it,
offers the branch ruleset, and then deletes its own reference from `CLAUDE.md` so it never
runs again.

What it does, for when you would rather do it by hand:

1. Rename `src/template_repo/` to `src/<package_name>/`.
2. `pyproject.toml`: set `[project] name` to `<package_name>`.
3. `pyproject.toml`: set `[project] description`.
4. `README.md`: update the title, the description and the two install URLs above.
5. `pyproject.toml`: add runtime dependencies to `[project] dependencies`.
6. `tests/test_hello_world.py`: change the import to `from <package_name> import greet`.
7. `STRUCTURE.md`: update the tree and the module paths to the new package name.
8. `CLAUDE.md`: set the approver in the Review and merge table.
9. Replace `src/<package_name>/hello_world.py` and `tests/test_hello_world.py` with real
   code, updating `STRUCTURE.md` as you go.
10. Remove the `/repo-setup` reference from `CLAUDE.md`.

`docs/plans/` starts with only `TEMPLATE.md` in it. Leave that file alone — `/feature`
copies it into a new folder for each piece of work.

Little else references the package name: `__init__.py` uses a relative import,
`[tool.setuptools.packages.find]` points at `src` rather than naming the package,
`[tool.mypy] files` names directories, and everything under `.claude/` is package-name
agnostic.

### Why `src/`

Everything installable lives under `src/`, so nothing else in the repo — `tests/`, `docs/`,
a stray script — can be picked up as a package by accident, and an import in a test resolves
against the installed package rather than against whatever happens to sit in the working
directory.

The trade-off: the repo root is not on `sys.path`, so `python -m <package>.<module>` only
works once you have run `pip install -e ".[dev]"`. `pytest` is unaffected — `pythonpath`
in `pyproject.toml` points it at `src`.

Avoid naming the package folder `lib`, `build`, `dist` or `sdist`: the `.gitignore`
inherited from GitHub's Python template ignores those, so the folder would be silently
untracked even under `src/`.

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

Anything that is not cosmetic goes through ten steps, with a hard stop after each one so
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
| 10 | `/watch-pr` | An hourly check of the open PR, acting on comments, until it merges or closes |

Step 9 requests your review on the PR it opens, and step 10 may complete the merge once you
have approved — but only with the approval un-stale, CI green, no conflict and no thread
waiting on Claude. Note that **GitHub lets nobody request a review from, or approve, their
own pull request**: in a solo repo, where Claude pushes under your token, every PR is
authored by you, so the review route is unavailable and the merge signal is instead an
explicit "merge it" comment from you. `CLAUDE.md` names the approver.

Start with `/feature <what to build>` — it creates the plan file and opens step 1. After
that, each step is opened by running its own command. A step never starts the next one on
its own.

**You do not have to type the commands.** Describe the work in prose — "I want to add CSV
export", "rename that variable" — and Claude classifies it against the small-or-large test
before doing anything: a local rename with no signature or behaviour change is small, and
anything that adds a file, changes a public signature, changes behaviour or needs a test is
not. It says which way it routed and why in one line, so a wrong call costs you a sentence
to correct, and asks only when the request is genuinely borderline. When it is close, it
routes up to the pipeline, because step 1 is a conversation you can redirect — whereas a
feature handled as a small change quietly skips the concept, the tests and the audit.

A slash command still wins if you type one, and a question stays a question: asking how
something works gets an answer, not a pipeline.

Each step also picks its own model. Concept, planning and recommendations run on Opus
because they are judgment; implementation, verification, tests, the concept check and the
pull request run on Sonnet at max effort because the thinking has already been done and
written down. `/small-change` runs on Opus too — deciding a change is small enough to skip
the pipeline is the one judgment made without the pipeline to catch it. The override lasts one step and reverts, so your own `/model` setting is left
alone. `CLAUDE.md` has the table.

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
