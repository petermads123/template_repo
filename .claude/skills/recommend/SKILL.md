---
name: recommend
description: Step 8 of the feature pipeline. Check whether the finished round leaves anything critical undone — usually nothing — and decide any such item with the user. Lesser ideas become one-line notes in DEVELOPMENT.md, which this step also cleans. With nothing critical it hands straight on to /create-pr. Opened by /build when the round is complete.
argument-hint: [slug, if more than one plan exists]
model: opus
effort: high
---

# Step 8 — Recommend

The round is on its branch and provably does what was agreed. This step asks one narrow
question: **is anything critical left undone?** Usually the answer is no, and that is the
answer this step expects.

**You do not have to come up with any recommendations.** None is the normal outcome, not a
sign the step was skimped. Every recommendation costs the user time to read and decide, and
an invented one costs that time for nothing. Do not brainstorm to fill section 8, and do not
go looking for ideas to note down either.

## 1. What counts

A recommendation qualifies only if both of these hold:

- **Critical.** Leaving it undone makes what this branch ships wrong, unsafe or unfit for
  the purpose section 1 states. Or it is a live defect outside what section 1 promised
  that gives silently wrong results, breaks something that already worked, or weakens a
  safety rule `CLAUDE.md` sets. "Nicer", "cleaner", "more general", "faster" and "the
  obvious next feature" do not qualify, however good the idea.
- **Of this work.** It concerns what this branch built or what this session ran into. The
  repo at large and a future feature's wish list are out.

When it is close, it is not critical: note it (section 4) and move on.

## 2. Look, briefly

Read what the round itself recorded. No panel of readers:

- the `Halted` section and section 3's deviations, which show where the plan was thinner
  than the code needed;
- section 5's deliberately skipped cases and section 6's drift notes;
- on a fix round, every member of the Defect block's Class row that **Explicitly out of
  scope** names.

On a fix round, and only then, also run one read-only reader:

```
Agent with subagent_type: "brainstormer"   lens: defect-class
```

Give it the plan file's path and its lens by name, and say the brief comes from step 8, so
it marks each item critical or not by §1's bar, or says in one line that it found nothing.
It asks three things:

- where else the root cause's shape occurs;
- which out-of-scope class member is now the nearest bug;
- what should have caught this before it shipped.

Hold its answers to the same bar as your own. The same cause live elsewhere and giving wrong
results qualifies. The rest is a note at most. Its **Bugs** heading is not a note: those go
back to the build (§3).

The `user`, `maintainer` and `integrator` lenses are not run here. They exist for when the
user asks what to build next.

## 3. What does not belong here

**A bug in what this round built is not a recommendation.** Anything broken in the code
this round's section 1 promised — found by you or under the `defect-class` reader's
**Bugs** heading — goes back through `/build` from step 3 and gets fixed before the pull
request: write it at the bottom of section 6 with its reproduction, as step 6 does for an
unmet criterion, set the marker to `<!-- claude-plan step=3 status=active -->`, commit and
push, and invoke `/build`. Step 8 runs again when the build reaches it. If the same bug is
back unfixed at that step 8, do not send it again: write a `Halted` section with the
question and end the turn, as `/build` §4 does — the fix was a guess. Do not let such a
defect leave this step wearing a "future improvement" label.

A critical defect *outside* what this round promised is different. It might be one section
1 put out of scope by name, one the `defect-class` lens found elsewhere, or one in code this
round never touched. Fixing it in the build would be drift, so it **is** a recommendation,
and a round opened on it goes through `/fix`, below.

Anything agreed in section 1 and not built is not a recommendation either. It is an unmet
acceptance criterion, which step 6 should have caught; send it back the same way.

## 4. Record

### Section 8

With nothing critical, replace section 8's table with the single line `None.` That is a
complete section 8.

Otherwise fill the table, most critical first:

| # | Recommendation | Why it is critical | Effort | Decision |
|---|---|---|---|---|

For effort, `small` is an hour, `medium` a session and `large` its own pipeline. State it
even when uncertain; "unknown" is an honest answer.

### Notes in `DEVELOPMENT.md`

Some ideas from section 2's reading fall short of the bar but would be a pity to lose:

- a workaround the build left in place;
- an edge case a later feature will meet;
- a debt the round exposed.

Each becomes a one-line entry in `DEVELOPMENT.md`, under a heading naming the branch and the
round, with the date. No decision is asked for; the user reads them in the file. Note only
what the round already turned up. Zero notes is fine, and an idea not worth a line is
dropped.

