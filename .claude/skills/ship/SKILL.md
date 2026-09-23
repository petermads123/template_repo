---
name: ship
description: Step 7 of the feature pipeline. Close the round — confirm every gate still holds on the whole tree, review everything the round committed for things that should not be there, record the commits, and push. Runs inside /build as a subagent, after the concept check passes; does not open a pull request.
argument-hint: [slug, if more than one plan exists]
model: sonnet
effort: max
---

# Step 7 — Ship

Every step since 1 has committed and pushed as it went, so the work is already safe on the
remote. This step closes the round: it is the one moment the round is looked at whole
rather than a step at a time, and the point at which the build promises a green tree that
nothing after it takes back — the stop gate blocks from step 8 on that promise.

This step runs unattended, as a subagent of `/build`. The rules for a failure are the
block's: fix once, halt on a repeat.

## 1. Confirm the gates hold on the whole tree

Everything before this step passed at the time it ran. Confirm it still passes now:

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

And confirm the plan file agrees: steps 1 to 6 all marked `done`, section 6's criteria
table filled in with no unmet rows, section 5's intent table with a test against every
intent. A criterion still marked unmet means step 6 sent the work back and it has not come
back — halt and say so.

## 2. Review what the round committed

```bash
git log main..HEAD --oneline
git diff main...HEAD --stat
```

Read it as a reviewer would. Two things to catch here and nowhere else:

- **Files that should not be committed** — scratch scripts, sample data, anything under a
  temp directory. `.claude/.skip-gate` and `settings.local.json` are ignored, but a stray
  file is not. Remove it in a commit of its own so the history says what happened.
- **A step that committed nothing.** Every step from 1 leaves a commit naming the round
  file. One missing means that step's record is only in the file, not in the history;
  note it in section 7 rather than rewriting anything.

On a later round the earlier rounds' commits are already there and untouched. Only this
round's are reviewed.

## 3. Record, commit, push

Section 7 of the plan file: the commit subjects of this round and the branch they are on.

```bash
git push -u origin <branch>
```

On a network failure, retry up to four times with 2s, 4s, 8s then 16s backoff. Do not
retry on a rejection — a rejection means something is wrong rather than slow, so read it.

**If this repository is public, pushing is publishing.** Nothing in the diff should be
anything the user would not want read by a stranger.

## Stop here

1. Mark step 7 `done` and set the marker to `<!-- claude-plan step=8 status=active -->`.
   Commit that with subject `Ship: <title>` — the last commit of the round — and push.
2. Report, in the `/build` contract: `STATUS`, and a `TRACE` with the four checks and
   their results, the pass count, and the round's commit list.
3. End. `/build` reports the round and opens step 8; do not open a pull request.
