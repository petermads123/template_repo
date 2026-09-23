---
name: small-change
description: Make a small, low-risk edit — renaming a local variable, rewording a docstring or message, adjusting plot styling or formatting. Use for cosmetic changes that do not alter behavior, add or remove files, change a public signature, or need a new test. Applies whether the user names the skill or just describes such a change in prose. Anything that does any of those routes to the feature pipeline instead.
argument-hint: [what to change]
model: opus
effort: high
---

# Small change

The escape hatch from the ten-step pipeline. A tight loop for cosmetic work: no plan file,
no branch ceremony, no pull request.

## 1. Check it is actually small

It is **not** small if it does any of these:

- adds or removes a file
- changes a public signature
- changes behavior
- needs a new test

If any apply, say so and switch to `/feature`. Do not proceed here — the whole point of the
split is that this path skips the concept, plan and verification work that a real change
needs.

Borderline cases worth naming out loud: renaming a *public* name is not small, because it
changes a signature and `STRUCTURE.md`. Renaming a local variable is. Rewording a docstring
is small; changing what it documents means the behavior changed and it is not.

A defect is never small. Fixing a bug changes behaviour by definition, so it routes to
`/fix`, which diagnoses it before the pipeline runs. The one exception is the case `/fix`
itself sends here: the code is right and only the prose describing it is wrong.

This skill runs on `opus` at `high`, like the pipeline's own judgment steps. That is
deliberate: step 1 above is the single highest-stakes call in the whole setup, because it
is the one decision made with none of the pipeline's safety nets behind it. Everything
downstream of a wrong "yes, that's small" is skipped rather than caught.

## 2. Know that the gate is strict here

With no active plan file, `.claude/hooks/stop_gate.py` holds its strict line: any turn that
touched Python must leave ruff, mypy, pytest and `STRUCTURE.md` in order before it can end.
That is deliberate. The pipeline earns its leniency through step 7 by having the build's
own gates ahead of it; this path has nothing ahead of it, so it pays in full and
immediately.

## 3. Make the edit

Go straight to it. `.claude/hooks/lint_py.py` runs `ruff format` and `ruff check --fix` on
the file afterwards, so do not hand-format.

## 4. Verify narrowly

```powershell
ruff check .
mypy
pytest tests/test_<module>.py
```

Only the affected test file. If the change touched more than one module, run each. The stop
gate runs the full suite when the turn ends regardless, so a green narrow run is a fast
signal rather than the final word.

## 5. Report

State what changed, and confirm `STRUCTURE.md` needs no update **with the reason**: no
module was added, removed or renamed, and no public signature changed. If you cannot say
that truthfully, this was not a small change and step 1 was wrong — say so and move to
`/feature`.

Committing is the user's call. Offer it; do not do it unasked.
