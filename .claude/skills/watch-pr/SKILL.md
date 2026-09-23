---
name: watch-pr
description: Step 10 of the feature pipeline. Re-check the open pull request roughly hourly, act on review comments and CI, and decide whether a comment is a small fix or needs another round through the pipeline. Merges only when the user explicitly says to, never on an approval alone. Runs until the pull request is merged or closed. Use after the pull request is opened, or to resume watching one.
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

The plan file was marked `done` at step 9, so nothing on disk says a watch is running: the
watch is session state, and the pull request thread is the record of the review. Resuming
in a fresh session means finding the pull request for the checked-out branch and arming
the watch again.

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

**CI red** — where the repo has CI at all: fix it. A failure in code this branch touched is
this branch's to fix. A failure that reproduces on the base branch too is not, and standing
down from it is never silent: say once what is failing and why it is not this pull
request's. "Flake" is not a root cause, and never skip or disable a test to get green.

**Review comments** — classify each one. This is the judgment the step exists for:

| The comment asks for | Do |
|---|---|
| A nit, rename, clearer message, added test, one-function change | Fix it, push, reply, resolve the thread |
| Something you are confident is wrong or already handled | Reply explaining why, leave it open for the reviewer |
| A change of behaviour, a new capability, a different design | **A new round** — see below |
| Anything you cannot confidently place in one of those three | **Leave it open and tell the user.** Name the thread and say what you are unsure about. |

That last row is not a failure. A review comment you cannot classify is exactly the thing a
person should read, and guessing at it is worse than saying so.

A fix pushed from here is pushed with no active plan, so the stop gate holds its strict
line: the four checks must be green before the turn ends. That is right — a review fix is
the one change on the branch nothing else re-verifies.

### Bot reviews

Copilot and other review bots follow the same table with two differences that matter.

**A bot finding is a claim to verify, not a request to obey.** Read the code it points at
before doing anything. Bots produce confident false positives at a rate humans do not — they
miss context the surrounding code makes obvious, flag deliberate choices as mistakes, and
occasionally invent a rule the repo does not hold. Verifying is the work; the comment is
only the prompt for it.

**Every bot thread must reach a terminal state.** Where the ruleset sets
`required_review_thread_resolution`, an unresolved thread blocks the merge forever, and a
bot will never come back to resolve its own. "Leave it open for the reviewer" therefore does
not apply to a bot — there is no reviewer to leave it for. Each one ends in exactly one of:

| Verdict | Do |
|---|---|
| Correct, and in scope | Fix it, push, reply naming the commit, resolve |
| Correct, but a change of behaviour or design | Open a round, reply saying where it went, resolve |
| Wrong | Reply with the **specific** reason it is wrong, resolve, **and list it in the report to the user** |
| You cannot tell | Leave it open, and tell the user which thread and why |

**A dismissed bot finding is always reported.** This is the one place where the incentives
point the wrong way: the ruleset makes resolution a precondition of merging, so "resolve it"
is the cheapest action available and the one that makes the green appear. That is exactly
why it cannot be silent. Resolving a thread you did not understand, to get a merge through,
is the same failure as deleting a test that fails — and it is easier to do, because nobody
is watching a bot's thread.

Never resolve a bot thread without a reply saying what was decided. The reply is not for the
bot; it is the record a person reads later when the bug the bot actually found turns up.

**Nothing** — re-arm and stop, silently. Do not message the user, do not comment on the
pull request, and do not narrate a quiet check-in. Most check-ins are this one.

## 4. When a comment needs another round

A reviewer asking for behaviour that was never in the concept is not a fix, and squeezing it
in as one skips everything the pipeline exists to do. It gets a round, exactly as a step 8
recommendation does:

```bash
cp development/TEMPLATE.md development/<branch>/0<N>-<round-slug>.md
```

Set the new file to `<!-- claude-plan step=1 status=active -->`, fill its **Builds on**
section — naming the review comment and quoting it — commit, and invoke `/conceptualize`.
The round runs steps 1 to 9 on the same branch: its step 9 re-verifies the whole branch,
marks the round `done` and pushes into the same pull request, and its `/watch-pr` resumes
this watch.

