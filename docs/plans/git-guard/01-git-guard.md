# Git guard: quote-aware command parsing

<!-- claude-plan step=5 status=active -->

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
| 3 | Implement | `/implement` | done |
| 4 | Verify | `/verify` | done |
| 5 | Test | `/test` | in progress |
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
| `.claude/hooks/stop_gate.py` | changed in step 5 | Covered by tests, which found a defect in `PATH_IN_TEXT`. One-line fix; see section 3. |

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
3. Handle newline boundaries inside `segments()`. A newline is ordinary whitespace to the
   lexer, so `git checkout -b x` and `git commit` written on two lines would otherwise
   collapse into one invocation and the commit would never be examined — a regression
   against today. Claim the newline as punctuation instead: pass it in
   `punctuation_chars` and drop it from the lexer's `whitespace`, so it arrives as a
   separator token of its own while a newline inside a quoted message stays part of that
   token. *(Corrected in step 3; see section 3.)*
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

**The newline mechanism is not the one the plan specified.** Section 2 said to detect a
line boundary by comparing the lexer's `lineno` before and after each token against the
newlines inside the token. Tried first, and it is wrong: `shlex` consumes the whitespace
that *terminates* a token as part of reading that token, so the line break is attributed to
the token before the boundary rather than the one after it. Lexing
`git checkout -b x` + newline + `git commit -m "y"` marks `x` as newline-preceded and the
following `git` as not, putting the split one token early.

What replaced it is simpler than what was planned rather than more complex: pass the
newline in `punctuation_chars` and remove it from the lexer's `whitespace`, and it arrives
as its own token like any other separator, while a newline inside a quoted commit message
stays inside that token. The implementation guide in section 2 has been corrected to match.
No public signature changed, so the Public API table stands as planned.

**A run of separators is reduced by a new private helper, `_join`.** Not in the plan.
Writing the splitter surfaced a case the plan had not considered: an `&&` chain written
across two lines produces `&&` and a newline as consecutive separator tokens. Taking the
last would make the join non-guaranteeing and refuse
`git checkout -b x &&` + newline + `git commit` — a false positive on a perfectly ordinary
multi-line chain, and the same class of annoyance as the defect this round exists to fix.
A run containing `&&` therefore keeps its guarantee. Private, so it stays out of
`STRUCTURE.md` and out of the Public API table.

**Everything else was built as planned.** All seven public signatures match the section 2
table exactly.

### Added in step 5, when the tests found bugs

**Two bypasses in the step 3 code, both mine, both found by the suite.** Neither was in
the original defect; both were introduced by the rewrite and would have shipped without
these tests.

`shlex` groups a *run* of punctuation into one token, so `&&` followed by a newline arrives
as the single token `"&&\n"` and `;` followed by a newline as `";\n"`. Neither matched
`SEPARATORS`, so both were swallowed as ordinary words and the whole command collapsed into
one segment — leaving `git status ;` + newline + `git push origin main` **allowed on
`main`**. Separator detection now works on characters (`SEPARATOR_CHARS`) rather than whole
tokens, and `_governs` reduces a run to the separator that governs it, keeping the `&&`
guarantee for a chain written across two lines.

The grouping delimiters were the second. `(git commit -m "x")` and `{ git commit -m "x"; }`
were **allowed on `main`**, because `(` or `{` sat where the command name should be and
`git_subcommand` never saw `git` behind it. Those delimiters begin and end a command list,
so they now separate invocations too.

Step 3's own probe had reported the `&&`-across-lines case as allowed and read it as the
guarantee working correctly. It was not — the command was collapsing into one segment and
the commit was never examined. A probe that checks only the verdict cannot tell those
apart; the test that asserts on the *segmentation* can, which is why it caught it.

**`stop_gate.py` changed, and section 1 said it would not.** Its own tests found that
`PATH_IN_TEXT` (`[\w./-]+\.py`) cannot match a placeholder path whole: on
`src/<package>/module.py` it matches only the `/module.py` tail, which then passes the
`PLACEHOLDER` filter because the `<` and `>` are outside the match. The gate therefore
reports prose as a deleted file and blocks, clearable only by rewording documentation. The
character class now includes `<>*` so the filter sees what it was always meant to see.

