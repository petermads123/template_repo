---
name: create-pr
description: Step 9 of the feature pipeline. Verify the whole branch in one pass — clean tree, current base, the full test suite, every module showcase and every round's plan — then confirm with the user, mark the plan done, and open a pull request to main, ready for review. Use when the recommendations are decided and the branch is ready for review.
argument-hint: [slug, if more than one plan exists]
model: sonnet
effort: max
---

# Step 9 — Pull request

The last step that changes the branch. Gates first, confirmation second, publication last.

## 1. Refuse on `main`

```bash
git branch --show-current
```

If it is `main`, stop. There is nothing to open a pull request from, and the branch guard
has been refusing commits all along, so this means the work was never branched.

## 2. Verify the whole branch, not just the last round

Nothing before this step has verified the branch as a whole. Step 7 checked the tree at the
moment it closed its round, and knows nothing of what a later round did to the code an
earlier one shipped. This is the only place the finished branch is proved green in one
pass, so run all of it, in this order.

### 2a. Clean tree, so the gates test what ships

```bash
git status --short
```

**It must be empty before any gate runs.** Every step commits as it goes, so a dirty tree
here means something was edited outside the pipeline. Commit what belongs and remove what
does not, then continue. Do not run the suite first and reconcile afterwards — that is the
failure this ordering exists to prevent.

### 2b. Catch up with the base

```bash
git fetch origin main
git log --oneline HEAD..origin/main
```

If `main` has moved since the branch started, green here is not green merged. Merge it in,
resolve anything it conflicts with, and **start section 2 again from the top** — a merge
can break the suite as easily as a commit can.

### 2c. The four gates, whole suite

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

`pytest` with no filters, no `-k`, no deselects, no single test file: the point is the whole
suite, including every test every round added. Report the actual pass count.

**Any failure stops the skill.** Do not open a pull request on a red tree and do not offer
to open one anyway. Fix it, then re-run section 2 from the top.

### 2d. Every module the branch touched, run standalone

```bash
git diff --name-only main...HEAD -- "*.py"
```

Run `python -m <package>.<module>` for every module in that list that has a `main()`
showcase — not just the ones the newest round added. A round that edits a module an earlier
round shipped can leave its showcase printing something stale or crashing outright, and
nothing since step 4 of that earlier round has run it.

Read the output, not just the exit code.

### 2e. Plan completeness, every round

Take the Public API table from **every** round in the folder and confirm each signature
still exists as written. A later round that changed an earlier round's signature should
have corrected that round's table at the time; if it did not, the earlier plan now
advertises an API the code no longer has. Fix the table, and say which round drifted.

Then run the `structure-auditor` subagent one final time. `STRUCTURE.md` is what the next
session reads instead of searching the repo, so it being wrong costs more than any other
stale file.

### 2f. Every round finished

Confirm **every round in this branch's folder**: steps 1 to 8 marked `done`, section 6
with no unmet criteria, section 8 with a decision against every recommendation, no
`Halted` section left unanswered. An undecided recommendation means step 8 is not finished.

On a multi-round branch, also confirm the newest round's **Earlier rounds still hold**
regression table is filled in. An empty one means step 6 skipped the regression pass, and
the earlier rounds' criteria have not been checked against the code as it now stands.

Only the newest file should be `active`; an earlier one still marked `active` means a round
was abandoned mid-pipeline rather than finished, and that is worth raising before
publishing anything.

## 3. Confirm before publishing

Show the user, and wait for an explicit yes:

- the branch name, and whether it matches `type/kebab-case` (mention a mismatch, do not
  block on it),
- `git log main..HEAD --oneline` — the commits that become the pull request,
- the result of every check in section 2, including the pass count,
- the proposed title and the full body.

The tree was already required to be clean in 2a, so there should be nothing uncommitted to
report. If there is, something was written after the gates ran: go back to section 2.

**If this repository is public, opening a pull request is publishing.** Do not push, do not
create the pull request, and do not run anything with a remote side effect until the user
has answered.

## 4. Close the plan, then open the pull request

