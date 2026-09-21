# Git guard: quote-aware command parsing

<!-- claude-plan step=3 status=active -->

| Field | Value |
|---|---|
| Feature | `git-guard` (the folder) |
| Round | `1` |
| Branch | `claude/setup-recommendations-qoyxhf` |
| Started | `2026-09-21` |

## Progress

| # | Step | Skill | Status |
|---|---|---|---|
| 1 | Conceptualize | `/conceptualize` | done |
| 2 | Plan | `/plan` | done |
| 3 | Implement | `/implement` | pending |
| 4 | Verify | `/verify` | pending |
| 5 | Test | `/test` | pending |
| 6 | Concept check | `/concept-check` | pending |
| 7 | Ship | `/ship` | pending |
| 8 | Recommend | `/recommend` | pending |
| 9 | Pull request | `/create-pr` | pending |
| 10 | Review | `/watch-pr` | pending |

Statuses: `pending`, `in progress`, `done`.

## Builds on

Nothing — this is the first round.

---

## 1. Concept

### What this is

The three substantial hooks stop being exempt from the standards this repo applies to
everything else. `guard_git.py` currently splits a shell command with a regex that does not
understand quoting; the fragments it produces are rejected by `shlex.split`, dropped as
unparseable, and the command is allowed through. Its parsing is rebuilt to tokenize first
and split second, to follow branch switches within a compound command, and to refuse rather
than allow the residue it still cannot read when that residue names `commit` or `push` on
`main`. Alongside it, `guard_git.py`, `plan_state.py` and `stop_gate.py` get the test
coverage they have never had.

One concept, not two: the defect and the missing tests are the same omission seen from two
sides. The hooks are type-checked by `[tool.mypy] files` and documented in `STRUCTURE.md`
with full signature tables — treated as first-class code everywhere except in `tests/`, and
`.claude/rules/python.md` says every public function has tests. `guard_git.py` is what that
gap cost.

### Why it is worth building

The guard is the only control that refuses a commit to `main` *before* it happens. The
remote ruleset rejects a push afterwards; a local commit on `main` has to be unpicked by
hand. Today the guard is bypassed by ordinary punctuation:

```python
violation('git commit -m "Add parser; drop the old one"', "main")  # -> "" (ALLOWED)
violation('git commit -m "Handle a|b correctly"', "main")  # -> "" (ALLOWED)
violation('git commit -m "Fix && polish"', "main")  # -> "" (ALLOWED)
```

A second defect points the other way: `git checkout -b feat/x && git commit -m "..."` is
refused while on `main`, because the branch is read as it is now rather than as it will be
when `commit` runs — so the recovery the refusal message itself recommends fails when
written as one command. A guard that both misses real violations and blocks legitimate work
is one people switch off.

This is also a template repository. Every repo created from it inherits these files, so the
fix is paid once and collected on every project started from here.

### Inputs and outputs

`guard_git.py` reads a JSON payload on stdin (`tool_input.command`, `cwd`) and communicates
by exit code: `0` allows, `2` blocks and shows the text written to stderr. Its core is the
pure function `violation(command: str, branch: str) -> str` — the reason to refuse, or `""`
to allow — which is what the tests exercise directly.

`plan_state.py` turns the plan files and `git` output into `Plan` records. `stop_gate.py`
turns the filesystem, `git` and the tools in `.venv` into a block-or-allow decision. Neither
changes in this round; both gain tests.

The tests add no runtime inputs or outputs. They import the hooks as modules and drive their
public functions, which requires the hooks to be importable from the suite.

### How it connects to the rest of the repo

- `.claude/hooks/guard_git.py` imports `current_branch` from `.claude/hooks/plan_state.py`;
  that dependency is unchanged.
- `.claude/settings.json` registers the hook on `PreToolUse`/`Bash`; its registration is
  unchanged, so no Claude Code restart is needed for the parsing fix to take effect beyond
  the usual one.
- `tests/` gains one file per hook covered. `pyproject.toml` gains `.claude/hooks` on
  `[tool.pytest.ini_options] pythonpath` so `import guard_git` resolves in the suite the
  same way it resolves for a sibling hook at runtime.
- `STRUCTURE.md` must name every new test file: `stop_gate.structure_problems` blocks on any
  tracked `.py` file it does not mention.
- Nothing under `src/` is touched, and neither is the branch ruleset.

### Explicitly out of scope

- `lint_py.py` and `session_brief.py` — thin wrappers over Ruff and over `plan_state`, and
  covering them is not what this round is for.
- Making `PROTECTED` configurable. `main` stays hardcoded.
- Git aliases (`git ci` for `git commit`). Resolving them means reading git config; the
  allow-what-cannot-be-parsed posture covers them.
