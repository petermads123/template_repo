---
name: small-change
description: Make a small, low-risk edit — renaming a local variable, rewording a docstring or message, adjusting plot styling or formatting. Use for cosmetic changes that do not alter behavior, add or remove files, change a public signature, or need a new test. Anything that does route to implement-feature instead.
argument-hint: [what to change]
allowed-tools: Bash(ruff:*), Bash(mypy:*), Bash(pytest:*)
---

# Small change

A tight loop for cosmetic work. No branches, no PRs, no ceremony.

## 1. Check it is actually small

It is **not** small if it does any of these:

- adds or removes a file
- changes a public signature
- changes behavior
- needs a new test

If any apply, say so and switch to `/implement-feature`. Do not proceed here — the whole
point of the split is that this path skips design and STRUCTURE.md work that larger changes
need.

Borderline cases worth naming out loud: renaming a *public* name is not small (it changes a
signature and STRUCTURE.md). Renaming a local variable is. Changing a docstring's wording is
small; changing what it documents means the behavior changed.

## 2. Make the edit

Go straight to it. The `PostToolUse` hook runs `ruff format` and `ruff check --fix` on the
file afterwards, so do not hand-format.

## 3. Verify narrowly

```powershell
ruff check .
mypy
pytest tests/test_<module>.py
```

Only the affected test file — a full suite run is `/create-pr`'s job. If the change touched
more than one module, run each affected test file.

## 4. Report

State what changed and confirm STRUCTURE.md needs no update, with the reason — no module
was added, removed or renamed and no public signature changed. If you cannot say that
truthfully, this was not a small change and step 1 was wrong.
