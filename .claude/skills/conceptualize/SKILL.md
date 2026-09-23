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

**On a fix round the code is the subject, and reading it is required rather than
forbidden.** A fix round is one whose section 1 carries a filled **Defect** block, and
nothing else marks it. `/fix` has already reproduced the defect, found its cause, sized the
class of inputs it breaks and had a `diagnosis-critic` read the diagnosis; that diagnosis
arrives with the invocation and is the Defect block's starting content — it reaches disk
with the rest of section 1 when the user confirms, like everything else this step
produces. A concept for a fix names the line it fixes. Writing code still waits for step 3.
On a feature round, delete the Defect block from the round file.

**A round opened for a defect that has no diagnosis yet** — its Builds on section says
"Opened on a bug report — run `/fix` first", the Defect block is empty, and no diagnosis
arrived with this invocation — is not ready for this step. Invoke `/fix`; it diagnoses
into the file and hands back here with the diagnosis in the message. This is what a
session resumed after a context reset needs, because the session brief sends step 1 here
and nothing on disk would otherwise say a diagnosis was owed.

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

**On a fix round** the conversation starts from the Defect block rather than from a first
reading, and Why is already answered there — do not restate it. Cover instead:

- **Scope.** The one fork every fix has: *this instance* or *the class*. The Defect block
  lists what else the same cause breaks; ask, with `AskUserQuestion`, whether this round
  takes all of it or only the reported input, and record the answer and its reason in the
  Scope row. Whatever the class holds that is not taken goes under Explicitly out of scope
  **by name**, so step 8 finds it rather than the next bug report.
- **Blast radius decisions.** A caller, a test or a document that depends on the current
  wrong behaviour is a decision to make here — change it, or keep it and say why — not a
  surprise for step 3, which cannot ask.
- **What it is.** One paragraph on the fix, naming the cause it removes. "Rewrite the
  window loop" is a plan; "every complete window gets a mean, including the last" is a
  concept.
- **Verdict.** If the diagnosis says *works as designed* or *never decided*, this is not a
  fix round at all — say so and switch to a feature concept, deleting the Defect block.

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

On a fix round two criteria are always present. The **first** is the reproduction passing,
phrased from the Defect block:

> **A1** — Given `[1, 2, 3]` and `"daily"`, `rolling_mean` returns `[1.0, 2.0, 3.0]`, where
> today it drops the last window and returns `[1.0, 2.0]`.

The **last** is that nothing else changed, phrased so step 6 can evidence it with more than
a green suite — name what must still hold and how it can be shown:

> **A5** — Still returns `[]` for fewer samples than the window and still raises
> `ValueError` for an unknown resolution; shown by the existing suite and by a differential
> of generated inputs against the module on `main`.

If the scope is *the class*, each input in the class gets its own criterion between those
two. Step 3 writes A1 as a test and runs it red before touching the code; a reproduction
that is already green halts the build, because it means this section is wrong.

These criteria are also the **halting line** for the build: steps 3 to 7 run unattended,
and the one thing that stops them is a finding that would change this section. Write each
criterion so that a subagent can tell whether a surprise falls inside it or outside it. On
a fix round the Root cause row is on the same line: a build that finds the cause elsewhere
halts rather than fixing what it found.

## 4. Close the open questions

Fill the Open questions list as they come up, and empty it before the step ends. An
unanswered question here becomes a decision made by accident in step 3 — and in this
pipeline nobody is watching step 3.

## 5. Name the branch

Once the scope is settled, propose the branch, using the convention in `CLAUDE.md` —
`feat/`, `fix/`, `refactor/`, `docs/`, `test/` or `chore/` plus a kebab-case topic: what the
work *is*, not what it does to the repo. `feat/csv-export`, not `feat/add-csv-module`.
Include it in the confirmation message so the user reacts to it with the rest.

A round 1 opened by `/fix` takes the `fix/` prefix, and the topic names the defect rather
than the ticket: `fix/rolling-mean-last-window`, not `fix/bug-12`.

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
   everything from the conversation into section 1 — the Defect block from the diagnosis
   and the conversation on a fix round, or deleted whole on a feature round. On a round
   that was opened on a bug report, delete the "Opened on a bug report — run `/fix`
   first" line from **Builds on** now that the block is filled.

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
