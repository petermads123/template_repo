---
name: watch-pr
description: Step 10 of the feature pipeline. Re-check the open pull request roughly hourly, act on review comments and CI, and decide whether a comment is a small fix or needs another round through the pipeline. Runs until the pull request is merged or closed. Use after the pull request is opened, or to resume watching one.
argument-hint: [slug, if more than one plan exists]
model: opus
effort: medium
---

# Step 10 — Review

The pipeline does not end when the pull request opens. It ends when the pull request
**merges or closes**, and everything in between is this step: check the pull request about
once an hour, act on what has appeared, and re-arm.

Cheaper than the rest of the pipeline on purpose. Most check-ins find nothing and should
cost almost nothing; the expensive thinking happens only when a comment turns out to need a
new round, and that round runs at its own steps' settings.

## 1. Arm the watch

On the first run, subscribe to the pull request's activity if the environment offers it, so
comments and CI arrive as events rather than being waited for. Then schedule the recurring
check with whatever this environment provides, in this order:

- `send_later` or an equivalent self-scheduling tool — one hour out,
- a recurring task (`/loop 1h /watch-pr`, `CronCreate`),
- failing both, **say so plainly**. An unwatched pull request that everyone believes is
  watched is worse than one nobody claimed to be watching.

Never poll with `sleep`, and never sit in a loop waiting. End the turn; the schedule or the
event wakes you.

## 2. Look at the whole pull request

Every check-in, on the current head — not just the thing that woke you:

- merge state: is it conflicted with the base?
- CI on the latest commit, where the repo has any,
- open review threads and reviews,
- whether it has merged or closed since last time.

## 3. Act, in this order

**Merge conflict** — merge the base branch in and resolve it. Never rebase or force-push a
branch someone else may have checked out. Then re-run the gates and push.

**CI red** — fix it. A failure in code this branch touched is this branch's to fix. A
failure that reproduces on the base branch too is not, and standing down from it is never
silent: say once what is failing and why it is not this pull request's. "Flake" is not a
root cause, and never skip or disable a test to get green.

**Review comments** — classify each one. This is the judgment the step exists for:

| The comment asks for | Do |
|---|---|
| A nit, rename, clearer message, added test, one-function change | Fix it, push, reply, resolve the thread |
| Something you are confident is wrong or already handled | Reply explaining why, leave it open for the reviewer |
| A change of behaviour, a new capability, a different design | **A new round** — see below |

**Nothing** — re-arm and stop, silently. Do not message the user, do not comment on the
pull request, and do not narrate a quiet check-in. Most check-ins are this one.

## 4. When a comment needs another round

A reviewer asking for behaviour that was never in the concept is not a fix, and squeezing it
in as one skips everything the pipeline exists to do. It gets a round, exactly as a step 8
recommendation does:

```bash
cp docs/plans/TEMPLATE.md docs/plans/<feature-slug>/0<N>-<round-slug>.md
```

Mark this file's step 10 `done`, set the new file to
`<!-- claude-plan step=1 status=active -->`, fill its **Builds on** section — naming the
review comment and quoting it — and invoke `/conceptualize`. The round runs steps 1 to 7 on
the same branch and lands in the same pull request; step 10 resumes when it is pushed.

Use the same test as everywhere else. It is not small if it adds or removes a file, changes
a public signature, changes behavior, or needs a new test. **When it is close, route up** —
an over-routed comment costs a conversation, an under-routed one puts unplanned, untested
behaviour into a pull request a reviewer already looked at.

Tell the user before starting a round. They may prefer to answer the reviewer instead.

## 5. Record it

Section 10 of the plan file, one row per thread: who asked for what, and what was done —
fixed and pushed, replied and left open, or taken to round N. This is the record of how the
pull request got from opened to merged, and it is the part nobody can reconstruct later
from the diff.

Quiet check-ins are not recorded. A log of "nothing had changed" nineteen times is noise.

## 6. Merge when the approver has approved

Claude may complete the merge, but only on the approver's say-so and only into a state that
is actually mergeable. **All five** must hold:

1. **An approval exists** from the approver named in `CLAUDE.md` — a review with state
   `APPROVED`, or, where GitHub will not accept one, the fallback below.
2. **The approval is not stale.** A review approves a *commit*. If anything has been pushed
   since, the approval describes code nobody approved. Re-request review and do not merge.
3. **CI is green** on the current head, where the repo has CI at all.
4. **No merge conflict** with the base.
5. **Review threads are resolved.** Two separate things here: no thread is waiting on an
   answer from Claude, *and* — where the repo's ruleset sets
   `required_review_thread_resolution` — every thread is actually marked resolved, because
   GitHub will refuse the merge otherwise. Resolve the ones you addressed; leave open any
   where the commenter is still owed an answer, and say the merge is waiting on them.

Then merge with the repo's configured default method, and afterwards:

- delete the branch if the repo does that,
- mark the plan `<!-- claude-plan step=10 status=done -->` and record the merge in section 10,
- cancel the recurring check,
- say so once, naming the merge commit.

**Never approve anything yourself, and never merge without the approval.** The approval is
the whole authorisation; without it Claude is merging on its own judgment, which is the one
thing this step is not for. A failing gate is never bypassed to honour an approval either —
an approval says *the change is wanted*, not *ship it broken*.

### When the approver cannot leave a review

GitHub refuses both a review request and an approval from the pull request's own author. In
a solo repo — where Claude pushes under the owner's token, so every pull request is authored
by the person who would approve it — the review route is simply unavailable, and waiting for
an approval that cannot exist would wedge the pipeline.

There, the merge signal is an **unambiguous instruction in a comment from the approver on
the pull request**: "merge it", "approved, go ahead". Conditions 2 to 5 still apply in full,
and staleness is measured from the comment rather than a review.

Read that narrowly. "Looks good" on one thread is feedback, not authorisation to merge the
whole pull request, and neither is silence, a thumbs-up, or an approval of some earlier
round. If you are not certain the comment authorises the merge, ask — the cost of asking is
one message and the cost of being wrong is an unwanted merge to `main`.

## 7. Stop conditions

- **Merged or closed** — whether Claude merged it or someone else did, set the marker to
  `<!-- claude-plan step=10 status=done -->`, cancel the recurring check, and say so once.
  The pipeline is finished.
- **The user says stop** — unsubscribe, cancel the check, and stop. Immediately, no
  argument.

Until one of those, keep the next check-in scheduled. Never cancel it because the pull
request looks quiet — quiet is the normal state of a pull request awaiting review, and it
is exactly when a dropped watch goes unnoticed.
