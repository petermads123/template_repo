---
name: concept-check
description: Step 6 of the feature pipeline. Audit the finished implementation against the concept agreed in step 1 — not against the plan — marking each acceptance criterion met or unmet with evidence. Runs inside /build as a subagent, after the tests pass; a different model from the one that planned the work.
argument-hint: [slug, if more than one plan exists]
model: sonnet
effort: max
---

# Step 6 — Concept check

Steps 4 and 5 asked whether the code matches the plan and works. This step asks a different
question, and it is the one the pipeline exists to protect:

> Is the thing that got built the thing that was agreed?

A plan can drift from its concept a little at each step and still pass every check along
the way. This is the only place that drift gets caught before it ships — and in this
pipeline nobody has looked at the code since the plan was accepted, so it is also the first
pair of eyes. Read as an auditor, not as the author.

This step runs unattended, as a subagent of `/build`. An unmet criterion sends the work
back inside the block. A criterion that turns out to be *wrong* is a halt: the rules are
in `/build` and in your brief.

## 1. Read the concept first

Section 1 of the plan file, on its own, before looking at any code. Do not read section 2
first — reading the design before the concept is how you end up checking the code against
itself. The acceptance criteria are the contract.

## 2. Audit each criterion

For every criterion, fill a row of the table in section 6:

| # | Criterion | Met | Evidence |
|---|---|---|---|

Evidence is specific and checkable: a test name, a `file.py:line`, or the actual output of
running something. "Implemented in the exporter" is not evidence. If the only evidence you
can give is that the code looks right, the criterion is **not** demonstrably met — say so.

Mark honestly. `partially` is a real answer and a useful one; a table of nine `yes` rows
produced without friction usually means the audit was performed on the plan rather than the
code.

## 3. Re-check the earlier rounds

Later rounds only. This round changed code that earlier rounds in the same folder depend
on, and they were audited before it existed.

Go back through every acceptance criterion from every earlier round and fill the **Earlier
rounds still hold** table in section 6. Their tests passing is necessary but not
sufficient: a criterion can stay green while the feature stops doing what the criterion
describes, because the tests were written against an implementation this round replaced.
Re-read the criterion and check it against the code as it stands now.

A criterion from round 1 that this round broke is a regression, not a trade-off. It goes
back to step 3 like any other unmet criterion — unless it should change, which is a halt.

## 4. Check the things criteria do not cover

Then go looking, adversarially, for the ways the user would be disappointed on opening this:

- **Out of scope** — did anything from section 1's exclusion list get built anyway?
- **Connections** — do the modules it was meant to connect to actually use it, and does the
  data flow the way the concept described?
- **Surface** — is there public API a reader would expect from the concept that does not
  exist, or API that exists that the concept never asked for?
- **Showcase** — run `python -m <package>.<module>`. Would someone who read only the
  concept recognise this output as the feature they agreed to? And does the showcase read
  as a worked example — named inputs, one call, a named result — so a reader learns how to
  use the feature rather than just that it runs?
- **Structure** — run the `structure-auditor` subagent once more. Steps 3 and 5 both edit
  signatures, and this is the last chance to catch the drift before step 7 closes the round.

## 5. Act on what you find

- **Everything met, no drift** — say so plainly and move on. Do not manufacture findings to
  look thorough.
- **Unmet criterion or real drift, code wrong** — do not ship it and do not note it as a
  follow-up. Set the marker back to step 3, say exactly what is unmet and why, and report
  `STATUS: done` with the step named: `/build` re-runs from there. If the same criterion
  comes back unmet a second time, that is the gate failing twice — halt instead.
- **The design cannot satisfy the criterion, or the criterion itself is wrong** — either
  one changes section 1 or 2 under the user. **Halt**, with the criterion and what you
  found.
- **Something genuinely better than the concept** — that is still drift, and still a halt.
  They agreed to the concept; they get to agree to the change.

Record the drift and its resolution at the bottom of section 6 either way.

## 6. Commit and push

The plan file, and anything the structure auditor had you fix — subject
`Concept check: <title>`, round file in the body. Clean tree.

## Stop here

1. Mark step 6 `done` and set the marker to `<!-- claude-plan step=7 status=active -->`.
   If you sent the work back to step 3, set the marker there instead and say so.
2. Report, in the `/build` contract: `STATUS`, and a `TRACE` with the criteria table, the
   earlier-rounds table where there is one, and every drift found and what was done.
3. End. `/build` opens the next step; do not.
