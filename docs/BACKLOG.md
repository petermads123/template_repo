# Backlog — Claude setup improvements

Findings from a review of this repo's Claude configuration (`.claude/`, the hooks, the
ruleset, `pyproject.toml`), September 2026.

This is **not** a plan file. It carries no `claude-plan` marker and lives outside
`docs/plans/`, which is the only directory `.claude/hooks/plan_state.py` scans — so nothing
here affects the pipeline's state. Items graduate out of this file by becoming a plan
folder under `docs/plans/`, at which point delete the entry here.

| Status | Meaning |
|---|---|
| **confirmed** | Reproduced. The diagnosis below is verified, not a hunch. |
| **proposed** | Judgment call, not yet discussed. |
| **rejected** | Considered and declined; the reason is recorded so it is not re-litigated. |

---

## 1. `guard_git.py` fails open on quoted shell separators — **confirmed**

**Severity: high.** This is the one control that stops a commit landing on `main` before it
happens, and it can be walked past with ordinary punctuation.

### Reproduction

Run from the repo root with `.claude/hooks` importable:

```python
from guard_git import violation, segments

violation('git commit -m "Add parser; drop the old one"', "main")   # -> "" (ALLOWED)
violation('git commit -m "Handle a|b correctly"', "main")           # -> "" (ALLOWED)
violation('git commit -m "Fix && polish"', "main")                  # -> "" (ALLOWED)
```

All three commit to `main` with the hook installed and enabled. For comparison,
`git commit -m "Add the parser"` is correctly refused.

### Root cause

`segments()` splits the command with a regex that knows nothing about quoting:

```python
SEPARATORS = re.compile(r"&&|\|\||;|\n|\|")
```

A `;` or `|` inside a commit message is therefore treated as a shell separator.
`git commit -m "Add parser; drop the old one"` is cut into `git commit -m "Add parser` and
`drop the old one"`, both with unbalanced quotes. `shlex.split` raises `ValueError` on each
and the handler drops them:

```python
except ValueError:
    continue  # unbalanced quotes: not something to block on
```

`segments()` returns `[]`, the loop in `violation()` never executes, and the command is
allowed. Confirmed by printing `segments(...)` for each case above: all return `[]`.

The "allow what cannot be parsed" principle is right in general — a guard that blocks
legitimate work is worse than one that misses an exotic invocation. The defect is that the
parser *manufactures* the unparseable input and then fails open on its own damage.

### Second defect, same file

```python
violation('git checkout -b feat/thing && git commit -m "Add the parser"', "main")
# -> refused
```

The hook evaluates against the branch checked out *now*, not the branch that will be
checked out when `commit` runs. So the standard recovery — branch, then commit, on one
line — is refused while on `main`. The refusal message itself recommends
`git checkout -b <type>/<kebab-case-topic>`, so following its advice in a compound command
trips it. Lower severity than the fail-open, but it is the kind of false positive that ends
with someone disabling the guard.

### Fix approach

Tokenize **first**, split **second**. `shlex.split` understands quoting, so run it over the
whole command and partition the resulting token list on bare separator tokens, rather than
regex-splitting the raw string and tokenizing the fragments.

Two things that need pinning down with tests rather than assumed:

- `shlex.split('git commit -m "a";git push')` glues the separator into a single token
  (`a;git`) when it is not surrounded by whitespace. Separators adjacent to quoted text
  need explicit handling.
- The fail-open path must be kept for genuinely unparseable input (a real unbalanced quote
  typed by hand), while no longer being reachable from well-formed commands.

For the second defect: when a segment earlier in the same command switches branch
(`checkout -b`, `checkout <branch>`, `switch -c`, `switch <branch>`), evaluate later
segments against that branch instead of the current one.

### Test cases to pin

Commit messages containing `;`, `|`, `&&`, a newline, and a literal unbalanced quote; both
quote styles; `git -C <path> commit`; `git checkout -b x && git commit`;
`git checkout main && git commit`; `git push` bare on `main` and off it;
`git push origin main`, `HEAD:main`, `refs/heads/main`, `+main`, `--all`, `--mirror`.

### Routing

**`/feature`** — changes behaviour and needs new tests, two of the four small-change
disqualifiers. Proposed round 1 scope: fix both defects in `guard_git.py`, add
`tests/test_guard_git.py` (the first test coverage the hooks have had), and add
`pythonpath = ["src", ".claude/hooks"]` to `[tool.pytest.ini_options]` so the hooks are
importable from the suite. `plan_state.py` and `stop_gate.py` coverage is round 2, not the
same round.

---

## 2. Continuous integration — **rejected**

