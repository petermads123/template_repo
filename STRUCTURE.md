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

That covers `src/`, `tests/` and `.claude/hooks/`. The hooks are documented here with full
signature tables, type-checked like the package (`[tool.mypy] files` names all three) and
importable from the suite (`[tool.pytest.ini_options] pythonpath` names `src` and
`.claude/hooks`, so a test imports a hook by module name the same way a sibling hook does
at runtime), so they are held to the same standard despite not being installable.

## Growth

While the package is flat, keep everything here. Once it has subpackages, keep the tree and
one line per subpackage in this file, and move per-subpackage detail into
`.claude/rules/structure-<subpackage>.md` with `paths: ["<subpackage>/**"]` so it loads only
when Claude works in that subpackage. Split rather than delete — there is no length limit
here, but everything in this file is in context every session.

## Tree

```
src/                    everything installable; nothing outside it is packaged
  template_repo/        the package itself (rename this to <package_name>)
tests/                  pytest suite, one test_<module>.py per module
development/            one folder per branch, one file per round: the pipeline's state
.claude/                Claude Code configuration: rules, skills, agents, hooks
.vscode/                editor config (Ruff as formatter, format on save)
pyproject.toml          packaging, Ruff, mypy and pytest configuration
README.md               human setup guide
CLAUDE.md               routing map for Claude
STRUCTURE.md            this file
```

## Package: `src/template_repo/`

### `src/template_repo/__init__.py`

Package entry point. Re-export the public API here so callers can
`from template_repo import X` rather than reaching into modules, using relative imports so
it survives renaming the package folder. Nothing is exported yet — the placeholder script
has no public API.

Every package directory under `src/`, including every subpackage added later, needs one of
these. The stop gate blocks on a directory of modules without it: it is not a package, so
it will not install.

### `src/template_repo/hello_world.py`

Placeholder so the package is not empty. Delete the whole file when real code arrives.

| Signature | Description |
|---|---|
| `main() -> None` | Print `Hello, World!`. |

It is deliberately trivial and is **not** the conventions reference — `/implement` carries
the worked module and `/test` the worked test file, so the examples do not disappear with
the placeholder.

Runnable standalone: `python -m template_repo.hello_world`, once the package is installed
(`pip install -e ".[dev]"`). Under a `src/` layout the repo root is not on `sys.path`, so
without the install it fails with `No module named template_repo` — an un-set-up
environment, not a broken module.

## Tests: `tests/`

### `tests/test_hello_world.py`

Covers the placeholder script's `main` via `capsys`: the exact output, that it is one line,
that nothing goes to stderr, and that a second call prints the same thing. Deleted along
with the script it covers. The edge-case standard is demonstrated in `/test`, not here.

All tests live here and nowhere else — `testpaths = ["tests"]` in `pyproject.toml` means
`pytest` collects nothing outside this directory, and the stop gate blocks on a test file
found anywhere else.

### `tests/test_guard_git.py`

Covers `.claude/hooks/guard_git.py`, and is the regression suite for the quoting defect
its parser was rebuilt to fix. `segments` for quoting, every separator, a separator glued
to a word or to a newline, a run of newlines, a newline inside a quoted message, a `#`
inside a word, and input that cannot be lexed at all; `git_subcommand` for each spelling
of the executable and the options that hide the subcommand; `push_targets_main` for every
refspec shape that reaches `main`; `switch_target` for both subcommands, their new-branch
options, an option left without a value and a file restore; `violation` for the whole
behavioural matrix — punctuation in a commit message, a branch switch trusted across `&&`
and across an `&&` ending a line but distrusted across everything else, including a mixed
run such as `; &&`, a subshell that has closed and another repository reached with `-C`;
commands hidden behind grouping delimiters; unreadable input, matched on word boundaries
so `committee` is not a commit; and every refusal that held before the rewrite. `main` is
exercised end to end against a throwaway repository: a commit on `main` refused with exit
2 and the reason on stderr, a commit allowed after branching and off `main`, payloads that
are not a git command, an unparseable payload, and a byte-order mark.

The command-recognition cases follow: a commit or push hidden behind variable assignments,
behind each redirection form including `2>&1`, inside backticks and `$( )`, and under each
of the five wrapper programs; the executable in five spellings and cases; each push option
whose value would otherwise be read as the remote; `@` and `refs/heads/main` reduced to
the branches they name; an unresolvable switch refusing from either branch with its own
message; and the commands that must stay allowed — `echo git commit`, `grep push log.txt`,
`sudo apt install git`, `time ls`, and a commit message naming both `sudo` and `git push`.
One test asserts a documented miss rather than a fix: `sudo -u me git push` is allowed,
because only options are skipped after a wrapper and never a bare word.

