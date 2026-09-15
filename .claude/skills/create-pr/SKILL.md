---
name: create-pr
description: Step 9 of the feature pipeline. Re-run every gate, confirm with the user, then open a draft pull request to main with a body built from the plan file. Use when the work is shipped, the recommendations are decided, and the branch is ready for review.
argument-hint: [slug, if more than one plan exists]
---

# Step 9 — Pull request

The last step. Gates first, confirmation second, publication last.

## 1. Refuse on `main`

```bash
git branch --show-current
```

If it is `main`, stop. There is nothing to open a pull request from, and the branch guard
has been refusing commits all along, so this means the work was never branched.

## 2. Run every gate once more

The tree has changed since step 4 — step 5 fixed bugs, step 8 may have added a round. Prove
it is still green rather than trusting the earlier run:

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

**Any failure stops the skill.** Do not open a pull request on a red tree and do not offer
to open one anyway. Fix it, then re-run the whole set from the top.

Then confirm **every round in this feature's folder** is complete: steps 1 to 8 marked
`done`, section 6 with no unmet criteria, section 8 with a decision against every
recommendation. An undecided recommendation means step 8 is not finished.

A folder with several rounds means several files, and all of them ship in this pull
request. Only the newest should be `active`; an earlier one still marked `active` means a
round was abandoned mid-pipeline rather than finished, and that is worth raising before
publishing anything.

Run the `structure-auditor` subagent one final time. `STRUCTURE.md` is what the next session
reads instead of searching the repo, so it being wrong costs more than any other stale file.

## 3. Confirm before publishing

Show the user, and wait for an explicit yes:

- the branch name, and whether it matches `type/kebab-case` (mention a mismatch, do not
  block on it),
- `git log main..HEAD --oneline` — the commits that become the pull request,
- `git status --short` — anything uncommitted that will *not* be included,
- the proposed title and the full body.

**This repository is public. Opening a pull request is publishing.** Do not push, do not
create the pull request, and do not run anything with a remote side effect until the user
has answered.

## 4. Open it as a draft

```bash
git push -u origin <branch>
gh pr create --draft --title "<title>" --body "<body>"
```

Draft on purpose: nothing auto-merges, and the user gets a last look on GitHub.

## 5. Record and close the plan

Write the URL into section 9 of the newest round, then set that file's marker to
`<!-- claude-plan step=9 status=done -->`. That is what clears the session brief — leave it
`active` and every future session opens believing this work is still in flight. Commit and
push that final edit.

Earlier rounds in the folder are already `done`; they were stood down when their successor
opened. Confirm it rather than assuming it.

## The body

Built from the plan files, not from the diff. The diff is already on the page; what a
reviewer cannot see is why.

**Every round in the folder goes in the body**, oldest first. A reviewer opening a
three-round branch needs to see that it is three deliberate passes over one feature, not
one change that kept growing.

```markdown
## What
One paragraph from round 1's section 1: what this adds and why.
For a multi-round branch, one line per round after it: what that round added and which
recommendation it came from.

## Acceptance criteria
The table from section 6 of each round — criterion, met, evidence.
Group by round when there is more than one.

## Changes
- Bullet per meaningful change, file-scoped where useful.

## Verification
- `ruff check .` / `ruff format --check .` / `mypy` / `pytest` — all pass
- Test coverage of each intent, from section 5 of each round
- For a multi-round branch, the regression table from the newest round's section 6:
  the earlier rounds' criteria still hold
- Anything run by hand, with its actual result

## Follow-ups
Deferred recommendations from section 8 of every round, with their reasons. Drop any that
a later round went on to implement.

## Notes
Trade-offs, deliberate omissions, anything a reviewer should know.

Plan: `docs/plans/<feature-slug>/` — one file per round.
```

Omit a section rather than filling it with nothing.

Return the pull request URL as a markdown link.
