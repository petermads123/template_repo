# Working in this repo

@STRUCTURE.md

`STRUCTURE.md` above is the map of what lives where. Read it before searching the repo, and
update it in the same change whenever a module or public signature changes.

## This repo has not been set up yet

It was created from a template and still carries the template's package name. **Before
anything else in the first conversation, invoke `/repo-setup`.** It asks what the repo is
for, writes that into the README, renames the package to match the repository, offers the
branch ruleset, and then deletes this block so it never runs again.

If the user arrives with a task instead, say setup comes first and takes a couple of
minutes — a rename afterwards touches imports, tests and every file that names the package.
## The implementation pipeline

Anything that is not cosmetic goes through ten steps. State lives in
`development/<branch>/NN-<round-slug>.md`, not in the conversation, and every step commits
and pushes it, so work survives a context reset or a new session and any session resumes
from the branch. One folder per branch, one numbered file per round; a recommendation
accepted at step 8 opens the next round on the same branch.

| # | Step | Skill | Produces | Waits for |
|---|---|---|---|---|
| 1 | Conceptualize | `/conceptualize` | Agreed concept, acceptance criteria, the branch | the user |
| 2 | Plan | `/plan` | Modules, signatures, implementation guide, test intents | the user |
| 3 | Implement | `/build` → `/implement` | Working code | — |
| 4 | Verify | `/build` → `/verify` | ruff, mypy, plan completeness, STRUCTURE.md | — |
| 5 | Test | `/build` → `/test` | Edge-case suite, pytest green | — |
| 6 | Concept check | `/build` → `/concept-check` | Audit against step 1, not step 2 | — |
| 7 | Ship | `/build` → `/ship` | Round closed, whole tree green | — |
| 8 | Recommend | `/recommend` | Ranked follow-ups, decided with the user | the user |
| 9 | Pull request | `/create-pr` | Whole-branch re-verification, then a PR to `main` | the user, before publishing |
| 10 | Review | `/watch-pr` | Hourly check until the PR merges or closes | — |

`/feature <what to build>` starts the pipeline by opening step 1. In a session that is
already mid-pipeline it reports the step instead.

Exactly one plan file across the repo carries `status=active`. When step 8 opens the next
round, the round before it becomes `done` and the new file takes over. Step 9 marks the
newest round `done` in the commit that opens the pull request, so nothing on `main` ever
says a build is in flight and no commit exists only to tidy up afterwards.

### Three gates, one unattended block

The user decides three times: they confirm the concept (step 1), accept the plan (step 2),
and decide the recommendations (step 8), plus a yes before step 9 publishes. Everything
between the plan and the recommendations — **steps 3 to 7** — is `/build`: one skill that
runs the five steps in order without asking, each in its own subagent on the model that
step pins, committing and pushing after each.

The build **halts** and hands back to the user on exactly two things:

1. anything that would amend section 1 — a deviation that breaks an acceptance criterion,
   a case the concept never decided, a criterion that turns out to be wrong;
2. a gate failing twice for the same reason — one fix attempt is the build's, a second
   failure means the fix was a guess.

Everything else — a red check, a bug the tests find, a signature that had to change — is
the build's to handle. A halt commits what exists, red or not, writes a `Halted` section
into the plan file with the question, and ends the turn; `/build` resumes from the marker
once the user answers.

The user is not watching the build, so each step reports a **trace** — a line or two per
module, class, function and test group it produced — and `/build` relays every trace to the
chat verbatim as the step returns. That is their window into the work.

### More eyes where the work diverges

Most steps have one right answer and one agent is enough. Three do not, and there a second
reader is cheap insurance against one author's blind spots:

| Step | Extra readers | Why there |
|---|---|---|
| 2 Plan | one `plan-critic` | The plan is the last thing anyone re-thinks before the build runs unattended |
| 5 Test | two `test-designer` briefs, `input-space` and `contract` | Edge cases from the parameters and from the promises are different lists |
| 6 Concept check | none extra | Running as its own subagent already makes it an independent read |
| 8 Recommend | three `brainstormer` lenses, `user`, `maintainer`, `integrator` | Follow-ups are opinion; three opinions that disagree are worth more than one |

Read-only agents run in parallel; anything that writes runs alone. The calling step merges
what comes back, applies or rebuts each finding on the record, and stays the one voice in
the code and the plan file.

### Each step picks its own model

Every skill pins a model and effort in its frontmatter, so a step runs on what it needs
rather than on whatever the session happens to be set to. A skill's override lasts the
turn, which is exactly why steps 3 to 7 run as **subagents**: chained in one turn they
would all run on the first skill's model. `/build` passes each step's model to its
subagent; effort cannot be passed, so the subagent reads it from its skill file as intent.