### `tests/test_plan_state.py`

Covers `.claude/hooks/plan_state.py`. `parse` against a complete marker, a file with none,
a step outside 1-10, an uppercase status, a missing Branch row, a missing title, an
unreadable path, a nested `type/topic` folder read as a relative `feature`, a file outside
the plans directory falling back to its parent's name, and an unprefixed filename such as
`TEMPLATE.md` giving round 0 and an empty `feature`; `all_plans` for a missing plans
directory, recursion, files without a marker, modification-time ordering and relative
paths; `active_plan` for none, one and several active at once; `feature_rounds` for round
ordering, a nested feature folder, feature isolation and an unknown feature; `git_lines`/`current_branch` against a throwaway
repository, including a detached HEAD and a directory that is not a repository at all; and
`main` printing the plans it finds, with one active and with none. `Plan.step_name` and
`Plan.gated` are covered either side of `GATE_FROM_STEP`.

### `tests/test_stop_gate.py`

Covers `.claude/hooks/stop_gate.py`. `venv_tool` for both layouts, neither, and which wins
when both exist; `capture` for output, a non-zero exit and an expired timeout;
`changed_python_files` and `tracked_python_files` against a throwaway repository, including
a rename, a `.gitignore` and work committed on a branch; `structure_problems` in both
directions plus placeholder paths; `stray_test_files`; `missing_init_files`; and
`advisory_notes`, `notice` and `block`; `enforce` for blocking on one failure, for gathering
every check's problems into a single reason, and for returning quietly when all four pass; and
`main` for an unreadable payload, a turn already blocked once, the `.skip-gate` escape hatch,
enforcement with no plan and Python changed, and the advisory path below the gate step.

`gate_failures` is driven through a monkeypatched `venv_tool` and `capture` rather than
real executables. Running it for real would invoke Ruff, mypy and `pytest` from inside
`pytest`, and building stub executables would need a shell script on POSIX and an `.exe` on
Windows. `enforce` and `main` are driven the same way, with the four checks monkeypatched, so
neither reaches a real tool either.


## Plans: `development/`

One folder per branch, one numbered file per round inside it, created at the close of step
1 from `TEMPLATE.md` and carried through all ten steps:

```
development/
  TEMPLATE.md                     copied for each new round; never itself active
  feat/csv-export/                the folder is the branch name, so it nests one level
    01-csv-export.md              round 1, shipped
    02-streaming-writer.md        round 2, opened from round 1's recommendation R2
```

Each file holds the concept and acceptance criteria, the plan, the verification and test
logs, the concept-check audit, the recommendations and the pull request, plus a `Halted`
section if the build stopped to ask. A fix round's section 1 also carries a **Defect**
block — reproduction, root cause, class, blast radius, scope — filled from the `/fix`
diagnosis; its presence is what tells the later steps the round is a fix. Every round
of a feature shares one branch and one pull request; a later round's **Builds on** section
names what the earlier rounds delivered, and its step 6 re-checks their acceptance criteria
as a regression pass.

The first line after the title is the workflow's state and is read by the hooks:

```
<!-- claude-plan step=3 status=active -->
```

`step` is 1 to 10; `status` is `active`, `done`, `parked` or `template`. Exactly one file
across the whole repo should be `active` — opening a round stands its predecessor down to
`done`, and step 9 marks the newest round `done` in the commit that opens the pull request,
so `main` never carries a live marker. Every step commits and pushes the file with what it
produced: plan files are the record of why the code looks the way it is, the state any
session resumes from, and what `/create-pr` builds the pull request body from.

## Claude configuration: `.claude/`