This is a genuine defect found by this round's own tests, in a module this round was
explicitly testing — but section 1 listed no production change to it, so it is scope the
concept did not authorise. One line, and it fails toward blocking rather than allowing, so
it was taken rather than deferred. **Step 6 should judge this against the concept, not wave
it through**, and section 2's Modules table has been corrected to match.

---

## 4. Verification log

| Check | Result |
|---|---|
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `30 files already formatted` |
| `mypy` | `Success: no issues found in 8 source files` |
| `pytest` | `4 passed in 0.01s` — the existing suite; the new one is step 5 |
| Plan completeness | every signature in the Public API table exists as written (table below) |
| `STRUCTURE.md` | in sync; auditor run, two edits applied |
| Hook run standalone | refuses on `main`, allows when the command branches first (below) |

One failure was fixed during step 3 and is recorded here for completeness: Ruff's `D301`
on a docstring containing a backslash escape. Reworded the sentence to avoid the escape
rather than adding an `r` prefix to a docstring that has no other reason to be raw. No
suppressions were added anywhere in this change — no `# noqa`, no `# type: ignore`.

### Plan completeness

Signatures read back out of the imported module with `inspect`, not by eye.

| Planned | Found | Verdict |
|---|---|---|
| `Segment` — frozen, `tokens: tuple[str, ...]`, `separator: str` | `frozen=True fields=(tokens: tuple[str, ...], separator: str)` | match |
| `segments(command: str) -> list[Segment] \| None` | identical | match |
| `git_subcommand(tokens: tuple[str, ...]) -> tuple[str, tuple[str, ...]]` | identical | match |
| `push_targets_main(args: tuple[str, ...], branch: str) -> bool` | identical | match |
| `switch_target(subcommand: str, args: tuple[str, ...]) -> str` | identical | match |
| `violation(command: str, branch: str) -> str` | identical | match |
| `main() -> None` | identical | match |

Public names defined in the module: exactly those seven. Nothing missing, nothing
unplanned. `_is_newline` and `_join` are private and correctly absent from both the table
and `STRUCTURE.md`.

### STRUCTURE.md audit

The `structure-auditor` subagent found no signature drift anywhere in the repo — all five
hooks, both package modules and the test file are present and accurate, and no entry names
a file that no longer exists. Two edits returned and applied:

1. The "Keeping this file current" paragraph said the hooks are held to the package's
   standard by mypy alone. It now also names the pytest `pythonpath` entry, which is what
   makes `import guard_git` resolve from the suite — the thing a reader needs before
   writing step 5's tests.
2. The `Segment` row now says the separator is `""` for the first invocation, matching the
   detail the `Plan` row carries in `plan_state`'s table.

It also noted, for step 5 rather than here, that each new test file will need its own entry
under `## Tests:` or `stop_gate.structure_problems` will block.

### Standalone run

`guard_git.py` is an executable script, not a library module, so `main()` is its entry
point and the showcase form in `.claude/rules/python.md` does not apply — the rule exempts
"anything under `.claude/hooks/`". It was therefore exercised the way it actually runs: a
JSON payload on stdin, against a throwaway repository checked out on `main`.

```
$ echo '{"tool_input":{"command":"git commit -m \"Add parser; drop the old one\""},
         "cwd":"<throwaway repo on main>"}' | python .claude/hooks/guard_git.py
Refused: this would commit to `main`, which this repo never commits to directly.
Move the work onto a branch first, keeping the changes:
    git checkout -b <type>/<kebab-case-topic>
Prefixes: feat, fix, refactor, docs, test, chore.
exit=2

$ echo '{"tool_input":{"command":"git checkout -b feat/x && git commit -m \"ok\""},
         "cwd":"<throwaway repo on main>"}' | python .claude/hooks/guard_git.py
exit=0
```

The first is the bypass this round closes, refused through the real entry point rather than
through `violation()` alone. The second is the false positive it removes.

### Behaviour probe

Not the test suite — that is step 5 — but 29 cases were run across A1 to A5 while
implementing, covering every bypass, the branch-switch rules for `&&`, `;`, `||` and
newline, the unreadable-input cases, and every push refspec shape. All 29 behaved as
specified. They become real tests in step 5 rather than staying a one-off script.

---

## 5. Test log

190 tests, all passing. 186 are new; the remaining 4 are the placeholder suite that was
already there.

