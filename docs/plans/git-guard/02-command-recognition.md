# Git guard: recognising the command

<!-- claude-plan step=2 status=active -->

| Field | Value |
|---|---|
| Feature | `git-guard` (the folder) |
| Round | `2` |
| Branch | `claude/setup-recommendations-qoyxhf` |
| Started | `2026-09-21` |

## Progress

| # | Step | Skill | Status |
|---|---|---|---|
| 1 | Conceptualize | `/conceptualize` | done |
| 2 | Plan | `/plan` | pending |
| 3 | Implement | `/implement` | pending |
| 4 | Verify | `/verify` | pending |
| 5 | Test | `/test` | pending |
| 6 | Concept check | `/concept-check` | pending |
| 7 | Ship | `/ship` | pending |
| 8 | Recommend | `/recommend` | pending |
| 9 | Pull request | `/create-pr` | pending |
| 10 | Review | `/watch-pr` | pending |

Statuses: `pending`, `in progress`, `done`.

## Builds on

| Round | File | What it delivered |
|---|---|---|
| 1 | `01-git-guard.md` | Rebuilt `guard_git.py`'s parsing on a quote-aware lexer, so punctuation in a commit message no longer switches the guard off. Judges each invocation against the branch that will be checked out when it runs, trusting a switch only across a run of `&&` and newlines. Refuses unreadable input naming `commit` or `push` on `main`. Gave `guard_git.py`, `plan_state.py` and `stop_gate.py` their first tests — 217 of them. Fixed one placeholder defect in `stop_gate.py`, accepted into that round's concept by the user at step 6. |

This round came from recommendations `R1`, `R2` and `R3` of round `1`, taken together
because they are one idea seen three ways. They read:

> **R1** — Find the git invocation inside a segment instead of assuming `tokens[0]`.
> Closes five of the nine remaining holes at once — `GIT_EDITOR=true git commit`,
> `sudo git push`, backticks, a leading redirection, and `GIT` in capitals on a
> case-insensitive filesystem.
>
> **R2** — Teach `push_targets_main` the refspec shapes it does not know: a push option
> that takes a value is read as the remote, so `git push -o ci.skip origin` slips through
> on `main`; `@` is git's alias for `HEAD` and only the literal is matched;
> `refs/heads/main` is not recognised as `main` when it is a *switch* target.
>
> **R3** — Decide the policy for a switch that cannot be resolved statically.
> `git checkout -` is treated as no switch at all, which is right when `-` goes somewhere
> safe and wrong when it goes to `main`.

What is already on the branch that this round must not break:

- **Round 1's eight acceptance criteria**, A1 to A9, re-checked in this round's step 6 as a
  regression pass. The differential that evidenced A5 — 783 generated commands, 1,566
  comparisons against the module on `main` — is the tool to re-run, not a set of test names
  to re-read.
- **217 tests** across the three hooks. A change that makes the guard stricter will move
  some of them; each move is a decision to record, not a number to restore.
- **The seven public signatures** in `guard_git.py`. R1 in particular pushes on
  `git_subcommand`, whose parameter list is documented in `STRUCTURE.md` and checked
  literally at step 4.
- **The allow-what-cannot-be-parsed posture.** Round 1 narrowed it deliberately: unreadable
  input is refused only when it names `commit` or `push` on `main`. R1 makes the guard
  stricter in a direction that risks false positives — `echo git commit` must not trip it —
  and a guard that blocks legitimate work is the failure its own docstring calls worse.

---

## 1. Concept

### What this is

Round 1 taught the guard to read a command the way a shell reads it. This round teaches it
to find, inside that reading, *which* invocation is git and *what* that invocation actually
targets.

Three things change. The guard skips the prefix a shell skips before a command's name —
variable assignments, redirections, and the backticks or `$( )` that wrap a substitution —
and matches the executable without regard to case. It steps over a short list of wrapper
programs that exec their argument: `sudo`, `env`, `time`, `nohup`, `doas`. And it learns the
refspec shapes it does not yet know: a push option that takes a value, `@` as git's alias
for `HEAD`, and `refs/heads/main` named as a switch target. Alongside those, a branch switch
whose target cannot be resolved statically — `git checkout -` — makes the branch *unknown*
rather than unchanged, and a commit or push that follows it is refused.

### Why it is worth building

Round 1 closed the parsing defect and left nine holes it had inherited. Eight of them are
these. All are live on the branch today:

```
GIT_EDITOR=true git commit -m "m"       on main        -> ALLOWED
sudo git push origin main               on feat/topic  -> ALLOWED
`git push origin main`                  on feat/topic  -> ALLOWED
>log git commit -m "m"                  on main        -> ALLOWED
GIT commit -m "m"                       on main        -> ALLOWED
git push -o ci.skip origin              on main        -> ALLOWED
git checkout refs/heads/main && git commit -m "m"      -> ALLOWED
git checkout - && git commit -m "m"                    -> ALLOWED
```

The first is the one that matters most: setting an environment variable before a git command
is ordinary practice, not evasion, and it turns the guard off completely.

**The design aims at the grammar, not at an adversary, and this is deliberate.** The
module's docstring says the guard exists to catch slips, and that one which blocks
legitimate work is worse than one which misses an exotic invocation. Skipping assignments
and redirections is not a heuristic — it is parsing the prefix a shell itself skips, and it
cannot produce a false positive. The wrapper list is the one pragmatic exception: incomplete
by construction, but its failure mode is missing a wrapper nobody listed, never refusing
something legitimate. Anyone determined to evade a local hook can edit the hook; raising
strictness past the grammar buys nothing against that and costs false positives.

### Inputs and outputs

Unchanged at the boundary. `guard_git.py` still reads a JSON payload on stdin
(`tool_input.command`, `cwd`) and answers by exit code — `0` allows, `2` blocks and prints
the reason to stderr — and `violation(command: str, branch: str) -> str` is still the pure
function the tests drive. What changes is which invocations that function recognises, and
one new shape of refusal message: a command whose branch could not be determined.

### How it connects to the rest of the repo

- `.claude/hooks/guard_git.py` is the only module whose behaviour changes.
- `.claude/hooks/plan_state.py` and `.claude/hooks/stop_gate.py` do **not** change. Round 1
  said the same and then changed `stop_gate.py` by one line when its own tests found a
  defect; that was recorded as drift and accepted by the user as a step 1 decision. The same
  rule applies here: if this round's tests find a defect in a module this section says is
  untouched, it goes back to the user as a concept decision rather than being absorbed.
- `tests/test_guard_git.py` grows. The other two test files do not.
- `STRUCTURE.md`: the `guard_git.py` prose and, if step 2 changes a public signature, its
  table.
- `.claude/settings.json` is untouched, so the hook's registration is unchanged.

### Explicitly out of scope

- **Nested interpreters.** `bash -c "git commit -m x"`, `ssh host git commit`,
  `xargs git commit`. The outer command is a program that takes a command as *data*;
  following it means parsing arbitrary nested shells, which is where a guard for slips
  turns into a sandbox.
- **Evaluating command substitution.** Backticks and `$( )` are stripped where they wrap an
  invocation so the invocation inside is seen. What the substitution would evaluate to, and
  substitutions used as an argument value such as `git push origin $(cat branch.txt)`, stay
  out.
- **Wrappers beyond the list.** It is `sudo`, `env`, `time`, `nohup`, `doas` and nothing
  else. Extending it later is a one-line change and does not need a round.
- **Git aliases.** Still out, for round 1's reason: resolving them means reading git config.
- **Making `PROTECTED` configurable**, and protecting anything other than `main`.
- **The ninth hole from round 1 is not here.** `git push origin HEAD` when `HEAD` is
  detached, and similar cases where the guard's own `current_branch` returns `""`, are a
  different question about what the guard does when it cannot name the current branch at
  all.

### Acceptance criteria

> Lettered `B` rather than `A` so that step 6 and `/create-pr` can tell them apart from
> round 1's `A1`-`A9`, which are re-checked here as a regression pass rather than restated.

| # | The finished feature... |
|---|---|
| B1 | Refuses a commit or push preceded only by variable assignments — `GIT_EDITOR=true git commit -m "m"` on `main`. |
| B2 | Refuses one preceded by a redirection — `>log git commit -m "m"` on `main`. |
| B3 | Refuses one wrapped in backticks or `$( )` — `` `git push origin main` `` from any branch. |
| B4 | Refuses one invoked under a listed wrapper — `sudo git push origin main`, and the same for `env`, `time`, `nohup` and `doas`. |
| B5 | Matches the executable without regard to case — `GIT commit -m "m"` on `main`. |
| B6 | Recognises the three unknown refspec shapes: `git push -o ci.skip origin` on `main`, `git push origin @` on `main`, and `git checkout refs/heads/main && git commit` from a feature branch. |
| B7 | Treats an unresolvable switch as making the branch unknown, so `git checkout - && git commit` is refused from any branch, with a message saying the branch could not be determined rather than the message for committing to `main`. |
| B8 | Introduces no false positives: `echo git commit`, `grep push log.txt`, `git log --grep=commit`, `sudo apt install git` and `time ls` are all still allowed, demonstrated by re-running round 1's differential across both branches rather than by citing test names. |