| Path | Role |
|---|---|
| `settings.json` | Registers the four hooks; pre-approves ruff/mypy/pytest, `python -m`, and the git commands the pipeline uses (read-only ones plus add, commit, push, fetch, checkout, switch, merge, mv) so an unattended build never stalls on a prompt — `guard_git.py` is what keeps that safe |
| — | Every skill pins `model` and `effort` in its frontmatter; the table in `CLAUDE.md` says which and why |
| `skills/build/` | `/build` — steps 3 to 7 as one unattended block: a subagent per step on its pinned model, commit and push after each, halting rules, trace relay, resume from the marker |
| `rules/python.md` | Coding conventions, auto-loaded for `**/*.py` |
| `skills/repo-setup/` | `/repo-setup` — one-time setup of a repo made from this template; carries `main_protect.solo.json` and `main_protect.collab.json` |
| `skills/feature/` | `/feature` — starts or resumes the pipeline |
| `skills/fix/` | `/fix` — starts the pipeline from a defect: reproduces, finds the root cause, sizes the class, has the diagnosis criticised, decides whether it is a bug at all, then hands to `/conceptualize` as a fix round |
| `skills/conceptualize/` | `/conceptualize` — step 1, agree the concept |
| `skills/plan/` | `/plan` — step 2, design it |
| `skills/implement/` | `/implement` — step 3, write the code (inside `/build`) |
| `skills/verify/` | `/verify` — step 4, static verification |
| `skills/test/` | `/test` — step 5, edge-case suite |
| `skills/concept-check/` | `/concept-check` — step 6, audit against the concept |
| `skills/ship/` | `/ship` — step 7, close the round: whole-tree gates and diff review (inside `/build`) |
| `skills/recommend/` | `/recommend` — step 8, ranked follow-ups |
| `skills/create-pr/` | `/create-pr` — step 9, pull request ready for review |
| `skills/watch-pr/` | `/watch-pr` — step 10, hourly review watch until merge or close |
| `skills/small-change/` | `/small-change` — cosmetic edits, outside the pipeline |
| `agents/diagnosis-critic.md` | Subagent that tries to falsify a defect diagnosis before step 1 agrees a fix on it — re-runs the reproduction, traces the cause independently, checks the class (feeds `/fix`); may run code from a scratch directory but never writes to the tree; pinned to `opus` |
| `agents/plan-critic.md` | Read-only subagent that reads a plan against its concept and the repo before the user accepts it (feeds step 2); pinned to `opus` |
| `agents/test-designer.md` | Read-only subagent that finds edge cases; run twice at step 5 with the `input-space` and `contract` briefs |
| `agents/brainstormer.md` | Read-only subagent that proposes follow-ups through one lens — `user`, `maintainer` or `integrator`, plus `defect-class` on a fix round; three or four run in parallel at step 8 |
| `agents/structure-auditor.md` | Read-only subagent that reconciles this file (feeds steps 4 and 6) |

### `.claude/hooks/plan_state.py`

Shared by the other hooks: parses the `claude-plan` marker out of the plan files and
answers which plan is active, plus the small git helpers the hooks need. Importable by its
siblings because Python puts a script's own directory on `sys.path`. Stdlib only.

| Signature | Description |
|---|---|
| `Plan` | Frozen dataclass: `path`, `step`, `status`, `title`, `branch`, `feature` (the folder relative to `development/`, so the branch name with its `/`; empty for `TEMPLATE.md`), `round_number`, plus `step_name` and `gated` properties. |
| `parse(path: Path) -> Plan \| None` | Parse one plan file, or None if it has no valid marker. |
| `all_plans(project_dir: Path) -> list[Plan]` | Every parseable plan in every feature folder, most recently modified first. |
| `active_plan(project_dir: Path) -> Plan \| None` | The plan the pipeline is working through. |
| `feature_rounds(project_dir: Path, feature: str) -> list[Plan]` | One feature's rounds, oldest first; `feature` is the folder relative to `development/`, as on `Plan.feature`. |
| `git_lines(project_dir: Path, args: list[str]) -> list[str]` | Run git, return output lines. |
| `current_branch(project_dir: Path) -> str` | The checked-out branch, or `""`. |
| `main() -> None` | Showcase: prints the plans found, the active one and its sibling rounds. |

`GATE_FROM_STEP = 8` is the step at which the stop gate starts blocking: steps 3 to 7 are
the build, which carries its own gates and must be able to halt on a red tree.
`PLAN_DIR = development` is the directory it scans; `Plan.feature` is a folder path relative
to it, so a branch-named folder such as `feat/csv-export` comes back with its `/`.

### `.claude/hooks/session_brief.py`

`SessionStart` hook. Injects the active plan's step into a new session's context, the skill
that resumes it (`/build` for steps 3 to 7), plus what any earlier rounds of the same
feature delivered, so work resumes without the user having to re-explain it. Silent when
no plan is active — including while a pull request is open, since step 9 closes the plan.
Stdlib only.

| Signature | Description |
|---|---|
| `brief(project_dir: Path, plan: Plan) -> str` | Describe one active plan's state. |
| `main() -> None` | Entry point: emit the brief as session context. |

### `.claude/hooks/guard_git.py`

`PreToolUse` hook on `Bash`. Refuses a `git commit` or `git push` that would land on
`main`. Reads the command the way a shell does — `shlex` resolves quoting, so a `;` or `|`
inside a commit message stays part of the message — then splits it on the real separators
into one invocation per segment. The grouping delimiters `(`, `)`, `{` and `}` split too, so
a command hidden inside `(git commit -m "x")` is seen rather than left with `(` sitting
where its name should be.

