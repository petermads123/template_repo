---
name: fix
description: Start the pipeline from a defect — wrong output, a crash, a guard that lets something through. Diagnoses before anything is agreed: reproduces the symptom, finds the root cause, sizes the class of inputs it breaks, has a second reader try to falsify the cause, and decides whether it is a defect at all; then hands the diagnosis to /conceptualize as a fix round. Use for any reported bug, whether the user names the skill or describes the symptom in prose.
argument-hint: [the symptom]
model: opus
effort: xhigh
---

# Fix

A defect goes through the same ten steps as a feature, on the same plan file, watched by
the same hooks. What differs is where it starts. A feature starts from a wish, and step 1
can agree what it is before anyone reads a line of code. A defect starts from an
observation — something that exists behaves wrongly — and nothing can be agreed until it is
known *why*. Agreeing a fix before the cause is found is how the symptom gets fixed and the
bug stays.

So this skill is `/feature` with a diagnosis in front of it. It reproduces the symptom,
finds the cause, sizes what else the cause breaks, has the diagnosis read a second time,
and only then opens step 1 — which on a fix round has a **Defect** block to fill and a scope
question to ask. It does not fix anything. The fix is the build's, once the concept and the
plan are agreed like any other.

A **fix round** is one whose section 1 carries a filled Defect block, and nothing else
marks it: a round this skill opens as round 1 takes the `fix/` prefix, a later round opened
on a bug report gets the block whatever its folder is called, and a follow-up round that is
not itself a defect has no block even in a `fix/` folder. Steps 1, 2, 3, 5, 6, 8 and 9 behave
differently on one — `CLAUDE.md` has the table — and each reads that from the plan file:
no hook and no marker changes.

## 1. Look before starting

Same as `/feature`:

```bash
ls development/*/*/
```

**If a plan is `active` at step 1 whose Builds on says "Opened on a bug report — run
`/fix` first"** and whose Defect block is empty, it is a round that step 8 or step 10
opened for this defect — possibly in an earlier session. Diagnose into it: skip nothing
below, and hand off to `/conceptualize` as usual, which will find the file already there.

**If any other plan is `active`**, report it and ask whether to resume or park it, as
`/feature` does. A bug in the code that plan is building belongs to its build — step 5
fixes what its tests find — not to a second pipeline.

**If no plan is active but the current branch has an open pull request**, the report may
be about what that branch shipped. Ask. If it is, open the round the way `/watch-pr`
section 4 does — a new numbered file in that branch's folder, marked as opened on a bug
report — and diagnose into it, rather than branching a fresh `fix/` round from `main`.

**If the request is not a defect** — the user wants something that does not exist, or wants
existing behaviour changed rather than corrected — say so and switch to `/feature`. The
verdict in section 2 catches the cases that only look like bugs.

## 2. Diagnose

Read code freely; this is the one place before step 3 where the code is the subject. Write
nothing into the tree: reproductions run from a scratch script or a one-liner, and the
plan file either does not exist yet or is waiting for step 1 to fill it. Produce every item
below, in this order, and say plainly which you could not.

### Reproduce

Run it. Quote the exact command or call, its actual output and the expected output. A
description of the symptom is what the user gave you; a reproduction is what turns it into
a fact:

```
>>> rolling_mean([1, 2, 3], "daily")
[1.0, 2.0]          # actual: the last window is missing
[1.0, 2.0, 3.0]     # expected
```

**If you cannot reproduce it, stop here.** Say what you tried and ask for the exact input,
the environment, or the output they saw. A diagnosis of a symptom you have not seen is a
guess, and everything downstream would be built on it.

### Root cause

The line, as `file.py:NN`, and the decision on it that is wrong. Keep asking why until the
answer is a line rather than a module: "the statistics module is flaky" is a description;
"`rolling_mean` builds its windows with `range(len(values) - window)`, which stops one
window early, so the last complete window never gets a mean" is a cause. Distinguish the
**site** — where the wrong value is noticed — from the **cause** — where it is produced. A
fix at the site is the one that comes back.