- Any protection beyond `main` — force-push policy on feature branches, protected tags.
- The two stop-gate checks proposed in `docs/BACKLOG.md` §3.4 (two active plans, the
  `main()` guard rule). Adding checks is a different round from testing what exists.
- `plan_state.py`'s module docstring calling this a "nine-step pipeline" when it has ten
  steps. A docstring reword is `/small-change` and should not ride along in here.
- CI, declined in `docs/BACKLOG.md` §2.

### Acceptance criteria

| # | The finished feature... |
|---|---|
| A1 | Refuses a commit to `main` whose message contains a shell metacharacter — `;`, `|`, `&&` or a newline — where today all four are allowed through. |
| A2 | Allows a compound command that switches to a non-`main` branch before committing (`git checkout -b feat/x && git commit -m "..."`), while still refusing one that switches *to* `main` before committing. |
| A3 | Treats a branch switch as effective only when the separator guarantees it ran: across `&&`, later segments are judged against the switched-to branch; across `;` and `\|\|`, where the switch may have failed and the commit still runs, they are judged against the branch checked out now. |
| A4 | Refuses a command it cannot parse when that command names `commit` or `push` and `main` is checked out, saying that it could not read the command — and allows the same unparseable command on any other branch. |
| A5 | Still refuses everything it refuses today: `git commit` on `main`, bare `git push` on `main`, and `git push` naming `main` as `origin main`, `HEAD:main`, `refs/heads/main`, `+main`, `--all` or `--mirror`; and still allows all of those on a feature branch, plus every non-git command. |
| A6 | Ships a pytest suite under `tests/` that imports `guard_git`, `plan_state` and `stop_gate` as modules and passes under a plain `pytest` from the repo root. |
| A7 | Covers every public function named in those three modules' `STRUCTURE.md` signature tables, except that the functions which would otherwise execute the repo's own toolchain or exit the interpreter — `gate_failures`, `enforce`, `main` — are driven with a stubbed tool directory and a captured exit, never by invoking Ruff, mypy or pytest recursively. |
| A8 | Leaves `ruff check .`, `ruff format --check .`, `mypy` and `pytest` green, with `STRUCTURE.md` naming every file added. |

### Open questions

None. Two were raised and settled during this step:

- *What should the guard do with what it still cannot parse?* Refuse it when it names
  `commit` or `push` on `main`, allow it otherwise (A4). Genuinely unparseable input would
  usually fail in the shell anyway, so the cost of refusing is close to zero, while allowing
  it leaves the hole open in principle.
- *How wide is this round?* All three substantial hooks, agreed rather than `guard_git.py`
  alone. `lint_py.py` and `session_brief.py` stay out.

---

## 2. Plan

### Approach

Tokenize first, split second. `shlex.shlex(command, posix=True, punctuation_chars=True)`
with `whitespace_split = True` is a shell-aware lexer: it respects quoting, and it emits
`&&`, `||`, `;`, `|` and `&` as their own tokens even when they are glued to a word. The
parser therefore stops manufacturing the unparseable fragments it currently chokes on, and
`git commit -m "a";git push` — flagged in `docs/BACKLOG.md` §1 as a case needing to be
pinned down — parses correctly with no special handling. Splitting the token stream on
those separator tokens gives one invocation per segment, each tagged with the separator
that preceded it, which is what criterion A3 needs to decide whether a branch switch can be
trusted. `violation()` then walks the segments carrying an effective branch forward across
`&&` and resetting it on every other separator.

Rejected — **keep `segments()` returning `list[list[str]]`** and merely swap the regex for
the lexer. It is the smallest possible diff and it fixes A1, A4 and A5, but it throws away
which separator joined two invocations, so A2 and A3 cannot be expressed at all. The
rejection cost is one dataclass.

Rejected — **extract shell parsing into a new `.claude/hooks/shell_parse.py`** shared by
all hooks. Cleaner long-term shape, but `lint_py.py` and `session_brief.py` parse no shell,
so it would be a module with one consumer. Worth revisiting the day a second hook needs it;
today it is structure for its own sake.

### Modules

| Path | New or changed | Purpose |
|---|---|---|
| `.claude/hooks/guard_git.py` | changed | Quote-aware parsing, branch-switch tracking, and refusal of unreadable commit/push on `main`. |
| `pyproject.toml` | changed | `[tool.pytest.ini_options] pythonpath` gains `.claude/hooks`, so the suite imports the hooks the same way a sibling hook does at runtime. |
| `STRUCTURE.md` | changed | The `guard_git.py` signature table, which step 4 checks literally. |
| `.claude/hooks/plan_state.py` | unchanged | Covered by tests in step 5; no production change. |
| `.claude/hooks/stop_gate.py` | unchanged | Covered by tests in step 5; no production change. |