Each segment is judged against the branch that will be checked out when it runs. Only `&&`
guarantees its left side succeeded, so a branch switch carries forward across a run of
separators that is `&&` and newlines, and across nothing else: `git checkout -b feat/x &&
git commit` is allowed from `main`, and so is the same pair with the `&&` ending the line,
while `;`, `|`, `||`, `&`, a bare newline or a mixed run such as `; &&` is refused. A switch
that may not have taken effect here is distrusted the same way: one made inside a subshell
that has since closed, or aimed elsewhere by a global `-C`, `--git-dir` or `--work-tree`,
leaves the branch as it was. What still cannot be read is refused when it names `commit` or
`push` — matched on word boundaries, so `committee` is not a commit — while `main` is
checked out, and allowed anywhere else.

Within a segment it finds the command name where a shell would, after the prefix of
variable assignments and redirections, so `GIT_EDITOR=true git commit` and
`>log git commit` are seen. Backticks around a substitution are stripped, the executable is
matched without regard to case, and a short list of wrapper programs — `sudo`, `env`,
`time`, `nohup`, `doas` — is stepped over. That list is deliberately incomplete: a wrapper
nobody listed is a miss, which is safe, while scanning a segment for any `git` token would
refuse `echo git commit`, which is the failure this module treats as worse. Only options are
skipped after a wrapper, never a bare word, so an option that takes a value hides what
follows it.

A push's destination is read with the same care. The arguments are walked rather than
filtered, so an option that takes a value — `-o`, `--push-option`, `--repo`,
`--receive-pack`, `--exec` — does not leave its value standing where the remote should be,
and `git push -o ci.skip origin` is seen as the bare push it is. Every ref is then reduced
to the branch it names: a leading `+` dropped, the destination half of a `src:dst` pair
taken, `refs/heads/` stripped, backticks removed and `@` read as `HEAD`. Switch targets go
through the same reduction, so `git checkout refs/heads/main` is a switch to `main`.

A branch switch whose target only the running shell can resolve — `git checkout -`,
`@{-1}` — leaves the branch *unknown* rather than unchanged, and a `commit` or `push` that
meets an unknown branch is refused with a message saying so rather than the one about
`main`. Stdlib only.

| Signature | Description |
|---|---|
| `Segment` | Frozen dataclass: `tokens` and the `separator` that preceded them — one of `SEPARATORS`, a newline, or a grouping delimiter (`""` for the first). |
| `segments(command: str) -> list[Segment] \| None` | Split a command into invocations, or None if it cannot be read. |
| `git_subcommand(tokens: tuple[str, ...]) -> tuple[str, tuple[str, ...]]` | Identify the git subcommand and its arguments. |
| `push_targets_main(args: tuple[str, ...], branch: str) -> bool` | Whether a push would update `main`. |
| `switch_target(subcommand: str, args: tuple[str, ...]) -> str` | The branch a `checkout`/`switch` moves to, `""` when it moves none, or the sentinel `UNRESOLVED` (`"?"`) for a target only the running shell can resolve — `-` and `@{-1}`. |
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
7, blocking from step 8 and whenever no plan is active, and only when a Python file changed
in the tree or on the branch. When it blocks it runs ruff, mypy
and pytest, cross-checks `STRUCTURE.md` against the modules on disk, reports any test file
sitting outside `tests/` where `pytest` would silently never collect it, and reports any
package directory under `src/` missing its `__init__.py`. Bypass with
`.claude/.skip-gate`. Stdlib only.

| Signature | Description |
|---|---|
| `venv_tool(project_dir: Path, name: str) -> Path \| None` | Locate a tool in the project venv. |
| `capture(cmd: list[str], cwd: Path, timeout: int) -> CompletedProcess[str]` | Run a command, capturing output. |
| `changed_python_files(project_dir: Path) -> set[str]` | Python files changed in the tree or on this branch. |
| `tracked_python_files(project_dir: Path) -> set[str]` | All non-ignored Python files. |
| `structure_problems(project_dir: Path) -> list[str]` | File-level drift between this file and disk. |
| `stray_test_files(project_dir: Path) -> list[str]` | Test files outside `tests/`, which pytest never collects. |
| `missing_init_files(project_dir: Path) -> list[str]` | Package directories under `src/` with no `__init__.py`. |
| `gate_failures(project_dir: Path) -> list[str]` | Run the verification set, collect failures. |
| `advisory_notes(project_dir: Path, plan: Plan, changed: set[str]) -> list[str]` | Non-blocking observations for the steps below the gate. |
| `notice(message: str) -> None` | Show the user a message without blocking. |
| `block(reason: str) -> None` | Emit the block decision and exit. |
| `enforce(project_dir: Path) -> None` | Run the verification set and block on failure. |
| `main() -> None` | Entry point: decide whether the turn may end. |