### Since when

```bash
git log -S "<the offending expression>" --oneline -- <file>
git blame -L <NN>,<NN> <file>
```

The commit that introduced it, or "older than the history here". Sometimes the fix is a
revert; sometimes the line is older than every test, which says something about the tests.

### The class

Two lists. **Other inputs the same cause breaks**: enumerate them and run the ones that
matter, because they are the raw material of the acceptance criteria and the substance of
the scope question. **The same shape elsewhere**: grep for the pattern — a second
comparison that fails the same way, a second parser with the same blind spot. What is found
here is either in this round's scope or a recommendation at step 8, and step 1 decides
which.

### Blast radius

Who calls the cause, which tests assert the current behaviour and will move when it
changes, and whether anything depends on the bug. A caller that relies on the wrong answer
is a finding, not an obstacle — it goes into the concept as a decision.

### Verdict

One of:

| Verdict | Then |
|---|---|
| **Defect** | The code does not do what its docstring, its tests or its concept say. Continue to section 3. |
| **Works as designed** | It does what was agreed and the user wants something else. Switch to `/feature`. |
| **Never decided** | No docstring, test or concept says what should happen here. Switch to `/feature`; step 1 decides it. |
| **Prose only** | The code is right and the docstring or `STRUCTURE.md` is wrong. `/small-change`. |
| **Already fixed** | `main` has moved past it. Say so and stop. |

Say the verdict in one line with the evidence that decided it. The three routings are the
point of diagnosing first: the pipeline should not be asked to fix what is not broken.

**When a round was already opened for this defect** by step 8 or step 10, a verdict other
than Defect has to deal with that file rather than leave it active and empty:

- *Works as designed* and *Never decided* — the round is real, just not a fix. Hand to
  `/conceptualize` as a feature round in the same file: it deletes the Defect block and
  has the concept conversation. Say so.
- *Prose only* and *Already fixed* — stand the round down. Delete the file, record the
  outcome where the round came from (the decision column of the previous round's section
  8, or a reply on the review thread), and if the previous round's marker was stood down
  to open this one, set it back to `<!-- claude-plan step=9 status=active -->` so the
  pipeline resumes at the pull request. Commit and push. A live marker left on an empty
  round would reach `main` with the branch.

## 3. Have it criticised

```
Agent with subagent_type: "diagnosis-critic"
```

Give it the reproduction, the root cause, the class and the blast radius as you have them,
and the files they name. It tries to falsify the cause: whether it explains all of the
observed behaviour, whether there is a second explanation, whether the cause is really a
site, and whether the class is complete. It returns ranked findings and a verdict.

Apply or rebut each finding in one sentence, on the record — the list goes into the Defect
block's **Critique** line with the diagnosis. A rebuttal is a legitimate outcome; a finding
silently dropped is not. If its verdict is **not reproduced** or **different cause**, go
back to section 2 before going on; if it is **not a defect**, re-decide the verdict in
section 2 against what it found, and route accordingly.

## 4. Hand off to step 1

Invoke `/conceptualize` with the diagnosis — reproduction, cause, since when, class, blast
radius, verdict and the critique — in the message. It fills the Defect block of section 1
from it, puts the scope question to the user, and writes the acceptance criteria, which on
a fix round always include the reproduction passing and nothing else changing.

Do not write the concept here and ask for a yes. The scope fork — this instance or the
class — is the user's, and it is the conversation step 1 exists to have.

## What this skill never does

- Fix the bug, in the tree or as a suggested patch, before the concept and the plan are
  agreed.
- Write the reproduction as a test. Step 3 does that first thing on a fix round, and runs
  it red before fixing.
- Diagnose from a description without reproducing it.
- Open a second pipeline beside an active one.
