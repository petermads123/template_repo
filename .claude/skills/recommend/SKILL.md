---
name: recommend
description: Step 8 of the feature pipeline. Propose ranked follow-up work that would make the shipped change into a better product, and agree with the user which to defer, reject, or take through another round. Use after the work is pushed and before opening the pull request.
argument-hint: [slug, if more than one plan exists]
---

# Step 8 — Recommend

The work is shipped to its branch and provably does what was agreed. This step asks the
question the pipeline has deliberately suppressed until now: **what would make this
better?**

It was suppressed for a reason. Scope that arrives during steps 1 to 7 is a distraction;
scope that arrives here is a decision, taken with the finished thing in front of you.

## 1. Look at the finished feature, not the diff

Read section 1 and run the showcase. Then think about it as a user of the code rather than
its author. Productive angles:

- **Adjacent capability** — the obvious next thing someone will ask for once they have
  this. Often the strongest recommendation on the list.
- **Ergonomics** — a signature that works but is awkward to call; a default that will be
  overridden every time; an error a caller cannot act on.
- **Robustness** — an input class the concept declared out of scope that is going to turn
  up anyway.
- **Reach** — a connection to an existing module that would multiply the value of both.
- **Debt this created** — duplication introduced to keep the change small, a `TODO` left
  behind, a test that covers the case rather than the rule.
- **Debt this exposed** — something already wrong in the repo that this work ran into.

## 2. Rank them

Fill section 8. Order by value to the product, not by ease:

| # | Recommendation | Why it helps | Effort | Decision |
|---|---|---|---|---|

Effort in rough terms — `small` is an hour, `medium` is a session, `large` is its own
pipeline. State it even when uncertain; "unknown" is a useful answer and an honest one.

Three to six sharp recommendations beat a dozen mechanical ones. If the honest answer is
that the feature is complete as it stands, say that in one line and offer nothing — an
invented recommendation costs the user real time to evaluate.

## 3. What does not belong here

**A bug is not a recommendation.** Anything actually broken goes back to step 3 and gets
fixed before the pull request. Do not let a defect leave this step wearing a "future
improvement" label.

Neither is anything already agreed in section 1 and not built — that is an unmet acceptance
criterion, and step 6 should have caught it.

## 4. Decide them with the user

Present the list and ask for a decision on each. Three outcomes:

- **`deferred`** — worth doing, not now. Record it; it stays in the plan file as the record.
- **`rejected`** — record the reason. Next time this comes up, the reasoning is already
  there.
- **`next round`** — take it through the pipeline again, as a new round on this branch.

### Opening the next round

A round is a new file in this feature's folder, not an edit to this one. The work already
shipped in step 7 stays exactly as it was written and audited.

```bash
cp docs/plans/TEMPLATE.md docs/plans/<feature-slug>/0<N>-<round-slug>.md
```

Then, in order:

1. In **this** file, mark step 8 `done` and set its marker to
   `<!-- claude-plan step=8 status=done -->`. Exactly one file in the repo is `active`, so
   this one has to stand down before the new one starts.
2. In the **new** file, set the title, the Feature and Round rows, the same branch, and the
   marker `<!-- claude-plan step=1 status=active -->`.
3. Fill its **Builds on** section: what each earlier round delivered, the recommendation it
   came from quoted in full, and what is already on the branch that it must not break.
4. Invoke `/conceptualize` for the follow-up.

The branch and the pull request carry every round. Step 6 of the new round re-checks this
round's acceptance criteria as a regression pass, and step 9 builds the pull request body
from every file in the folder.

Multiple accepted recommendations become multiple rounds, run one at a time — not one round
carrying several. Pick the one with the most value and open it; the rest stay `deferred` in
this file until their turn.

## Stop here

1. Mark step 8 `done` and set the marker to `<!-- claude-plan step=9 status=active -->`.
   If a next round was opened, this file's marker becomes
   `<!-- claude-plan step=8 status=done -->` instead and the new file carries the pipeline.
2. Report: the ranked list with each decision.
3. End the turn.

The user opens step 9 with `/create-pr`.
