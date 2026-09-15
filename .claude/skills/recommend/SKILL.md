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
- **`round 2`** — take it through the pipeline again.

For a round 2, append a new `### Round 2 — <title>` section under Rounds rather than
editing sections 1 to 7, set the marker back to `<!-- claude-plan step=1 status=active -->`,
and invoke `/conceptualize` for the follow-up. The original concept stays readable, and the
existing branch and pull request carry both rounds.

## Stop here

1. Mark step 8 `done` and set the marker to `<!-- claude-plan step=9 status=active -->`.
   For a round 2, set it back to step 1 instead.
2. Report: the ranked list with each decision.
3. End the turn.

The user opens step 9 with `/create-pr`.
