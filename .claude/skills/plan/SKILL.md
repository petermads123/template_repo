---
name: plan
description: Step 2 of the feature pipeline. Turn an agreed concept into named modules, full public signatures, an ordered implementation guide and high-level test intents, all tied back to the acceptance criteria. Use after the concept is confirmed and before any code is written.
argument-hint: [slug, if more than one plan exists]
model: opus
effort: high
---

# Step 2 — Plan

Design it completely enough that step 3 is transcription rather than invention. Still no
code, still no branch.

## 1. Re-read the concept

Section 1 of the plan file, in full, including Out of scope. Everything below is planned
against the acceptance criteria — they are the contract, not your memory of the chat.

## 2. Survey what exists

Read `STRUCTURE.md`, then the modules it names as relevant. Report, concretely:

- which existing modules this touches and what they currently do,
- where the new code most naturally belongs and why,
- any existing function that already does part of this and should be reused rather than
  reimplemented.

Use the `Explore` subagent if the answer needs a broad sweep of the repo.

## 3. Weigh the approaches

Sketch two or three genuinely different approaches, not one plus two straw men. Useful
angles to push against each other:

- **Minimal** — the smallest change that fully satisfies the criteria; reuse hard, add as
  little public surface as possible.
- **Structural** — the cleanest long-term shape, willing to add or split a module where it
  pays off.
- **Defensive** — hardest to misuse; narrow types, explicit errors, awkward states made
  unrepresentable.

Recommend one in a short paragraph and say what the rejection cost. If two are genuinely
close and the difference matters to the user, put it to them with `AskUserQuestion` rather
than flipping a coin. If the design is obvious, say so in one line and move on — ceremony
over a third function on an existing module is waste.

## 4. Write the plan

Fill section 2 of the plan file:

- **Modules** — path, new or changed, purpose. A new module needs a reason better than "it
  felt separate".
- **Public API** — every public class and function, with its **full signature exactly as it
  will be written**, including annotations and defaults. Step 4 checks the code against
  this table character by character, so guesswork here becomes a failure there.
- **Implementation guide** — ordered, each entry small enough to finish and check.
- **Test intents** — what a test must *prove*, not how it is written. Step 5 turns each
  into concrete cases.
- **Risks** — what could make this harder than it looks, and the plan if it does.

Private helpers (leading `_`) do not belong in the Public API table, exactly as they do not
belong in `STRUCTURE.md`.

## 5. Check the coverage

Before stopping, verify explicitly and state the result:

- every acceptance criterion is covered by at least one Public API entry,
- every acceptance criterion is covered by at least one test intent,
- nothing in the Public API table exists without a criterion behind it.

A gap in either direction means the plan and the concept disagree. Fix the plan, or go back
to step 1 and say why — do not quietly widen the concept to fit the design.

## Stop here

1. Mark step 2 `done` and set the marker to `<!-- claude-plan step=3 status=active -->`.
2. Report: the chosen approach in a sentence, the modules to be touched, the public
   signatures, and the coverage result from step 5.
3. End the turn.

Do not create a branch and do not write code. The user opens step 3 with `/implement`.
