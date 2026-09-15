---
name: verify
description: Step 4 of the feature pipeline. The static half of verification — ruff, mypy, module showcases, and a literal check that the code matches the planned public signatures and that STRUCTURE.md is in sync. Use after implementing, before writing tests.
argument-hint: [slug, if more than one plan exists]
---

# Step 4 — Verify

Does the code that exists match the code that was planned, and is it well-formed? This step
is static: no new tests are written here, and `pytest` runs only to confirm nothing already
in the suite broke.

From this step on the stop gate blocks. A turn cannot end with ruff, mypy or pytest failing.

## 1. Run the tools

All of them, and report the actual output rather than a summary:

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

Any failure is fixed here and the whole set re-run from the top. Never add a bare `# noqa`
or an uncoded `# type: ignore` to get past one — `.claude/rules/python.md` gives the form a
justified suppression has to take, and anything else is hiding the problem rather than
solving it.

## 2. Check the plan was actually built

The part a linter cannot do. Take the Public API table from section 2 of the plan file and,
for each row, confirm the code defines that name with that exact signature — parameter
names, defaults, annotations, return type.

Report a table of the result. For each mismatch, say which it is:

- **Missing** — planned, not written. Go back and write it.
- **Deviation** — written differently on purpose. It should already be recorded in section
  3 and corrected in section 2. If it is not, that is a step 3 omission: record it now and
  say so.
- **Unplanned** — public surface that no plan entry and no acceptance criterion asked for.
  Either justify it in section 3 or remove it. Public API that nobody asked for is the
  cheapest thing to delete today and the most expensive thing to delete in a year.

## 3. Check STRUCTURE.md

Run the auditor rather than eyeballing it:

```
Agent with subagent_type: "structure-auditor"
```

It catches the signature drift the stop gate cannot see. Apply the edits it returns — it is
read-only by design.

## 4. Run every new module standalone

Each new module's `main()` showcase has to actually work:

```powershell
python -m <package>.<module>
```

Read the output, not just the exit code. A showcase that prints nothing a reader could
learn from is not a showcase; fix it here. Expect a `RuntimeWarning` when the module is
also re-exported from `__init__.py` — that is normal and is explained in the rules.

## 5. Record it

Fill section 4 of the plan file: the command output, the plan-completeness table, the
auditor's findings and what was done about them, the showcase output.

## Stop here

1. Mark step 4 `done` and set the marker to `<!-- claude-plan step=5 status=active -->`.
2. Report: every check and its result, and anything fixed along the way.
3. End the turn.

The user opens step 5 with `/test`.