### Open questions

None. Two were raised and settled during this step:

- *How far should the guard go in finding the command name?* Shell grammar — assignments,
  redirections, substitution delimiters, case — plus a short, explicitly incomplete list of
  wrapper programs. Not recursion into any unknown leading command, which would refuse
  `echo git commit`.
- *What happens when a switch target cannot be resolved?* The branch becomes unknown and a
  following commit or push is refused wherever it runs. `-` may be `main` and the guard
  cannot tell; the cost is one retry with an explanatory message, against an unpicked commit
  on `main`.

---

## 2. Plan

> Written in step 2. Concrete enough that step 3 is transcription, not invention.

### Approach

One paragraph on the chosen approach, and one on what was rejected and why.

### Modules

| Path | New or changed | Purpose |
|---|---|---|

### Public API

> Every public class and function, with its full signature as it will be written.
> `Covers` links back to the acceptance criteria above.

| Signature | Module | Purpose | Covers |
|---|---|---|---|

### Implementation guide

Ordered. Each entry small enough to finish and check.

1.
2.

### Test intents

> High-level: what a test must prove, not how it is written. Step 5 turns each of these
> into concrete cases, including the edge cases.

| # | Must prove | Covers |
|---|---|---|
| T1 | | |

### Risks

What could make this harder than it looks, and the plan if it does.

---

## 3. Implementation notes

> Written in step 3. Only deviations from the plan above, each with its reason. "Built as
> planned" is a complete and good entry.

---

## 4. Verification log

> Written in step 4: the static half. Command output, not a summary of it.

| Check | Result |
|---|---|
| `ruff check .` | |
| `ruff format --check .` | |
| `mypy` | |
| Plan completeness | every signature in the Public API table exists as written |
| `STRUCTURE.md` | in sync |
| `python -m <package>.<module>` | |

---

## 5. Test log

> Written in step 5: the dynamic half.

| Intent | Test names | Result |
|---|---|---|

Edge cases considered and deliberately skipped, with reasons:

---

## 6. Concept check

> Written in step 6, against section 1 — not against section 2. The question is whether
> the thing built is the thing agreed, not whether it matches the plan.

| # | Criterion | Met | Evidence |
|---|---|---|---|
| A1 | | | |

Drift found, and what was done about it:

### Earlier rounds still hold

> Later rounds only. Re-check every acceptance criterion from every earlier round in this
> folder: this round changed code they depend on, and their tests passing is necessary but
> not sufficient — a criterion can be satisfied by tests that no longer describe what the
> feature does.

| Round | # | Criterion | Still met | Evidence |
|---|---|---|---|---|

---

## 7. Ship log

| Field | Value |
|---|---|
| Commits | |
| Pushed to | |

---

## 8. Recommendations

> Written in step 8. Follow-up work this change makes possible or desirable. Not bugs —
> a bug found here goes back to step 3 before shipping.

| # | Recommendation | Why it helps | Effort | Decision |
|---|---|---|---|---|
| R1 | | | | |

Decisions: `deferred`, `rejected`, or `next round` — a new numbered file in this folder,
taken back through steps 1 to 7 on the same branch.

---

## 9. Pull request

| Field | Value |
|---|---|
| URL | |
| Opened as | ready for review |

---

## 10. Review log

> Written in step 10, one row per review thread. The record of how the pull request got
> from opened to merged — the part nobody can reconstruct from the diff later.
>
> Quiet check-ins are not recorded. Nineteen rows of "nothing had changed" is noise.

| Thread | Who asked for what | Outcome |
|---|---|---|

Outcomes: `fixed and pushed`, `replied, left open`, `round N`, or — for a bot finding —
`dismissed: <reason>`. Every dismissal is also reported to the user, never only recorded here.

### Outcome

| Field | Value |
|---|---|
| Merged or closed | |
| Merge commit | |
| Instructed by | who said to merge, and where |
| Bot findings dismissed | each one, with its reason |
