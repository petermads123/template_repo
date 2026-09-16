---
name: conceptualize
description: Step 1 of the feature pipeline. Discuss and agree what a feature is, what it connects to, and the observable criteria that define it as done, writing the result into the plan file. Use at the start of a feature, or to revise a concept before planning.
argument-hint: [what to build]
model: opus
effort: xhigh
---

# Step 1 — Conceptualize

This step produces agreement, not code and not a design. It ends when the user says the
concept is right.

**Write no code. Create no branch. Choose no module names.** Those are step 2 and step 3.
Deciding them here quietly settles questions the concept has not asked yet.

## 1. Ground yourself

Read `STRUCTURE.md` and skim whatever it names as relevant. A concept that ignores what
already exists produces a plan that duplicates it.

**If this is a later round** — a second or third file in the feature's folder — read every
earlier round in that folder first, then fill in the **Builds on** table: what each earlier
round delivered, which recommendation this round came from, and what is already on the
branch that this round must not break. A later round's concept is a change to something
that already exists, so a concept written without reading those is being written blind.

## 2. Have the conversation

Propose a first reading of what the user asked for — your understanding, not a restatement
of their words — and then work through the gaps with them. Cover:

- **What it is.** One paragraph a reader could act on.
- **Why.** The problem it solves. If this is thin, say so now rather than after step 7.
- **Inputs and outputs.** Concrete types and shapes, in prose. What arrives, what leaves,
  what the caller is expected to already have.
- **Connections.** Which existing modules it calls, which will call it, which data it
  shares. Name them from `STRUCTURE.md`.
- **Out of scope.** The neighbouring things it deliberately does not do. This section
  prevents more rework than any other.

Ask about genuine forks rather than picking for the user — use `AskUserQuestion` when two
readings would lead to materially different work. Do not ask about things a careful
colleague would simply decide; say what you assumed instead.

Push back once where it is warranted: an input shape that will be awkward to use, a
connection that couples two things that were separate, scope that is really two features.
Say it in a sentence or two, then follow the user's call.

## 3. Write the acceptance criteria

The most important output of this step. Numbered, observable from outside the code, and
phrased so step 6 can mark each one met or not met:

> **A1** — Given a list of records and a path, the exporter writes a UTF-8 CSV whose
> header row matches the record field names in declaration order.

Not observable, therefore not a criterion:

> **A1** — The exporter is clean and easy to extend.

Aim for three to eight. If there are twenty, the feature is several features and should be
split. If there is one, the concept is probably too vague to plan.

In a later round, these cover only what *this* round adds. The earlier rounds' criteria are
not restated here — they stay where they were written and are re-checked in step 6.

## 4. Close the open questions

Fill the Open questions list as they come up, and empty it before the step ends. An
unanswered question here becomes a decision made by accident in step 3.

## Stop here

Write everything into section 1 of `docs/plans/<slug>.md`. Then:

1. Ask the user to confirm the concept, quoting the acceptance criteria in your message so
   they can react without opening the file.
2. **If they want changes**, make them and ask again. Stay on step 1. This is the cheapest
   place in the pipeline to change your mind and the most expensive one to rush.
3. **Only once they confirm**, mark step 1 `done` in the Progress table and set the marker
   to `<!-- claude-plan step=2 status=active -->`.
4. End the turn.

Do not begin step 2. The user opens it with `/plan`.
