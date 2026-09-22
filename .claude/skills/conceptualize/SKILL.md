---
name: conceptualize
description: Step 1 of the feature pipeline. Discuss and agree what a feature is, what it connects to, and the observable criteria that define it as done; then name the branch, create its plan folder and first round file, and commit. Use at the start of a feature, or to revise a concept before planning.
argument-hint: [what to build]
model: opus
effort: xhigh
---

# Step 1 — Conceptualize

This step produces agreement, not code and not a design. It ends when the user says the
concept is right — and only then does it create anything on disk.

**Write no code. Choose no module names.** Those are step 2 and step 3. Deciding them here
quietly settles questions the concept has not asked yet. The one thing this step does
choose is the branch, because the scope it settles is what the branch is named for.

## 1. Ground yourself

Read `STRUCTURE.md` and skim whatever it names as relevant. A concept that ignores what
already exists produces a plan that duplicates it.

**If this is a later round** — step 8 or step 10 opened a second or third file in the
branch's folder — read every earlier round in that folder first, then fill in the **Builds
on** table: what each earlier round delivered, which recommendation or review comment this
round came from, and what is already on the branch that this round must not break. A later
round's concept is a change to something that already exists, so a concept written without
reading those is being written blind.

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

These criteria are also the **halting line** for the build: steps 3 to 7 run unattended,
and the one thing that stops them is a finding that would change this section. Write each
criterion so that a subagent can tell whether a surprise falls inside it or outside it.

## 4. Close the open questions

Fill the Open questions list as they come up, and empty it before the step ends. An
unanswered question here becomes a decision made by accident in step 3 — and in this
pipeline nobody is watching step 3.

## 5. Name the branch

Once the scope is settled, propose the branch, using the convention in `CLAUDE.md` —
`feat/`, `fix/`, `refactor/`, `docs/`, `test/` or `chore/` plus a kebab-case topic: what the
work *is*, not what it does to the repo. `feat/csv-export`, not `feat/add-csv-module`.
Include it in the confirmation message so the user reacts to it with the rest.

A later round keeps the branch its folder is named for. There is nothing to choose.

## Stop here, then create

Ask the user to confirm the concept, quoting the acceptance criteria and the branch name in
your message so they can react without opening a file. Nothing exists on disk yet.

**If they want changes**, make them and ask again. Stay on step 1. This is the cheapest
place in the pipeline to change your mind and the most expensive one to rush.

**Only once they confirm**, in this order:

1. Create the branch from `main`, unless this is a later round — then the branch already
   exists and is checked out.

   ```bash
   git fetch origin main
   git checkout -b <type>/<topic> origin/main
   ```

   Where the environment dictates the branch — a hosted session that may only push to a
   branch it was given — keep the conventional name for the **folder** and write the branch
   you actually push to in the Branch row. The folder is the feature's name; the row is
   where its commits go.

2. Create the folder and the round file (round 1 shown; a later round's file already
   exists, created by the step that opened it):

   ```bash
   mkdir -p development/<type>/<topic>
   cp development/TEMPLATE.md development/<type>/<topic>/01-<topic>.md
   ```

   Set the title, fill the Feature, Round, Branch and Started rows, write "Nothing — this
   is the first round." under **Builds on**, delete the quoted instructions, and write
   everything from the conversation into section 1.

3. Mark step 1 `done` in the Progress table and set the marker to
   `<!-- claude-plan step=2 status=active -->`.

4. Commit and push. Subject `Concept: <title>`, body naming the round file. This is the
   first commit on the branch, and from here every step leaves one, so a fresh session can
   always resume from the remote.

   ```bash
   git add development/ && git commit -m "..." && git push -u origin <branch>
   ```

5. **Invoke `/plan`** in the same turn. The user's confirmation is the gate between the two
   steps, and they have just passed it; the plan is what they see next, and it ends on its
   own confirmation before anything is built.
