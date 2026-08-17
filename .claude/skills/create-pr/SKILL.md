---
name: create-pr
description: Open a pull request for the current branch after verifying the tree is clean. Runs the full test suite plus ruff and mypy, checks STRUCTURE.md is in sync, then confirms with the user before pushing and opening a draft PR. Use when work is finished and ready for review.
allowed-tools: Bash(ruff:*), Bash(mypy:*), Bash(pytest:*), Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(git branch:*)
---

# Create a pull request

Gates first, confirmation second, push last. Nothing leaves the machine before the user
says so.

## 1. Refuse on `main`

```bash
git branch --show-current
```

If it is `main`, stop. The remote has a `main_protect` ruleset, so the push would be
rejected anyway. Tell the user to move the work to a branch and offer the command:

```bash
git checkout -b feat/<topic>
```

## 2. Run the gates

All four. Report the actual output, not a summary:

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

**Any failure stops the skill.** Do not open a PR on a red tree, do not offer to open one
anyway, and do not fix the failures silently and carry on — report what failed, fix it if
the fix is obvious, then re-run the whole gate from the top.

## 3. Check STRUCTURE.md

Compare the `.py` files on disk against the module paths named in `STRUCTURE.md`. Anything
present on disk but missing from the file, or named in the file but gone from disk, stops
the skill until it is fixed. Also skim the signature tables for the modules this branch
touched — the stop gate cannot see signature drift, so this is the only place it gets
caught.

## 4. Confirm before publishing

Show the user, and wait for an explicit yes:

- the branch name, and whether it matches the `type/kebab-case` convention (mention a
  mismatch, do not block on it)
- `git log main..HEAD --oneline` — the commits that will become the PR
- `git status --short` — anything uncommitted that will *not* be included
- the proposed PR title and body

**This repository is public. Pushing is publishing.** Do not push, do not create the PR,
and do not run any command with a side effect on the remote until the user has answered.

## 5. Push and open a draft

Only after confirmation:

```bash
git push -u origin <branch>
gh pr create --draft --title "<title>" --body "<body>"
```

Draft on purpose — nothing auto-merges and the user gets a final look on GitHub.

Return the PR URL as a markdown link.

## PR body shape

```markdown
## What
One paragraph: what this changes and why.

## Changes
- Bullet per meaningful change, file-scoped where useful.

## Verification
- `ruff check .` / `ruff format --check .` / `mypy` / `pytest` — all pass
- Anything run by hand, with the actual result

## Notes
Anything a reviewer should know: trade-offs, deliberate omissions, follow-ups.
```

Omit a section rather than filling it with nothing.
