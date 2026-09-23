---
name: recommend
description: Step 8 of the feature pipeline. Propose ranked follow-up work that would make the shipped change into a better product, and agree with the user which to defer, reject, or take through another round. Opened by /build when the round is complete; the user's gate before the pull request.
argument-hint: [slug, if more than one plan exists]
model: opus
effort: xhigh
---

# Step 8 — Recommend

The round is on its branch and provably does what was agreed. This step asks the question
the pipeline has deliberately suppressed until now: **what would make this better?**

It was suppressed for a reason. Scope that arrives during steps 1 to 7 is a distraction —
and since steps 3 to 7 now run without the user, it would have been a distraction nobody
was there to dismiss; scope that arrives here is a decision, taken with the finished thing
in front of you. This is the first time the user has been asked anything since they
accepted the plan, so the report that opens this step is also where they see the build's
outcome as a whole.

## 1. Look at the finished feature, not the diff

Read section 1 and run the showcase. Then get three readings of it that are not yours —
four on a fix round — in parallel; all of them are read-only:

```
Agent with subagent_type: "brainstormer"   lens: user
Agent with subagent_type: "brainstormer"   lens: maintainer
Agent with subagent_type: "brainstormer"   lens: integrator
```

Give each the plan file's path and its lens by name. The **user** lens asks what someone
calling this tomorrow will need next and what is awkward to call; the **maintainer** lens
asks what debt this created or exposed and what the next change will break; the
**integrator** lens asks which existing module would multiply the value of both and where
data leaves in the wrong shape. Each returns three to five recommendations with evidence,
and any bug it found under a separate heading.

On a fix round — section 1 carries a Defect block — run a fourth in the same batch:

```
Agent with subagent_type: "brainstormer"   lens: defect-class
```

It asks where else the root cause's shape occurs, which input from the Class row was put
out of scope and is now the nearest bug, and what should have caught this before it
shipped. Those are the follow-ups a fix produces, and the other three lenses are not
looking for them.

Add your own angle, which the lenses do not cover because only the plan file shows it:

- **What the build halted on or worked around** — the `Halted` section and section 3's
  deviations are a list of places the plan was thinner than the code needed.
- **What the scope left behind** — on a fix round, every item of the Defect block's Class
  row that Explicitly out of scope names is a candidate, and a round opened on one is a
  fix round too.

## 2. Merge and rank them

Combine the lenses' lists with your own. Drop duplicates, keep the better-evidenced of two
that say the same thing, and note where two lenses disagreed — a recommendation the user
lens wants and the maintainer lens warns against is worth showing the user as exactly
that. Then fill section 8, ordered by value to the product, not by ease:

| # | Recommendation | Why it helps | Effort | Decision |
|---|---|---|---|---|

Effort in rough terms — `small` is an hour, `medium` is a session, `large` is its own
pipeline. State it even when uncertain; "unknown" is a useful answer and an honest one.

Three to six sharp recommendations beat a dozen mechanical ones. If the honest answer is
that the feature is complete as it stands, say that in one line and offer nothing — an
invented recommendation costs the user real time to evaluate.

## 3. What does not belong here

**A bug in what this round built is not a recommendation.** Anything broken in the code
this round's section 1 promised — found by you or under a brainstormer's **Bugs** heading —
goes back through `/build` from step 3 and gets fixed before the pull request. Do not let
such a defect leave this step wearing a "future improvement" label.

A defect *outside* what this round promised is different: one section 1 put out of scope by
name, one the `defect-class` lens found elsewhere in the repo, one in code this round never
touched. Fixing it in the build would be drift — the concept check calls a fix that quietly
widened exactly that — so it **is** a recommendation, and a round opened on it goes
through `/fix`, below.

Neither is anything already agreed in section 1 and not built — that is an unmet acceptance
criterion, and step 6 should have caught it.

## 4. Decide them with the user

Commit and push the list first — subject `Recommend: <title>` — so it is on disk before
the conversation, which can take a while. Then present it and ask for a decision on each.
Three outcomes:

- **`deferred`** — worth doing, not now. Record it; it stays in the plan file as the record.
- **`rejected`** — record the reason. Next time this comes up, the reasoning is already
  there.
- **`next round`** — take it through the pipeline again, as a new round on this branch.

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
4. Commit and push both files, then invoke `/conceptualize` for the follow-up — or `/fix`
   when the recommendation is a defect, so the diagnosis comes first; it finds the round
   file already open and hands to `/conceptualize` itself. In that case also write
   "Opened on a bug report — run `/fix` first" under **Builds on** before committing: a
   session resumed from the marker is sent to step 1, and that line is what tells it a
   diagnosis is still owed.

The branch and the pull request carry every round. Step 6 of the new round re-checks this
round's acceptance criteria as a regression pass, and step 9 builds the pull request body
from every file in the folder.

Multiple accepted recommendations become multiple rounds, run one at a time — not one round
carrying several. Pick the one with the most value and open it; the rest stay `deferred` in
this file until their turn.

## Stop here

1. Once every recommendation has a decision, mark step 8 `done` and set the marker to
   `<!-- claude-plan step=9 status=active -->`, commit and push. If a next round was
   opened, this file's marker is `<!-- claude-plan step=8 status=done -->` instead and the
   new file carries the pipeline.
2. Report: the ranked list with each decision.
3. End the turn.

The user opens step 9 with `/create-pr`.
