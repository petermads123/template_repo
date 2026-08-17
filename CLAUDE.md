# Working in this repo

@STRUCTURE.md

`STRUCTURE.md` above is the map of what lives where. Read it before searching the repo, and
update it in the same change whenever a module or public signature changes.

## What to invoke

| Situation | Use |
|---|---|
| Rename, docstring wording, plot styling, message text, formatting | `/small-change` |
| New module, new public function, behavior change, anything needing a design decision | `/implement-feature` |
| Ready to open a pull request | `/create-pr` |
| Question about the conventions themselves | `/conventions` |
| Need edge cases for a function | `test-designer` subagent |
| STRUCTURE.md looks out of sync with the code | `structure-auditor` subagent |
| Broad "where is X" search across the repo | built-in `Explore` subagent |

### Small or large?

It is **not** a small change if it does any of these:

- adds or removes a file
- changes a public signature
- changes behavior
- needs a new test

Any one of them routes to `/implement-feature`. Everything else is `/small-change`.

## Conventions

`.claude/rules/python.md` loads automatically whenever a `.py` file is read or edited, so
the conventions are already in context — you do not need to invoke anything to get them.
`/conventions` holds the long-form reference with worked examples.

## Branches

Never commit to `main`; it is protected on the remote. Branch names are
`type/kebab-case`:

| Prefix | Use for |
|---|---|
| `feat/` | new behavior |
| `fix/` | corrected behavior |
| `refactor/` | changed structure, identical behavior |
| `docs/` | prose only |
| `test/` | test-only additions |
| `chore/` | tooling, dependencies, config |

Examples: `feat/csv-export`, `fix/greet-unicode-crash`, `refactor/split-solver-module`,
`chore/bump-ruff`. Nothing validates this — it is a convention, so apply it when creating
branches.

## Commands

Run from the repo root with `.venv` active. All four must pass before a PR:

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

## Automation already in place

- **After every `Write`/`Edit` of a `.py` file**, `.claude/hooks/lint_py.py` runs
  `ruff format` and `ruff check --fix` on that file. Formatting is handled for you; only
  unfixable errors come back.
- **Before a turn ends**, `.claude/hooks/stop_gate.py` blocks if `.py` files changed and
  ruff, mypy or pytest fail, or if STRUCTURE.md does not mention a module that exists on
  disk. Create `.claude/.skip-gate` to bypass it deliberately.

Hooks are read at session start. If you change anything under `.claude/hooks/` or
`.claude/settings.json`, Claude Code must be restarted before it takes effect. Skills and
rules hot-reload without a restart.

## Growth

Keep this file a routing map. When guidance grows past routing, move it into a skill — a
skill's body loads only when used, while everything here is in context every session. Facts
and routing stay; procedures become skills.