Test files are step 5's output, not step 3's, and are listed under Test intents below.

### Public API

| Signature | Module | Purpose | Covers |
|---|---|---|---|
| `Segment` | `guard_git` | Frozen dataclass: `tokens: tuple[str, ...]`, `separator: str` — one invocation and the separator that preceded it (`""` for the first). | A3 |
| `segments(command: str) -> list[Segment] \| None` | `guard_git` | Split a command into invocations, or `None` when it cannot be lexed. | A1, A4 |
| `git_subcommand(tokens: tuple[str, ...]) -> tuple[str, tuple[str, ...]]` | `guard_git` | Identify the git subcommand and its arguments. | A5 |
| `push_targets_main(args: tuple[str, ...], branch: str) -> bool` | `guard_git` | Whether a push would update `main`. | A5 |
| `switch_target(subcommand: str, args: tuple[str, ...]) -> str` | `guard_git` | The branch a `checkout`/`switch` moves to, or `""`. | A2 |
| `violation(command: str, branch: str) -> str` | `guard_git` | The reason to refuse, or `""` to allow. | A1-A5 |
| `main() -> None` | `guard_git` | Entry point: allow or refuse the command. | A5 |

`git_subcommand` and `push_targets_main` change parameter type from `list[str]` to
`tuple[str, ...]` so the whole parsing path is immutable and `Segment` can stay frozen in
substance rather than only in name. Both are documented in `STRUCTURE.md` and both changes
must land there in the same edit.

### Implementation guide

1. Add the `Segment` frozen dataclass and the separator constants: the set of separator
   tokens (`&&`, `||`, `;`, `|`, `&`) and the single guaranteeing one (`&&`).
2. Replace `SEPARATORS`-based splitting in `segments()` with the `shlex` lexer, returning
   `None` on `ValueError` instead of dropping fragments.
3. Handle newline boundaries inside `segments()`. `punctuation_chars` treats `\n` as plain
   whitespace, so `git checkout -b x\ngit commit` would otherwise collapse into one
   invocation and the commit would never be examined — a regression against today. Detect
   a boundary by comparing the lexer's `lineno` before and after each token against the
   count of newlines inside the token itself; a newline outside a token starts a new
   segment with a non-guaranteeing separator. A newline *inside* a quoted commit message
   must not split.
4. Retype `git_subcommand` and `push_targets_main` to `tuple[str, ...]`.
5. Add `switch_target`: the first non-option positional of `checkout`/`switch`, honouring
   `-b`/`-B`/`-c`/`-C` and stopping at `--`.
6. Rewrite `violation()`: `None` from `segments()` refuses when the raw command mentions
   `commit` or `push` and `branch == PROTECTED`, otherwise allows; then walk the segments
   carrying an effective branch forward across `&&` only, resetting to the real branch on
   every other separator, applying `switch_target` after each segment is judged.
7. Add the refusal text for the unreadable case, saying what could not be read.
8. Update the `guard_git.py` signature table in `STRUCTURE.md`.
9. Add `.claude/hooks` to `pythonpath` in `pyproject.toml`.

### Test intents

| # | Must prove | Covers |
|---|---|---|
| T1 | A commit on `main` is refused when its message contains `;`, `\|`, `&&` or a newline — the four cases that are allowed through today. | A1 |
| T2 | `git checkout -b feat/x && git commit` is allowed on `main`; `git checkout main && git commit` is refused from a feature branch. | A2 |
| T3 | A switch joined by `;`, `\|\|`, `&` or a newline does not take effect: the later commit is judged against the branch actually checked out. | A3 |
| T4 | An unlexable command naming `commit`/`push` on `main` is refused and the message says it could not be read; the same input on a feature branch is allowed; an unlexable command naming neither is allowed on `main`. | A4 |
| T5 | Every refusal that holds today still holds: `git commit` on `main`; `git push` bare, `origin main`, `HEAD:main`, `refs/heads/main`, `+main`, `--all`, `--mirror`; `git -C path commit`; and all of them allowed on a feature branch, with non-git commands ignored everywhere. | A5 |
| T6 | `guard_git`, `plan_state` and `stop_gate` import as modules under a plain `pytest` from the repo root. | A6 |
| T7 | `plan_state`'s public surface behaves: `parse` on a valid marker, a missing marker, an out-of-range step, a file with no Branch row and no title; `all_plans` ordering and recursion; `active_plan` when none, one or several are active; `feature_rounds` ordering; `git_lines` and `current_branch` against a real temporary repo, including detached HEAD and a non-repo directory; `Plan.step_name` and `.gated` at the boundary step. | A7 |
| T8 | `stop_gate`'s file-level checks behave against temporary trees: `venv_tool` for both layouts and neither; `capture` returning output and honouring its timeout; `changed_python_files` and `tracked_python_files`; `structure_problems` in both directions; `stray_test_files`; `missing_init_files`; `advisory_notes` for each note it can emit; `notice` and `block` exiting zero with the right JSON; and `gate_failures` driven through a monkeypatched `venv_tool`/`capture` rather than real executables. | A7 |
| T9 | The full suite, `ruff check .`, `ruff format --check .` and `mypy` are green, and `STRUCTURE.md` names every file added. | A8 |

