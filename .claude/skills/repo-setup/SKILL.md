---
name: repo-setup
description: One-time setup for a repo created from this template. Asks what the repo is for and writes it into the README, renames the package to match the repository, offers the branch protection ruleset, then removes its own reference from CLAUDE.md so it never runs again. Use at the start of the first conversation in a fresh clone.
argument-hint: [what the repo is for, optionally]
model: opus
effort: high
---

# Repo setup

Runs once, in the first conversation after a repo is created from this template. It turns
`template_repo` into *this* repo and then deletes itself from the routing map.

Everything here is a conversation. Do not guess the repo's purpose, its package name or how
many people work on it — those are the three things only the user knows, and getting any of
them wrong means renaming things twice.

## 1. Check it has not already run

```bash
ls src/
grep -n "repo-setup" CLAUDE.md
```

If `src/template_repo/` is gone, or `CLAUDE.md` no longer references this skill, setup has
already happened. **Say so and stop.** Re-running would rename an already-renamed package.

If the two disagree — the package is renamed but the reference is still there, or the
reverse — say which, and fix only the half that is wrong.

## 2. Ask what the repo is for

One question, and listen to the answer rather than filling it in:

> What is this repo for? A sentence or two on what it does and who or what uses it.

Write it into `README.md`: replace the `# template_repo` title and the `Repo description.`
line under it. Keep it to what they said — this is the description a stranger reads first,
and inflating it helps nobody.

## 3. Rename the package

The package folder should match the repository. Derive a candidate from the remote:

```bash
git remote get-url origin
```

`my-cool-thing` becomes `my_cool_thing`. The name must be a valid Python identifier —
lowercase, underscores, not starting with a digit — and must not be `lib`, `build`, `dist`,
`sdist`, `src`, `tests` or `docs`. The first four are in `.gitignore` and would leave the
folder silently untracked; the rest collide with directories this repo already uses.

**Propose the candidate and let the user confirm or override it.** A repo name is not always
a good package name.

Then rename, and update everything that names it:

```bash
git mv src/template_repo src/<package_name>
```

| File | What to change |
|---|---|
| `pyproject.toml` | `[project] name`, `[project] description` |
| `tests/test_hello_world.py` | `from <package_name> import greet` |
| `STRUCTURE.md` | the tree, the two module headings, the `main()` invocation |
| `README.md` | the title, the description, both install URLs, the setup checklist |
| `.claude/rules/python.md` | the worked-example path in the showcase section |

`[tool.setuptools.packages.find]` points at `src` and `[tool.mypy] files` names directories,
so neither needs touching. Confirm that by reading them rather than assuming it.

Set the **Approver** row in `CLAUDE.md`'s Review and merge table to the repo owner from the
remote URL, unless the user names someone else.

## 4. Offer the branch ruleset

First ask, because the answer changes the ruleset:

> Do other people work in this repo, or is it just you?

- **Collaboration** — set `required_approving_review_count` to `1`.
- **Solo** — set it to `0`.

The template is `.claude/skills/repo-setup/main_protect.json`. It protects `main` against
deletion and force-push, requires a pull request, dismisses stale reviews on push, requires
review threads to be resolved, and asks Copilot for a review on each push.

Apply it if this environment can — a rulesets API call, `gh api`, an MCP tool. **If it
cannot, do not pretend.** Write the filled-in JSON out, show it, and tell the user exactly
where it goes: *Settings → Rules → Rulesets → New ruleset → Import a ruleset*.

One thing to flag either way, because it decides whether step 10 can ever merge:
`require_last_push_approval` is `true`, which means the most recent push must be approved by
someone other than whoever pushed it. In a solo repo nobody else exists to approve it, and
GitHub will not let an author approve their own pull request — so merging needs either a
bypass actor or that rule turned off. Say this plainly and let the user decide; do not
quietly change it for them.

## 5. Remove yourself from the routing map

Delete the `/repo-setup` block from `CLAUDE.md`. That reference is the only thing that makes
this skill run at the start of a conversation, so removing it is what stops setup happening
twice. The skill file stays on disk — harmless, and still there if a rename is needed later.

## 6. Ask what else

> Is there anything else about this repo's setup I should know or configure?

Dependencies to add, a CI workflow, an editor setting, a convention that differs from the
template's. Handle what comes back, or route it: a CI workflow is a `/feature`, a wording
tweak is a `/small-change`.

## 7. Finish

Run the full gate, since a rename touches imports:

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

Then `pip install -e ".[dev]"` and `python -m <package_name>.hello_world`, which is the
first thing that proves the rename and the `src/` layout agree.

Show the user what changed and ask whether they are happy with the setup. **Only if they
are**, offer to commit it on a `chore/repo-setup` branch and open a pull request to `main`.
Do not commit setup they have not looked at.