### Clean `DEVELOPMENT.md`

Every step 8, whatever else happened:

- remove the entries this branch resolved;
- merge duplicates and update anything stale, so only open items remain.

Before deleting or renaming an entry, find what points at it. Code comments and
`STRUCTURE.md` usually point at the file as a whole ("see `DEVELOPMENT.md`") and sometimes
at an entry's heading, so search for both:

```bash
git grep -n -F -e '<heading text>' -e 'DEVELOPMENT.md' -- . ':(exclude)DEVELOPMENT.md' ':(exclude)development' ':(exclude).claude' ':(exclude)CLAUDE.md'
```

Single quotes keep a heading's backticks literal in bash and PowerShell alike; a heading
with a single quote in it needs `'\''` in bash or `''` in PowerShell. Exit status 1 means
no match, not an error.

Read each hit's sentence. Where it relies on the entry you are removing, update or remove it
in the same commit, so nothing is left pointing at an entry that no longer exists. Plan files
under `development/` are a historical record; leave them as written.

## 5. Hand on, or decide

### Nothing critical

Only when §3 sent nothing back to the build. Then close the step:

1. Mark step 8 `done` and set the marker to `<!-- claude-plan step=9 status=active -->`.
2. Commit and push the plan file with `DEVELOPMENT.md` and every file whose pointer the
   cleaning updated, subject `Recommend: <title>`.
3. Report in two lines at most: no critical follow-up, and the notes added to
   `DEVELOPMENT.md` (how many, and their gist), or none.

Then invoke `/create-pr` in the same turn. It re-verifies the branch and asks the user
before it publishes, so the user still decides before anything leaves the branch. Step 8
adds no second question.

### Something critical

Commit and push the list first, subject `Recommend: <title>`, so it is on disk before the
conversation. Then present it and ask for a decision on each. There are three outcomes:

- **`deferred`**: worth doing, not now. Record it, and add a line to `DEVELOPMENT.md`
  pointing at its row.
- **`rejected`**: record the reason. Next time this comes up, the reasoning is already
  there.
- **`next round`**: take it through the pipeline again, as a new round on this branch.

### Opening the next round

A round is a new file in this branch's folder, not an edit to this one. The work already
on the branch stays exactly as it was written and audited.

```bash
cp development/TEMPLATE.md development/<branch>/0<N>-<round-slug>.md
```

Then, in order:

1. In **this** file, mark step 8 `done` and set its marker to
   `<!-- claude-plan step=8 status=done -->`. Exactly one file in the repo is `active`, so
   this one has to stand down before the new one starts.
2. In the **new** file, set the title, the Feature and Round rows, the same branch, and the
   marker `<!-- claude-plan step=1 status=active -->`.
3. Fill its **Builds on** section: what each earlier round delivered, the recommendation it
   came from quoted in full, and what is already on the branch that it must not break.
   When the recommendation is a defect, also write "Opened on a bug report — run `/fix`
   first" there. A session resumed from the marker is sent to step 1, and that line is what
   tells it a diagnosis is still owed.
4. Commit and push both files together with `DEVELOPMENT.md` and every file whose pointer
   the cleaning updated.
5. Report the list with each decision, then invoke `/conceptualize` for the follow-up, or
   `/fix` when the recommendation is a defect, so the diagnosis comes first; `/fix` finds
   the round file already open and hands to `/conceptualize` itself.

The branch and the pull request carry every round. Step 6 of the new round re-checks this
round's acceptance criteria as a regression pass, and step 9 builds the pull request body
from every file in the folder.

Several accepted recommendations become several rounds, run one at a time, never one round
carrying several. Open the most critical; the rest stay `deferred` in this file until their
turn.

## Stop here

With nothing critical and nothing sent back by §3, the hand-on above ends this step and
`/create-pr` continues in the same turn. A bug §3 sent back ends it at `/build` instead.

Otherwise, once every recommendation has a decision:

1. If a next round was opened, *Opening the next round* has already set this file's marker
   to `<!-- claude-plan step=8 status=done -->`, committed, reported the list and handed
   on; nothing is left to do here.
2. Otherwise mark step 8 `done`, set the marker to
   `<!-- claude-plan step=9 status=active -->`, and commit and push, `DEVELOPMENT.md` and
   every file whose pointer the cleaning updated included.
3. Report the list with each decision, then invoke `/create-pr` in the same turn, as with
   nothing critical; it asks before it publishes.
