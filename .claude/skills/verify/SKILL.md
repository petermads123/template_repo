---
name: verify
description: Step 4 of the feature pipeline. The static half of verification — ruff, mypy, module showcases, and a literal check that the code matches the planned public signatures and that STRUCTURE.md is in sync. Runs inside /build as a subagent, after implementing and before writing tests.
argument-hint: [slug, if more than one plan exists]
model: sonnet
effort: max
---

# Step 4 — Verify

Does the code that exists match the code that was planned, and is it well-formed? This step
is static: no new tests are written here, and `pytest` runs only to confirm nothing already
in the suite broke.

This step runs unattended, as a subagent of `/build`. A failure here is yours to fix — once.
The same failure back after the fix is a halt; the rules are in `/build` and in your brief.

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

- **Missing** — planned, not written. Write it.
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

Read the output, not just the exit code, and check the showcase is in the form
`.claude/rules/python.md` requires: every argument bound to a named variable, the call on
its own line, the result named, then printed, with the accepted values listed in a same-line
comment wherever an argument takes one of a fixed set. A showcase that prints nothing a
reader could learn from is not a showcase, and one with its arguments inline is not in the
required form — the whole point is that someone can change an input and re-run without
untangling the call. Fix either here. Expect a `RuntimeWarning` when the module is also
re-exported from `__init__.py` — that is normal and is explained in the rules.

## 5. Record, commit, push

Fill section 4 of the plan file: the command output, the plan-completeness table, the
auditor's findings and what was done about them, the showcase output.

Commit everything this step changed — fixes, `STRUCTURE.md`, the plan file — with subject
`Verify: <title>` and the round file in the body, then push. Clean tree at the end.

## Stop here

1. Mark step 4 `done` and set the marker to `<!-- claude-plan step=5 status=active -->`.
   That edit goes in the commit above.
2. Report, in the `/build` contract: `STATUS`, and a `TRACE` with every check and its
   result, every mismatch from section 2 and how it was resolved, and a line per function
   whose code was changed here to get green.
3. End. `/build` opens step 5; do not.
