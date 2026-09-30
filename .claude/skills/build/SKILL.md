---
name: build
description: Steps 3 to 7 of the feature pipeline, run as one unattended block once the user has accepted the plan — implement, verify, test, concept-check and ship, each as a subagent on its pinned model, committing and pushing after every step. Halts only for something that would change the agreed concept, or a gate that fails twice for the same reason. Use after the plan is accepted, or to resume a halted build.
argument-hint: [slug, if more than one plan exists]
model: opus
effort: medium
---

# Steps 3 to 7 — Build

The user has agreed what to build (step 1) and how (step 2). Everything from here to a
pushed, verified, tested, concept-checked branch is transcription and checking, and none of
it needs a decision from them — so none of it waits for one. This skill runs the five steps
in order and stops only when the pipeline reaches step 8, or when something turns up that
the plan did not settle.

You are the **orchestrator**. You do not write code, run the gates or edit the plan's
sections yourself: each step runs in its own subagent, on the model its skill pins, and you
read the plan file between steps to decide what happens next. The reason is in `CLAUDE.md`:
a model override set by a skill lasts the turn, so five skills chained in one turn would all
run on whatever the first one set. A subagent per step is how each step gets its own model.

## 1. Find the step

```bash
git branch --show-current
```

Then read the active plan file — the one whose marker says `status=active` — and take
its `step`. It must be 3 to 7. If it is 1 or 2 the plan is not accepted yet; say so and
stop. If it is 8 or later the build is finished; say so and stop. If a `Halted` section
exists in the file, read it: the build is resuming, and the user's answer to it is in the
conversation or in the file.

Then look for an interrupted run:

```bash
git status --short
git log --oneline main..HEAD
```