| Step | Model | Effort | Why |
|---|---|---|---|
| 1 Conceptualize | `opus` | `xhigh` | Shaping the concept is the most expensive thing to get wrong |
| 2 Plan | `opus` | `high` | The design fork, and signatures step 4 checks literally |
| 3–7 `/build` | `opus` | `medium` | Orchestration: reads the marker, spawns, relays, halts |
| 3 Implement | `sonnet` | `max` | Transcribing a plan that has already done the thinking |
| 4 Verify | `sonnet` | `max` | Mechanical checks plus classifying each mismatch |
| 5 Test | `sonnet` | `max` | Edge cases and the bugs they expose |
| 6 Concept check | `sonnet` | `max` | A different model from the one that wrote the plan |
| 7 Ship | `sonnet` | `max` | Gates on the whole round, diff review; procedural |
| 8 Recommend | `opus` | `xhigh` | Judging what is worth building next |
| 9 Pull request | `sonnet` | `max` | Verification and writing, both well-specified |
| 10 Review | `opus` | `medium` | Most check-ins find nothing; the judgment is fix-or-new-round |

`/feature` carries step 1's settings because it opens step 1 in the same turn.
`/small-change` runs `opus` at `high`: bypassing the pipeline is a judgment call made
without any of its safety nets, so the step that decides whether a change really is small
gets the clever model.

`max` is the top effort level; every Sonnet step uses it. Aliases rather than pinned IDs, so
a newer Opus or Sonnet is picked up without editing a dozen files. `ultracode` is a
session-level effort setting and not valid in frontmatter, where the levels are `low`,
`medium`, `high`, `xhigh` and `max`.

### Review and merge

| Fact | Value |
|---|---|
| Approver | `petermads123` |
| Merge method | the repository's configured default |

Step 9 requests a review from the approver when it opens the pull request.

**Claude never merges on its own judgment, and never on an approval alone.** A pull request
reaches `main` either because the approver pressed the button themselves, or because they
explicitly told Claude to merge it. An approval says the change is wanted; it does not say
ship it now, and it does not start a merge. Neither does a green tree or every precondition
being satisfied at once — those make a merge permissible, never due.

Once told, the instruction authorises the merge but waives nothing: it must not be stale
(anything pushed since means they are approving code they have not seen), CI green where
there is CI, no merge conflict, and every review thread resolved where the ruleset demands
it. If one fails, say which and wait. Never approve anything yourself.

Where a review request is refused, step 9 **assigns** the approver instead — GitHub permits
assigning an author even though it refuses to make them a reviewer. It gates nothing, but it
puts the pull request in their *Assigned* queue rather than only in *Created*.

**GitHub will not let anyone request a review from, or approve, their own pull request.** In
a solo repo every pull request Claude opens is authored by the person who would approve it,
so the review route is unavailable and waiting for an approval that cannot exist would wedge
the pipeline. There the merge signal is an unambiguous instruction from the approver in a
pull request comment — "merge it", "approved, go ahead". Read it narrowly: "looks good" on
one thread is feedback, not authorisation to merge. When unsure, ask.

### Step 10 runs until the pull request closes

Opening the pull request is not finishing the work. Step 10 re-checks it about once an hour,
acts on review comments and CI, and ends only when the pull request merges or closes. The
plan file is already `done`, so the watch is session state and the pull request thread is
the record; `/watch-pr` in a fresh session finds the pull request from the branch.

`/create-pr` invokes `/watch-pr` unasked, because the alternative is a published pull
request nobody is watching. It is also the one step that mostly does nothing, and a quiet
check-in re-arms silently rather than reporting.

Its judgment call is whether a review comment is a fix or a new round. The same small-or-
large test decides, and the same rule applies: **when it is close, route up.** An
over-routed comment costs a conversation; an under-routed one puts unplanned, untested
behaviour into a pull request a reviewer has already read. A comment that fits neither is
left open and handed to the user — guessing at a comment you cannot place is worse than
saying you cannot place it.

A bot's finding, Copilot's included, is a claim to verify against the code rather than a
request to obey. Because thread resolution gates the merge and a bot never resolves its own
thread, every bot thread must end resolved — which makes "resolve it" the cheapest way to
green. So **a dismissed bot finding is always reported to the user**, with the reason, in
the same breath as the merge.

### The gates are the point

**Steps 1, 2 and 8 end on a question, and wait for the answer.** Never take a user's gate
for them: not because the answer looks obvious, not because they seem to want speed. The
user's confirmation at step 1 opens step 2 in the same turn, and their acceptance at step 2
opens the build — those are the user passing a gate, not Claude skipping one.

The gates are where the work is cheap to redirect: a concept costs a conversation to
change, a plan a revision, and a build that halts costs whatever it built. A build that
runs on a plan the user had not accepted has skipped the only decision that mattered.

Going *backwards* needs no permission. A failing test that reveals an unsettled concept
belongs back at step 1, and saying so — as a halt, from inside the build — is always right.

## What to invoke