The plan file is `done` from here, and it says so **before** the pull request exists, in
the last commit the pull request carries. Marking it done afterwards would need a commit
after the review started, or a second pull request just for bookkeeping; leaving it active
would put a live marker on `main` at merge and make every fresh session think a build is in
flight. Neither is acceptable, so:

1. In the newest round, mark step 9 `done`, set the marker to
   `<!-- claude-plan step=9 status=done -->`, and leave the URL row of section 9 reading
   `opened by step 9 — see the branch's pull request`. The URL does not exist yet and there
   will be no commit to write it into; the pull request is found from the branch.
2. Commit with subject `Pull request: <title>` and push:

   ```bash
   git push -u origin <branch>
   ```

3. Open the pull request with whatever this environment provides — the GitHub MCP tools
   where they are available, `gh pr create` where it is — with the title and body the user
   confirmed, base `main`, **not a draft**, and a review requested from the approver named
   in `CLAUDE.md`. Two things can go wrong with the request, and both are expected rather
   than errors:

   - **The approver is the pull request's own author.** GitHub refuses with *"Review cannot
     be requested from pull request author"*. This is the normal case in a solo repo, where
     Claude pushes under the owner's own token.
   - **The approver is not a collaborator.** Say the request could not be made and name
     who would need to be added.

   **When the review request is refused, assign them instead.** GitHub allows assigning an
   author even though it refuses to make them a reviewer, so the pull request still lands
   in their *Assigned* queue rather than only in *Created*. It is not a review request and
   does not gate anything, but it is the closest thing that works. Say which of the two
   happened. Never let a failed reviewer request stop the pull request being opened.

**If the branch already has an open pull request** — a later round opened from step 10, or
a fix round opened on a bug reported against what the branch shipped — there is nothing to
open. Push, update the existing pull request's body from every round in the folder, skip
the review request, say so, and go straight to section 5 so `/watch-pr` resumes.

**Not a draft.** Everything ahead of a reviewer has already happened: the branch was
verified whole in section 2, audited against its concept in step 6, and the user said yes
in section 3. A draft would understate that and leave them a button to press before anyone
can look at it.

This also means section 3 is the only gate between the work and a published pull request.
Treat it that way — an unanswered confirmation is not a yes, and neither is silence.

## 5. Hand off to step 10

Invoke `/watch-pr`. That is the one place in the pipeline where a step starts the next one
without being asked: the alternative is a published pull request that nobody is watching
because the user did not know to say so.

The plan is `done`, so the session brief goes quiet from here; the pull request thread is
the record of the review, and `/feature` with no argument reports the last round and its
pull request when a fresh session asks where things stand.

## The body

Built from the plan files, not from the diff. The diff is already on the page; what a
reviewer cannot see is why.

**Every round in the folder goes in the body**, oldest first. A reviewer opening a
three-round branch needs to see that it is three deliberate passes over one feature, not
one change that kept growing.

```markdown
## What
One paragraph from round 1's section 1: what this adds and why. For a fix round, whichever
round carries the Defect block, add the Defect block's Observed, Root cause and Scope rows
in a line each, so the reviewer sees the cause and not only the change. For a multi-round
branch, one line per round after it: what that round added and which recommendation it
came from.

## Acceptance criteria
The table from section 6 of each round — criterion, met, evidence.
Group by round when there is more than one.

## Changes
- Bullet per meaningful change, file-scoped where useful.

## Verification
- `ruff check .` / `ruff format --check .` / `mypy` / `pytest` — all pass, N tests
- Every module showcase on the branch re-run standalone
- Test coverage of each intent, from section 5 of each round
- For a multi-round branch, the regression table from the newest round's section 6:
  the earlier rounds' criteria still hold
- Anything run by hand, with its actual result

## Follow-ups
Deferred recommendations from section 8 of every round, with their reasons. Drop any that
a later round went on to implement.

## Notes
Trade-offs, deliberate omissions, anything a reviewer should know — including anything the
build halted on and how the user answered.

Plan: `development/<branch>/` — one file per round.
```

Omit a section rather than filling it with nothing.

Return the pull request URL as a markdown link.