A GitHub Actions workflow running the four checks on every pull request, plus a
`required_status_checks` rule in the branch ruleset so a red branch cannot merge.

**Declined**: not worth the per-repo overhead on small solo projects.

One consequence to accept knowingly: the CI clauses in `watch-pr` ("CI red — fix it"),
`create-pr` ("CI green") and `CLAUDE.md` ("CI green where there is CI") now describe a
thing that will never exist. They are hedged with "where the repo has any", so nothing
misfires — they are simply dead text. Worth a prose cleanup eventually; not urgent.

---

## 3. Cheap, high value — **proposed**

### 3.1 `.gitignore` entries for `.claude/`

`.gitignore` has no `.claude/` rules, so `.claude/.skip-gate` (a deliberate bypass of every
quality check) and `.claude/settings.local.json` can both be committed. `/ship` step 2
handles this by asking Claude to *notice* `.skip-gate` in `git status`; two ignore lines
cannot forget. Routing: `/small-change` (no file added, no behaviour change).

### 3.2 A `PreCompact` hook

Pipeline state lives in a plan file precisely so it survives a context reset — and a
compaction is the moment that promise is tested. A ten-line hook re-injecting the active
plan's path and step would close the loop. Four of the five hook slots are in use; this is
the one that matters most. Routing: `/feature` (adds a file).

### 3.3 A statusline

`plan_state.py` already computes feature, round, step name and branch. Surfacing
`csv-export · round 2 · step 5 Test · feat/csv-export` permanently makes the single piece
of state the whole system turns on visible at all times. Routing: `/feature` (adds a file).

### 3.4 Two documentation drifts

- `CLAUDE.md` claims "two active plans is a state the hooks will complain about, and
  rightly". They do not. `plan_state.active_plan` explicitly treats it as "a mistake rather
  than an error" and silently returns the most recently modified one; `stop_gate` has no
  check. Either add the check to `gate_failures` — it is as mechanical as
  `missing_init_files` — or soften the sentence.
- `.claude/rules/python.md` spends roughly sixty lines mandating `main()` plus the
  `if __name__` guard on every module. Nothing verifies it.

Routing: the prose fix alone is `/small-change`; adding either check to the stop gate is
`/feature`.

---

## 4. Larger or later — **proposed**

| Item | Why | Routing |
|---|---|---|
| Tests for `plan_state.py` and `stop_gate.py` | The hooks are type-checked and documented in `STRUCTURE.md` with full signature tables, but `python.md` says every public function has tests and none of them do. Round 2 after item 1. | `/feature` |
| `gh` is an undeclared hard dependency | `create-pr` shells out to `gh pr create`/`gh pr edit` and `repo-setup` wants `gh api`. Nothing checks for it, and on Claude Code on the web it does not exist — steps 9 and 10 simply fail there. Either have `repo-setup` verify it, or ship a `.mcp.json` pinning the GitHub MCP server so the PR steps behave identically on every surface. | `/feature` |
| `CODEOWNERS` | `main_protect.collab.json` can set `require_code_owner_review`, and the collab ruleset is offered without the file that gives it meaning. Also auto-routes the approver named in `CLAUDE.md`. | `/small-change` |
| Pin the toolchain | `pytest`, `ruff` and `mypy` are unbounded in `[project.optional-dependencies]`. A ruff release that adds rules to `E`/`B`/`SIM` turns the stop gate red on untouched code, and it presents as if your change broke something. | `/small-change` |
| Portability | `.vscode/settings.json` hardcodes `.venv\Scripts\python.exe`, the documented commands are PowerShell, and `settings.json` invokes hooks as bare `python`. `venv_tool` correctly probes both layouts, so the hooks themselves are fine — but where the interpreter is `python3` only, all four hooks fail silently, which is a poor failure mode for the machinery enforcing every rule. | `/feature` |
| `/bugfix` skill | Ten steps cover building a feature and the routing table has exactly two destinations. A reported bug is neither cosmetic nor a fresh concept, so it all lands in `/feature` today. | `/feature` |
| `/release` skill | Nothing manages `version = "0.1.0"`. No tag, no changelog. | `/feature` |
| `/audit` skill | The git history contains "Fix the inconsistencies a full audit of the repo turned up" — that audit was ad hoc, and the drifts in 3.4 are the same class of thing recurring. Make it repeatable. | `/feature` |
| `plan-critic` agent | Both existing subagents feed steps 4 to 6, after the code exists. Step 2 is where design errors are cheapest to catch and has no adversarial read at all. Fits the "different model from the one that wrote it" principle already used at step 6. | `/feature` |
