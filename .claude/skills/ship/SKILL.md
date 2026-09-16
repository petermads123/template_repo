---
name: ship
description: Step 7 of the feature pipeline. Commit the verified, tested, concept-checked work and push it to its feature branch. Use after the concept check passes; this pushes the branch but does not open a pull request.
argument-hint: [slug, if more than one plan exists]
model: sonnet
effort: max
---

# Step 7 — Ship

Commit and push. The pull request is step 9 — this step exists so the work is safe on the
remote before the recommendations conversation, which can take a while and can end in
another round of changes.

## 1. Confirm the gates still hold

Everything before this step passed at the time it ran. Confirm it still passes now:

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

And confirm the plan file agrees: steps 1 to 6 all marked `done`, section 6's criteria
table filled in with no unmet rows. A criterion still marked unmet means step 6 sent the
work back and it has not come back — stop and say so.

## 2. Look at what you are about to commit

```bash
git status --short
git diff --stat
```

Read it. Two things to catch here and nowhere else:

- **Files that should not be committed** — scratch scripts, sample data, anything under a
  temp directory, `.claude/.skip-gate`. Leave them out rather than committing and reverting.
- **The plan file** — it *should* be committed. It is the record of why this code looks the
  way it does, and step 9 builds the pull request body from it. On a later round that means
  this round's file; the earlier ones went in with their own commits and are untouched.

## 3. Commit

The branch guard refuses a commit on `main` outright, so if it fires, step 3 did not create
a branch. Fix that before anything else.

One commit for a self-contained change; several if the work genuinely separates (the module,
then the tests, then the docs). Subject line in the imperative, under 72 characters, saying
what changes rather than what you did:

```
Add CSV export for record collections
```

Body: what changed and why, wrapped at 72 columns. Reference the plan file by path so the
reasoning is one link away. Do not paste the plan into the commit message.

## 4. Push

```bash
git push -u origin <branch>
```

On a network failure, retry up to four times with 2s, 4s, 8s then 16s backoff. Do not
retry on a rejection — a rejection means something is wrong rather than slow, so read it.

**This repository is public. Pushing is publishing.** Nothing in the diff should be
anything the user would not want read by a stranger.

## 5. Record it

Section 7 of the plan file: the commit subjects and the branch pushed to. Commit that
update too, or the record is one commit behind the thing it records.

## Stop here

1. Mark step 7 `done` and set the marker to `<!-- claude-plan step=8 status=active -->`.
2. Report: the commits, the branch, and the remote it went to.
3. End the turn.

Do not open a pull request. The user opens step 8 with `/recommend`.