| Situation | Use |
|---|---|
| New module, new public function, behavior change, anything needing a design decision | `/feature` |
| Rename, docstring wording, plot styling, message text, formatting | `/small-change` |
| Resuming work already in flight | The step's own skill, or `/feature` to check state |
| A build that halted, once the question is answered | `/build` |
| Need edge cases for a function | `test-designer` subagent, `input-space` or `contract` brief |
| A plan that needs a second reader | `plan-critic` subagent |
| Follow-ups for a finished feature | `brainstormer` subagent, one lens per run |
| STRUCTURE.md looks out of sync with the code | `structure-auditor` subagent |
| Broad "where is X" search across the repo | built-in `Explore` subagent |

### Small or large?

It is **not** a small change if it does any of these:

- adds or removes a file
- changes a public signature
- changes behavior
- needs a new test

Any one of them routes to `/feature`. Everything else is `/small-change`.

### Routing is Claude's job, not the user's

**The user never has to type a slash command.** When they describe work in prose — "I want
to add X", "can you change Y", "this should really do Z" — classify it against the test
above *before touching anything*, and act on the classification:

- **Clearly small** — say so in one line with the reason, then make the change under
  `/small-change`.
- **Clearly not small** — say so in one line with the reason, then start `/feature`.
- **Genuinely ambiguous** — ask, with `AskUserQuestion`, offering the two routes and what
  each would mean for this particular request. Do not resolve a coin flip by guessing.

Announce the routing either way. A one-line "small: local rename, no signature or behaviour
change" lets the user correct a wrong call before it costs anything.

**When it is close but not a coin flip, route up.** `/feature` step 1 is a conversation, so
an over-routed change costs a single sentence to correct — "this is tiny, just do it" — but
an under-routed one skips the concept, the tests and the concept check, and nobody finds out
until much later. The two mistakes are not equally expensive.

Three things this rule does *not* cover:

- **An explicit slash command wins.** If the user types `/small-change`, that is the route,
  even if you would have chosen otherwise. Say so if you disagree, then do as asked.
- **A question is not a work request.** "How does the stop gate decide?" or "where does X
  live?" gets an answer, not a pipeline.
- **A plan already in flight takes precedence.** If a plan file is `active`, a new request
  is usually part of *that* work: the current step, a step to go back to, or a step 8
  recommendation. Check the active plan before starting a second pipeline — the session
  brief reports two active plans as a mistake, and the hooks then guess which one is
  meant.

Never start editing code because a request sounded simple. Skipping the classification is
the failure this section exists to prevent.

## Conventions

`.claude/rules/python.md` loads automatically whenever a `.py` file is read or edited, so
the conventions are already in context — you do not need to invoke anything to get them.
A subagent does not get that for free: the build's steps read the file themselves.

## Branches

Never commit to `main`; it is protected on the remote and `.claude/hooks/guard_git.py`
refuses the command. Branch names are `type/kebab-case`:

| Prefix | Use for |
|---|---|
| `feat/` | new behavior |
| `fix/` | corrected behavior |
| `refactor/` | changed structure, identical behavior |
| `docs/` | prose only |
| `test/` | test-only additions |
| `chore/` | tooling, dependencies, config |

Examples: `feat/csv-export`, `fix/greet-unicode-crash`, `refactor/split-solver-module`,
`chore/bump-ruff`. The branch is chosen and created at the close of step 1, and its plan
folder is named for it: `development/feat/csv-export/`. Where the environment dictates a
different branch to push to, the folder keeps the conventional name and the plan's Branch
row records the real one.

## Commands

Run from the repo root with `.venv` active. All four must pass before a PR:

```powershell
ruff check .
ruff format --check .
mypy
pytest
```

## Automation already in place

- **At session start**, `.claude/hooks/session_brief.py` reports the active plan and the
  step it is on. Silent when nothing is in flight.
- **Before every `Bash` call**, `.claude/hooks/guard_git.py` refuses a commit or push that
  would land on `main`, including inside a compound command. `settings.json` pre-approves
  the git commands the pipeline needs — add, commit, push, fetch, checkout, switch, merge —
  so an unattended build never stalls on a permission prompt; the guard is what makes that
  safe.
- **After every `Write`/`Edit` of a `.py` file**, `.claude/hooks/lint_py.py` runs
  `ruff format` and `ruff check --fix` on that file. Formatting is handled for you; only
  unfixable errors come back.
- **Before a turn ends**, `.claude/hooks/stop_gate.py` decides how strict to be from the
  active plan's step. Steps 1 to 7 are advisory: the build carries its own gates at steps
  4, 5 and 7, and a halt has to be able to end the turn on a red tree. From step 8, and
  whenever no plan is active, it blocks if ruff, mypy or pytest fail, if `STRUCTURE.md`
  does not mention a module that exists on disk, if a test file sits outside `tests/` where
  `pytest` would never collect it, or if a package directory under `src/` has no
  `__init__.py`. Create `.claude/.skip-gate` to bypass it deliberately.

Hooks are read at session start. If you change anything under `.claude/hooks/` or
`.claude/settings.json`, Claude Code must be restarted before it takes effect. Skills and
rules hot-reload without a restart.

## Growth

Keep this file a routing map. When guidance grows past routing, move it into a skill — a
skill's body loads only when used, while everything here is in context every session. Facts
and routing stay; procedures become skills.