### Risks

**Fake executables do not port.** `gate_failures` runs whatever `venv_tool` finds, and
building real stub executables would need a shell script on POSIX and an `.exe` on Windows,
which this repo targets first. T8 therefore monkeypatches `venv_tool` and `capture` instead
of creating executables, and `venv_tool` itself is tested by touching files and never
running them.

**Recursion.** Testing `gate_failures` for real would run `pytest` inside `pytest`. The
monkeypatch above is what prevents it; this is why A7 carries its exception clause.

**Git-dependent tests.** `plan_state` and `stop_gate` shell out to `git`, so their tests
need throwaway repositories built in `tmp_path` with `git init` and an initial commit. If
git is absent the helpers return empty rather than raising, which those tests must assert
rather than accidentally rely on.

**`punctuation_chars` widens what counts as punctuation.** `<`, `>`, `(` and `)` also
become tokens, so a redirection such as `git log > out.txt` now splits mid-invocation.
Harmless — the subcommand is still `log` — but worth a case in T5 so the behaviour is
recorded rather than discovered.

**A public signature change.** `git_subcommand` and `push_targets_main` change parameter
type. Step 4 checks the code against the Public API table character by character, so
`STRUCTURE.md` and the table must agree exactly.

---

## 3. Implementation notes

> Written in step 3. Only deviations from the plan above, each with its reason. "Built as
> planned" is a complete and good entry.

---

## 4. Verification log

> Written in step 4: the static half. Command output, not a summary of it.

| Check | Result |
|---|---|
| `ruff check .` | |
| `ruff format --check .` | |
| `mypy` | |
| Plan completeness | every signature in the Public API table exists as written |
| `STRUCTURE.md` | in sync |
| `python -m <package>.<module>` | |

---

## 5. Test log

> Written in step 5: the dynamic half.

| Intent | Test names | Result |
|---|---|---|

Edge cases considered and deliberately skipped, with reasons:

---

## 6. Concept check

> Written in step 6, against section 1 — not against section 2. The question is whether
> the thing built is the thing agreed, not whether it matches the plan.

| # | Criterion | Met | Evidence |
|---|---|---|---|
| A1 | | | |

Drift found, and what was done about it:

### Earlier rounds still hold

> Later rounds only. Re-check every acceptance criterion from every earlier round in this
> folder: this round changed code they depend on, and their tests passing is necessary but
> not sufficient — a criterion can be satisfied by tests that no longer describe what the
> feature does.

| Round | # | Criterion | Still met | Evidence |
|---|---|---|---|---|

---

## 7. Ship log

| Field | Value |
|---|---|
| Commits | |
| Pushed to | |

---

## 8. Recommendations

> Written in step 8. Follow-up work this change makes possible or desirable. Not bugs —
> a bug found here goes back to step 3 before shipping.

| # | Recommendation | Why it helps | Effort | Decision |
|---|---|---|---|---|
| R1 | | | | |

Decisions: `deferred`, `rejected`, or `next round` — a new numbered file in this folder,
taken back through steps 1 to 7 on the same branch.

---

## 9. Pull request

| Field | Value |
|---|---|
| URL | |
| Opened as | ready for review |

---

## 10. Review log

> Written in step 10, one row per review thread. The record of how the pull request got
> from opened to merged — the part nobody can reconstruct from the diff later.
>
> Quiet check-ins are not recorded. Nineteen rows of "nothing had changed" is noise.

| Thread | Who asked for what | Outcome |
|---|---|---|

Outcomes: `fixed and pushed`, `replied, left open`, `round N`, or — for a bot finding —
`dismissed: <reason>`. Every dismissal is also reported to the user, never only recorded here.

### Outcome

| Field | Value |
|---|---|
| Merged or closed | |
| Merge commit | |
| Instructed by | who said to merge, and where |
| Bot findings dismissed | each one, with its reason |