A comment that reports a **defect** in what the branch shipped opens the round the same
way but invokes `/fix` instead: it finds the just-opened file, reproduces and diagnoses
before anything is agreed, and hands to `/conceptualize` itself. Write "Opened on a bug
report — run `/fix` first" under **Builds on** before committing, so a session resumed
from the marker knows a diagnosis is still owed. The folder keeps its prefix; the filled
Defect block is what makes the round a fix round.

Use the same test as everywhere else. It is not small if it adds or removes a file, changes
a public signature, changes behavior, or needs a new test. **When it is close, route up** —
an over-routed comment costs a conversation, an under-routed one puts unplanned, untested
behaviour into a pull request a reviewer already looked at.

Tell the user before starting a round. They may prefer to answer the reviewer instead.

## 5. The record

The pull request thread is the record: every fix names its commit in a reply, every
dismissal says why, every round says where it went. Nothing is written to the plan file
from here — it was closed at step 9, and a commit that only updates a log after the review
started is the bookkeeping this pipeline was redesigned to avoid.

Quiet check-ins are recorded nowhere. A log of "nothing had changed" nineteen times is noise.

## 6. Merge only when told to

**Claude never merges on its own judgment, and never on an approval alone.** A pull request
reaches `main` exactly two ways:

- **The user presses "Merge pull request" themselves.** Nothing for this step to do but
  notice it happened and close out.
- **The user explicitly tells Claude to merge it** — in the session, or in a pull request
  comment. "Merge it", "go ahead and merge", "approved, merge it".

**An approval is not an instruction.** A review marked `APPROVED` says the change is
wanted; it does not say ship it now. It does not start a merge, and neither does a green
tree, a resolved thread, a passing check, or every condition below being satisfied at once.
Satisfying the preconditions makes a merge *permissible*, never *due*.

Read the instruction narrowly. "Looks good" on one thread is feedback. A thumbs-up is not a
sentence. Silence is not consent, and neither is a week of it. If you are not certain the
user is telling you to merge **this** pull request **now**, ask — the cost of asking is one
message and the cost of being wrong is an unwanted commit on `main`.

### Once told, check before doing it

An instruction authorises the merge; it does not waive the gates. All four must hold, and
none may be bypassed to honour the instruction:

1. **The instruction is not stale.** It referred to the code as it stood. If anything has
   been pushed since, say so and ask again rather than merging something they have not seen.
2. **CI is green** on the current head, where the repo has CI.
3. **No merge conflict** with the base.
4. **Every review thread is resolved**, where the ruleset requires it — and resolved because
   it was dealt with, not to clear the gate.

If one fails, say which, fix what is fixable, and wait. "You told me to merge" is not a
reason to merge something broken; they told you to merge the thing they last saw working.

### After merging

- **Delete the branch.** Whoever merged it — the user in the GitHub UI, or Claude on their
  instruction — deleting the merged branch is part of closing out, and needs no separate
  permission. First confirm the merge from the repository rather than from the event:
  `git fetch origin` and `git merge-base --is-ancestor origin/<branch> origin/main`. Only a
  branch whose head is an ancestor of `main` is deleted; a closed-unmerged branch is left
  for the user. Then `git push origin --delete <branch>`, and drop the local branch too.
  A hosted environment may refuse a ref deletion while still accepting pushes; if the
  delete is refused, say so once and name the branch rather than reporting it deleted —
  the user can remove it from the repository's Branches page.
- Cancel the recurring check.
- Report once: the merge commit, and **every bot finding dismissed along the way**, with the
  reason each was dismissed.

## 7. Stop conditions

- **Merged or closed** — whether Claude merged it or someone else did, delete the branch
  if it was merged (per **After merging** above), cancel the recurring check and say so
  once. The pipeline is finished; the plan file already says so.
- **The user says stop** — unsubscribe, cancel the check, and stop. Immediately, no
  argument.

Until one of those, keep the next check-in scheduled. Never cancel it because the pull
request looks quiet — quiet is the normal state of a pull request awaiting review, and it
is exactly when a dropped watch goes unnoticed.