| Intent | Test names | Result |
|---|---|---|
| T1 — punctuation in a commit message | `test_violation_refuses_a_commit_whose_message_carries_punctuation` (6 cases: `;`, `\|`, `&&`, `\|\|`, `&`, newline), `test_violation_allows_those_same_commits_off_main` | pass |
| T2 — a guaranteed switch | `test_violation_allows_a_commit_after_a_guaranteed_switch_away` (3 cases), `test_violation_refuses_a_commit_after_a_switch_to_main`, `test_violation_refuses_a_push_after_a_switch_to_main`, `test_violation_carries_a_switch_through_an_intervening_command` | pass |
| T3 — a switch that may not have run | `test_violation_distrusts_a_switch_that_may_not_have_run` (4 cases), `test_violation_resets_the_branch_after_a_weak_separator`, `test_violation_trusts_a_switch_joined_across_lines_by_and`, `test_violation_splits_a_separator_glued_to_a_newline` (4 cases), `test_violation_trusts_and_glued_to_a_newline` | pass |
| T4 — unreadable input | `test_violation_refuses_unreadable_input_naming_a_risky_subcommand` (2 cases), `test_violation_allows_unreadable_input_off_main`, `test_violation_allows_unreadable_input_naming_nothing_risky`, `test_segments_returns_none_for_an_unbalanced_quote` | pass |
| T5 — everything that already held | `test_violation_refuses_every_push_that_would_reach_main` (7 cases), `test_push_targets_main_recognises_every_refspec_shape` (6 cases), `test_violation_refuses_a_plain_commit_on_main`, `test_violation_refuses_a_commit_reached_through_a_directory_option`, `test_violation_ignores_commands_that_are_not_git` (4 cases), `test_violation_sees_through_grouping_delimiters` (4 cases), and the rest of the `git_subcommand`, `push_targets_main` and `switch_target` blocks | pass |
| T6 — the hooks import as modules | every test in all three files; collection would fail otherwise | pass |
| T7 — `plan_state` | `tests/test_plan_state.py`, 36 tests across `Plan`, `parse`, `all_plans`, `active_plan`, `feature_rounds`, `git_lines`, `current_branch` | pass |
| T8 — `stop_gate` | `tests/test_stop_gate.py`, 38 tests across `venv_tool`, `capture`, `changed_python_files`, `tracked_python_files`, `structure_problems`, `stray_test_files`, `missing_init_files`, `gate_failures`, `advisory_notes`, `notice`, `block` | pass |
| T9 — the tree stays green | `ruff check .`, `ruff format --check .`, `mypy` (11 files), `pytest` (190) | pass |

### What the tests found

Three real defects, all fixed in this step and all recorded in section 3:

1. **A separator run collapsed a command into one segment**, so `git status ;` + newline +
   `git push origin main` was allowed on `main`. A bypass, introduced by step 3.
2. **Grouping delimiters hid the command behind them**, so `(git commit -m "x")` was
   allowed on `main`. A bypass, introduced by step 3.
3. **`stop_gate.PATH_IN_TEXT` could not match a placeholder path whole**, so the gate
   reported prose as a deleted file. Pre-existing, and out of the scope section 1 set.

### Edge cases considered and deliberately skipped

- **A quoted argument that is nothing but separator characters** — `git commit -m "&&"`.
  `shlex` does not report whether a token was quoted, so the argument is read as a
  separator and the command splits. It errs toward refusing rather than allowing: the
  `git commit` part still forms its own segment and is still caught. Left as is, since the
  only fix is a second parser that tracks quoting, and the failure direction is safe.
- **Git aliases** — `git ci` for `git commit`. Resolving them means reading git config, and
  section 1 put it out of scope.
- **A git command nested inside another interpreter** — `bash -c "git commit -m x"`,
  `ssh host git commit`. The outer command is not git, so the guard allows it. Detecting
  this means parsing arbitrary nested shells, which is the point at which a guard for slips
  becomes a sandbox.
- **Command substitution** — `$(git commit)`, backticks. Same reasoning; also not a form
  anyone reaches for by accident.
- **`None` and non-string commands.** `main()` already type-checks its payload before
  calling `violation`, and `mypy` covers the internal path, so a test would only prove
  Python raises `AttributeError`.
- **Windows executable layouts beyond `git.exe`.** `git_subcommand` normalises with
  `Path(...).name`, covered by the `/usr/bin/git` and `git.exe` cases; enumerating more
  spellings proves nothing further.

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
