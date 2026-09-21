# Git guard: quote-aware command parsing

<!-- claude-plan step=2 status=active -->

| Field | Value |
|---|---|
| Feature | `git-guard` (the folder) |
| Round | `1` |
| Branch | _set in step 3_ |
| Started | `2026-09-21` |

## Progress

| # | Step | Skill | Status |
|---|---|---|---|
| 1 | Conceptualize | `/conceptualize` | done |
| 2 | Plan | `/plan` | pending |
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
violation('git commit -m "Add parser; drop the old one"', "main")   # -> "" (ALLOWED)
violation('git commit -m "Handle a|b correctly"', "main")           # -> "" (ALLOWED)
violation('git commit -m "Fix && polish"', "main")                  # -> "" (ALLOWED)
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

> Written in step 2. Concrete enough that step 3 is transcription, not invention.

### Approach

One paragraph on the chosen approach, and one on what was rejected and why.

### Modules

| Path | New or changed | Purpose |
|---|---|---|

### Public API

> Every public class and function, with its full signature as it will be written.
> `Covers` links back to the acceptance criteria above.

| Signature | Module | Purpose | Covers |
|---|---|---|---|

### Implementation guide

Ordered. Each entry small enough to finish and check.

1.
2.

### Test intents

> High-level: what a test must prove, not how it is written. Step 5 turns each of these
> into concrete cases, including the edge cases.

| # | Must prove | Covers |
|---|---|---|
| T1 | | |

### Risks

What could make this harder than it looks, and the plan if it does.

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