A step was interrupted — by a restart or a usage limit, before its final commit — if the
tree has changes, or if the log, read from the top down to the first subject that does not
start `WIP step N:` (N being the marker's step), shows any such commits. Those are its
checkpoints, and after a fresh container they may be all that is left. Do not stash, reset
or commit anything yourself: the uncommitted changes and the checkpoints are that step's
partial work, and its brief hands them to it (item 6 below).

One change is not partial work: the user's answer to a halt. When the plan file has a
`Halted` section whose answer is not yet committed, record it as section 4 says and commit
and push it by explicit path, subject `Halt answered at step N: <short>`, before this check
counts anything.

The Branch row must match the checked-out branch. If it does not, stop and say so — the
branch was created at step 1 and nothing since should have moved.

## 2. Run the steps

For each step from the current one to 7, in order, spawn one subagent and wait for it.
Foreground, never background: the next step reads what this one wrote, so nothing useful
can overlap it.

| Step | Skill | Model | Reads | Writes |
|---|---|---|---|---|
| 3 | `/implement` | `sonnet` | sections 1 and 2 | the code, `STRUCTURE.md`, section 3; on a fix round the reproduction test first, run red |
| 4 | `/verify` | `sonnet` | section 2 | fixes, section 4 |
| 5 | `/test` | `sonnet` | section 2's test intents | `tests/`, fixes, section 5 |
| 6 | `/concept-check` | `sonnet` | section 1 **first**, then the code | section 6 |
| 7 | `/ship` | `sonnet` | everything | section 7 |

The model column is the skill's own frontmatter; pass it as the `model` argument to the
`Agent` tool. Effort cannot be passed to a subagent, so the `effort: max` those skills pin
is a statement of intent the subagent reads in its skill file rather than a setting.

### The readers you run for a step

A subagent cannot start another agent. So the extra readers three steps rely on are run by
you, just before you spawn the step, and their reports go into its brief. All of them are
read-only; run the two designers in parallel.

| Before step | Agent | Brief |
|---|---|---|
| 4 | `structure-auditor` | the plan file's path; reconcile `STRUCTURE.md` with the code as step 3 left it |
| 5 | `test-designer`, twice | `input-space` and `contract`, one each: the plan file's path, the public functions in section 2's Public API table (it reads their code itself), at most fifteen cases per function; on a fix round, the Defect block's Class and Expected rows, as `/test` describes |
| 6 | `structure-auditor` | as before step 4, against the code as step 5 left it |

A large Public API table may be split by module into several designer pairs.

Put each report into the step's brief verbatim, under a heading naming the agent and its
brief. If a report is too long to paste, write it to a file outside the repository and give
the path; never write it into the tree, where it would dirty it. Do not summarise or filter
a report: judging it is the step's job. If a reader fails or returns nothing, say so in the
brief; the step then does that check itself and says so in its trace.

### The subagent's brief

Every subagent gets the same shape of prompt:

1. The plan file's path, and the instruction to read it in full before anything else.
2. The instruction to read and follow `.claude/skills/<skill>/SKILL.md` as its procedure,
   and `.claude/rules/python.md` before touching any `.py` file. The rules load
   automatically in the main session; a subagent has to be told.
3. The halting rules below, verbatim, and that it must **not** proceed to the next step:
   it finishes its own step, commits, pushes, sets the marker, and reports.
4. Before steps 4, 5 and 6, the readers' reports, as above.
5. Work-in-progress commits. Commit and push at each natural checkpoint, then carry on. A
   checkpoint is a module written, a test file passing, a fix gone green. Stage by explicit
   path, with subject `WIP step N: <what>`. A restart then costs minutes rather than the
   step. The step's final commit and its marker change follow as usual. On a fix round,
   step 3's first checkpoint is the reproduction test with its red run pasted into section
   3, committed before any production code changes.
6. When the step resumes an interrupted run (section 1), this note, with the files, the
   commits, or both named:

   > An earlier run of this step was interrupted. The uncommitted changes in <files>, and
   > the commits <hashes>, are its partial work. Read them and continue from them. Do not
   > discard, reset or rewrite them before you have read them.

7. The report contract:

```
STATUS: done | halt
HALT_REASON: <one paragraph, only when halting>
MODEL: <the model it ran on, if it can tell>
TRACE:
<one or two lines per module, class, function and test group it produced or changed>
```

The trace is not a summary. It names every module, class and function the step touched,
each with a line or two saying what it does or what changed, and at step 5 every test group
with what it proves. The user is not watching the subagent work, so this is their window
into it — relay it to the chat verbatim, under a heading naming the step, the moment the
subagent returns. Do not condense it.

### Between steps

After each subagent returns:

- **`STATUS: done`** — confirm the marker advanced to the next step and the tree is clean
  (`git status --short` empty; the step committed and pushed). If either is false the step
  did not finish: run it once more with the discrepancy named, and with item 6's note if it
  left changes or `WIP step N:` commits behind. Halt if that also fails. Then relay the
  trace and start the next step.
- **`STATUS: halt`** — go to section 4.

A step that sends the work backwards is normal and stays inside the block: step 6 finding
the code wrong sends it to step 3, step 5 finding a bug fixes it in place. The subagent says
which in its report. Re-run from the step it named, and count it — the second time the same
step sends the work back for the same reason is a halt.

## 3. Halting rules

The block stops and hands the work to the user on exactly two things. Both are given to
every subagent, and the orchestrator applies them too.

1. **Anything that would amend section 1.** A deviation that invalidates an acceptance
   criterion, a test that reveals a case the concept never decided, a concept-check row that
   turns out to be wrong rather than unmet, a "better than the concept" finding. On a fix
   round, a reproduction that is already green before the fix, or a root cause found
   somewhere other than the Defect block's row. The user agreed to section 1; only they
   change it. Nothing in the block guesses an answer and buries it in code or an assertion.
2. **A gate failing twice for the same reason.** A subagent that hits a red gate fixes it
   and re-runs once. If the same failure comes back, it halts rather than trying a third
   time — the second failure means the fix was a guess, and a third attempt would be
   another one. "Same reason" is the same check on the same file with the same message
   class; a different failure is a new first failure.

Everything else is the block's to handle: a failing check, a bug the tests find, a signature
that needed changing, a missing `STRUCTURE.md` entry, `main` having moved.

## 4. On halt

1. **Commit and push what exists**, red or not, so a fresh session can resume from disk:
   subject `Halt at step N: <short reason>`, body naming the plan file. The stop gate is
   advisory through step 7 precisely so this turn can end on a red tree.
2. Write a **`## Halted`** section at the bottom of the plan file — the step, the reason
   verbatim from the subagent, and the question the user has to answer. Leave the marker
   on the step that halted, `status=active`. Commit and push that too.
3. Report to the user: the trace so far, the reason, and the question. Then end the turn.

When the user answers, `/build` resumes from the marker's step. If their answer changes
section 1, they are amending the concept: update section 1 (and section 2 where it follows),
record the change in the `Halted` section, delete nothing, commit and push that by explicit
path, subject `Halt answered at step N: <short>`, then resume. A halt answered by
"do it anyway" is also an answer; record that.

## 5. On reaching step 8

The marker reads `<!-- claude-plan step=8 status=active -->`, the tree is clean, and the
branch is pushed. Report once: every step's trace is already in the chat, so this is the
commit list from `git log main..HEAD --oneline`, the pass count from section 5, and the
criteria table from section 6.

Then invoke `/recommend` in this session, not as a subagent: it may start the
`defect-class` reader, ask the user and open `/create-pr`, none of which a subagent can do.
So it runs in this turn, on this turn's model rather than its own pin, and so does the
`/create-pr` it hands on to. It is the user's step, not the block's, so it is opened rather
than skipped. It asks the user only when it finds something critical. If it finds a bug in
this round's own code it sends the work back to step 3 and invokes `/build` again;
otherwise it records that there is nothing and hands on to `/create-pr`, which asks before
it publishes.

## What this skill never does

- Merge, open a pull request, or touch `main`.
- Write code or edit a plan section itself — that is a subagent's job, on its model.
- Continue past a halt, or attempt a third fix for the same failure.
- Condense a trace. The user asked for a window, not a summary.
