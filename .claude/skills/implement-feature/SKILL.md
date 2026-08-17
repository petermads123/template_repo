---
name: implement-feature
description: Implement a new feature, module, or public function end to end — design, branch, code to the conventions, edge-case tests, STRUCTURE.md update, and full verification. Use for anything that adds or removes a file, changes a public signature, changes behavior, or needs a new test.
argument-hint: [what to build]
effort: high
allowed-tools: Bash(ruff:*), Bash(mypy:*), Bash(pytest:*), Bash(git status:*), Bash(git diff:*), Bash(git branch:*)
---

# Implement a feature

The full path. Do not skip steps 6 or 7 — they are the ones that get dropped under time
pressure and they are the ones that cause drift.

## 1. Place the work

Read `STRUCTURE.md` first. Decide whether this extends an existing module or needs a new
one, and say which. A new module needs a reason that is not "it felt separate".

## 2. Design

State the approach and the alternative you rejected, in a couple of sentences.

For substantial work — several modules, a public API others will depend on, or a real
design fork — run the workflow instead of deciding alone:

```
Workflow with { scriptPath: ".claude/workflows/implement-feature.js", args: "<the task>" }
```

It fans out independent design approaches, scores them, and adversarially verifies the
result. It costs real tokens, so use it when the design is genuinely uncertain, not for a
third function on an existing module.

## 3. Branch

If already on a feature branch, stay. Otherwise branch from `main` using the naming
convention in `CLAUDE.md` — `feat/`, `fix/`, `refactor/`, `docs/`, `test/`, `chore/` plus a
kebab-case topic:

```bash
git checkout -b feat/<topic>
```

Never commit to `main`.

## 4. Implement

Follow `.claude/rules/python.md` — it is already in context. Every new module gets its
`main()` showcase and `__main__` guard. Do not hand-format; the hook handles it.

## 5. Tests

Delegate edge-case discovery rather than guessing:

```
Agent with subagent_type: "test-designer"
```

Give it the function signature, docstring and body. It returns ranked cases with concrete
inputs and expected results. **You** write the tests — the agent is read-only so the test
code stays in one voice.

## 6. Update STRUCTURE.md

In this change, not later. Add the module section, or amend the signature table, or both.
If a module moved or was deleted, fix its entry. The stop gate will block on a missing
module, but it cannot see a stale signature — that part is on you.

## 7. Verify

All four, all green:

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

Then confirm any new module actually runs standalone:

```powershell
python -m <package>.<module>
```

## 8. Hand off

Summarize what was built and what it changed in `STRUCTURE.md`, then point at `/create-pr`.
Do not push or open a PR from here.
