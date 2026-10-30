---
name: plan
description: Step 2 of the feature pipeline. Turn an agreed concept into named modules, full public signatures, an ordered implementation guide and high-level test intents, all tied back to the acceptance criteria, then have it criticised — handing straight on to the build when the critique is clean, and getting the user's acceptance when it is not. The last decision before the build runs unattended. Use after the concept is confirmed and before any code is written.
argument-hint: [slug, if more than one plan exists]
model: opus
effort: high
---

# Step 2 — Plan

Design it completely enough that step 3 is transcription rather than invention. Still no
code. The branch already exists — step 1 created it — so the tree is where the plan file
lives, and nothing else changes here.

This is the last thing the user reads before steps 3 to 7 run without them. Everything the
build will have to decide on its own is decided here or in section 1, and anything neither
settles becomes a halt. Plan accordingly.

## 1. Re-read the concept

Section 1 of the plan file, in full, including Out of scope. Everything below is planned
against the acceptance criteria — they are the contract, not your memory of the chat. On a
fix round, the Defect block too: the plan removes the cause named in its Root cause row,
not the site where the symptom shows, and Risks says what the build does if the cause turns
out to be elsewhere — halt.

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
- **Risks** — what could make this harder than it looks, and the plan if it does. In this
  pipeline a risk that materialises is handled by a subagent with no one to ask, so say
  here what it should do — or that it should halt.

Private helpers (leading `_`) do not belong in the Public API table, exactly as they do not
belong in `STRUCTURE.md`.

## 5. Check the coverage

Before going further, verify explicitly and state the result:

- every acceptance criterion is covered by at least one Public API entry,
- every acceptance criterion is covered by at least one test intent,
- nothing in the Public API table exists without a criterion behind it.

A gap in either direction means the plan and the concept disagree. Fix the plan, or go back
to step 1 and say why — do not quietly widen the concept to fit the design.

## 6. Have it criticised

Once the plan is written and section 5 passes, hand it to a second reader before the user
sees it:

```
Agent with subagent_type: "plan-critic"
```

Give it the plan file's path. It reads section 1 before section 2, checks the plan against
the concept and against the repo, and returns ranked findings — coverage gaps, awkward
signatures, decisions the build will halt on, code the plan reimplements — with a verdict.

Then, for every finding, either **apply** it to section 2 or **rebut** it in one sentence.
Record both in a short **Critique** list at the end of section 2: the finding, and what was
done. A rebuttal is a legitimate outcome; a finding silently dropped is not, because the
plan is about to be accepted — by the user, or by a clean critique — on the strength of it
having been read twice. A rebuttal also means the user sees the plan before the build runs
(section 7): it is the planner overruling the only other reader the plan gets.

If the critic's verdict is **back to step 1**, that is a real answer: say so, name the
criterion, and stay on step 2 until the user has decided. Do not present a plan for
acceptance over a concept the critic has shown to be unsettled.

Re-run section 5 if applying a finding changed the Public API or the test intents.

## 7. Decide whether the user is needed

The critique decides whether this step waits for the user. The plan is **clean**, and is
accepted on the strength of having been read twice, only when all of these hold:

- section 5 passed with no gap,
- the critic's verdict is **accept as is**, or **accept with the changes above** with every
  finding applied in full — none rebutted, none applied only in part,
- no finding's suggested change is a question for the user,
- no fork from section 3 is still waiting on the user, and nothing in Risks is a decision
  the plan leaves to them.

Anything short of that — a rebuttal, a question, a **back to step 1** verdict, an open
fork — and the user decides, exactly as before. When it is unclear whether a finding was
fully applied, it was not: wait. The rule is literal on purpose; it is not a guess at
whether the user would probably agree.

## Stop here, or hand on to the build

The full plan is in the file. The chat gets the high-level version either way: the chosen
approach in a sentence, the modules to be touched, the public signatures, the test intents
in a line each, the risks, the coverage result from step 5, and the critic's findings with
what was done about each.

**When the plan is clean** (section 7), it is accepted now:

1. End section 2's Critique list with `Accepted: clean critique, <date>`, mark step 2
   `done`, and set the marker to `<!-- claude-plan step=3 status=active -->`.
2. Commit and push: subject `Plan: <title>`, body naming the round file and saying it was
   accepted on a clean critique.
3. Report the plan as above, and say in one line that the build starts now without asking
   because the critic left nothing open, and that the user can interrupt to stop it.
4. **Invoke `/build`** in the same turn.

**Otherwise** the plan waits for the user:

1. Commit and push the plan file: subject `Plan: <title>`, body naming the round file.
   The marker stays on step 2 — the plan is written, not accepted.
2. Report the plan as above, name what kept it from being clean — the rebuttal, the
   question, the fork — and ask the user to accept it. Say plainly what acceptance means:
   steps 3 to 7 run without further questions, and halt only for something that would
   change the concept or a gate that fails twice the same way.
3. End the turn.

**When the user accepts** — in their next message, or later — end the Critique list with
`Accepted: by the user, <date>`, mark step 2 `done`, set the marker to
`<!-- claude-plan step=3 status=active -->`, commit and push that, and **invoke
`/build`**. Their acceptance is the gate, and it opens the build.

**If they want changes**, make them, re-run section 5, commit, and ask again. Stay on step
2. A plan the user is revising waits for their acceptance, whatever the critic said. A plan
revised three times is cheaper than a build halted once.
