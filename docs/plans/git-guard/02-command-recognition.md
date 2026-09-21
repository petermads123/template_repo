# Git guard: recognising the command

<!-- claude-plan step=8 status=active -->

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
| 2 | Plan | `/plan` | done |
| 3 | Implement | `/implement` | done |
| 4 | Verify | `/verify` | done |
| 5 | Test | `/test` | done |
| 6 | Concept check | `/concept-check` | done |
| 7 | Ship | `/ship` | done |
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

### Approach

A shell finds a command's name by skipping a prefix: variable assignments and redirections.
`git_subcommand` currently assumes that prefix is empty and reads `tokens[0]`. The change is
to give it a private helper that walks the prefix the way a shell does and returns the index
where the command name actually starts — then the same function, with the same signature,
asks its question at the right position. Case folding and backtick stripping happen at that
position; the wrapper list is one more kind of prefix to step over.

The refspec work is separate and mechanical: one normaliser, `_branch_name`, that reduces a
ref to the branch it names — dropping a leading `+`, taking the destination half of a
`src:dst` pair, stripping `refs/heads/`, and reading `@` as `HEAD` — used by both
`push_targets_main` and `switch_target` so the two cannot drift apart. `push_targets_main`
also stops filtering its arguments and walks them instead, so an option's value is never
mistaken for the remote.

For the unresolvable switch, `switch_target` gains a third answer. It already returns a
branch name or `""` for "no switch"; it now also returns `UNRESOLVED` for a target only the
running shell could resolve — `-` and `@{-1}`. `violation` carries that forward like any
other effective branch and refuses a risky subcommand that meets it.

**No public signature changes.** All four public functions keep the parameter lists and
return types round 1 documented; what changes is which invocations they recognise. That
keeps step 4's literal check green without special pleading and means `STRUCTURE.md` needs
prose, not a new table.

Rejected — **scan the segment for any `git` token**. It satisfies B1 to B5 in about four
lines, and refuses `echo git commit`, `grep push log.txt` and `git log --grep=commit`. B8
exists to make that trade explicit rather than discovering it in review.

Rejected — **resolve `-` by reading `.git/HEAD`'s reflog**. It would turn B7 from a refusal
into a correct answer, but it makes a pure function do I/O, and it is wrong the moment the
command runs in a different repository than the one the hook is looking at.

### Modules

| Path | New or changed | Purpose |
|---|---|---|
| `.claude/hooks/guard_git.py` | changed | Prefix-aware command recognition, ref normalisation, and the unresolved-branch policy. |
| `STRUCTURE.md` | changed | The `guard_git.py` prose. Its signature table does not move. |
| `tests/test_guard_git.py` | changed in step 5 | The B-criteria cases and the differential. |
| `.claude/hooks/plan_state.py`, `.claude/hooks/stop_gate.py` | unchanged | Section 1 says so, and says what happens if that turns out to be wrong. |

### Public API

Every entry already exists and keeps its signature. Listed so step 4 has something to check
literally, with what changes behind each one.

| Signature | Module | Purpose | Covers |
|---|---|---|---|
| `git_subcommand(tokens: tuple[str, ...]) -> tuple[str, tuple[str, ...]]` | `guard_git` | Identify the git subcommand. Now finds the command name after the shell prefix, folds case, and strips backticks. | B1-B5 |
| `push_targets_main(args: tuple[str, ...], branch: str) -> bool` | `guard_git` | Whether a push would update `main`. Now walks its arguments so an option value is not read as the remote, and normalises every refspec. | B6 |
| `switch_target(subcommand: str, args: tuple[str, ...]) -> str` | `guard_git` | The branch a `checkout`/`switch` moves to, `""` for none, or `UNRESOLVED` when only the running shell could say. | B6, B7 |
| `violation(command: str, branch: str) -> str` | `guard_git` | The reason to refuse, or `""`. Now refuses a risky subcommand whose effective branch is `UNRESOLVED`, with its own message. | B1-B7 |
| `Segment`, `segments`, `main` | `guard_git` | Unchanged in signature and behaviour. | — |

`UNRESOLVED` is a new module constant, the sentinel `switch_target` returns. It is named in
`switch_target`'s row in `STRUCTURE.md` rather than given a row of its own, the way
`GATE_FROM_STEP` is treated in `plan_state`.

### Implementation guide

1. Add the constants: `UNRESOLVED`; an `ASSIGNMENT` pattern for `NAME=value`;
   `REDIRECTION_STARTS` for the tokens `shlex` produces for `>`, `<`, `>>` and `>&`;
   `WRAPPERS` = `sudo`, `env`, `time`, `nohup`, `doas`; `PUSH_OPTIONS_WITH_VALUE` = `-o`,
   `--push-option`, `--repo`, `--receive-pack`, `--exec`.
2. `_strip_substitution(token)`: remove surrounding backticks so `` `git `` reads as `git`.
   `$( )` needs nothing — `(` is already a separator, so the invocation inside already
   lands in its own segment and is already refused today.
3. `_command_index(tokens)`: walk the prefix and return where the command name starts.
   Skip an assignment; skip a redirection operator *and its operand*; skip a bare file
   descriptor digit that precedes one, since `2>&1` lexes as `2`, `>&`, `1`; skip a wrapper
   and any options directly following it. Return `len(tokens)` when the prefix is all there
   is.
4. `git_subcommand`: start from `_command_index`, compare
   `Path(_strip_substitution(token)).name.lower()` against `{"git", "git.exe"}`, and scan
   for the subcommand from there as it does now.
5. `_branch_name(ref)`: strip a leading `+`, take the part after the last `:`, strip a
   `refs/heads/` prefix, and map `@` to `HEAD`.
6. `push_targets_main`: walk `args` with an index instead of filtering, skipping each
   `PUSH_OPTIONS_WITH_VALUE` together with its value, so the first positional really is the
   remote. Compare every refspec through `_branch_name`.
7. `switch_target`: return `UNRESOLVED` for `-` and `@{-1}`; pass every other target
   through `_branch_name`.
8. `violation`: when the effective branch is `UNRESOLVED` and the subcommand is `commit` or
   `push`, refuse with a message that says the branch could not be determined and names the
   switch that caused it — not the message for committing to `main`, which would be a lie.
9. `STRUCTURE.md`: rewrite the `guard_git.py` prose for the prefix rule, the wrapper list
   and its documented incompleteness, and the unresolved-branch policy.

### Test intents

| # | Must prove | Covers |
|---|---|---|
| U1 | A commit or push hidden behind one or more variable assignments is found. | B1 |
| U2 | One hidden behind a redirection is found, including the `2>&1` form where the file descriptor lexes as its own token. | B2 |
| U3 | One wrapped in backticks is found; and `$( )` still refuses, having always done so. | B3 |
| U4 | One under each listed wrapper is found, and a wrapper with an option value that hides the command is a documented miss rather than a surprise. | B4 |
| U5 | The executable is matched case-insensitively, in every spelling `git_subcommand` already accepts. | B5 |
| U6 | Each unknown refspec shape reaches `main`: an option value not read as the remote, `@` as `HEAD`, `refs/heads/main` as a switch target. | B6 |
| U7 | An unresolvable switch refuses a following commit or push from any branch, and the reason names the branch as undetermined rather than as `main`. | B7 |
| U8 | The non-invocations stay allowed: `echo git commit`, `grep push log.txt`, `git log --grep=commit`, `sudo apt install git`, `time ls`, and a commit message that contains the word `sudo`. | B8 |
| U9 | Round 1's differential re-run across both branches shows no command that round 1 refused and this round allows. | B8, and round 1's A5 as regression |

### Risks

**Every criterion but one pushes toward strictness.** Seven of eight make the guard refuse
more, and the failure this module's own docstring calls worse is refusing legitimate work.
U8 and U9 are the control, and U9 is the one that cannot be satisfied by writing agreeable
tests: it compares this module against round 1's across a generated corpus.

**The wrapper prefix is where a false positive would come from.** Skipping options after a
wrapper without knowing which take values means `sudo -u me git push` lands on `me` and is
allowed — a miss, which is safe. The unsafe mirror would be skipping too much and landing on
a `git` that is an argument rather than a command. The rule only ever skips tokens starting
with `-`, so it cannot walk past a bare word.

**`2>&1` and friends lex unusually.** `shlex` with `punctuation_chars` splits `2>&1` into
three tokens. The guide handles the shape seen in the probe; other descriptor forms may lex
differently and step 5 should try them rather than assume.

**Round 1's 221 tests are the regression surface.** A stricter guard may legitimately move
some of them. Each move is a decision to record in section 3, not a number to restore.

---

## 3. Implementation notes

**Built as planned, with one refinement the plan did not anticipate.**

`_branch_name` also strips backticks. The plan gave `_strip_substitution` a single job —
letting the command name be found inside `` `git push ...` `` — and that worked: the
invocation was recognised. The refspec then was not. A closing backtick rides on the *last*
token of a substitution, so `` `git push origin main` `` yields the refspec ``main` ``,
which is not `main`, and the command was allowed. Stripping the delimiter is part of reading
a ref, not only part of reading a command name, so `_branch_name` does it too.

It is worth naming why the probe caught this and the criterion would not have: B3 says the
command is *found*, and it was. What failed was one step later. A test that asserts only on
the verdict would have caught it; a test that asserted `git_subcommand` returns `push` would
have passed while the guard still let the push through — the same shape of mistake round 1
made when its probe read an accidental allow as a correct one.

**`$( )` needed nothing at all.** The plan already said so, and the probe confirmed it: `(`
is a separator from round 1, so `$(git push origin main)` already splits the invocation into
its own segment and already refused. Only backticks were open. Recording it because the
concept lists `$( )` in B3, and a reader comparing the criterion to the diff would otherwise
look for a change that was never needed.

**`_redirected` had to move with the command name.** It walked global options from index 1,
which assumed `tokens[0]` is git. With a prefix in front, it now starts from
`_command_index(tokens) + 1`. Not a behaviour change anyone asked for — a consequence of
the one this round did.

**No public signature changed**, as the plan said. All seven entries in round 1's
`STRUCTURE.md` table stand, and the new names — `_strip_substitution`, `_branch_name`,
`_command_index` — are private.

---

## 4. Verification log

| Check | Result |
|---|---|
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `34 files already formatted` |
| `mypy` | `Success: no issues found in 11 source files` |
| `pytest` | `221 passed` — round 1's suite, unchanged and unbroken. Round 2's cases are step 5. |
| Plan completeness | all seven signatures exist exactly as round 1 wrote them (table below) |
| `STRUCTURE.md` | in sync; auditor run, six edits applied |
| Hook run standalone | refuses a commit hidden behind an assignment and a push behind `sudo`, allows `echo git commit` |

### Plan completeness

Section 2 promised no public signature would change, which makes this check a check that
nothing moved. Read back with `inspect`, not by eye:

| Planned | Found | Verdict |
|---|---|---|
| `Segment` — frozen, `tokens: tuple[str, ...]`, `separator: str` | identical | match |
| `segments(command: str) -> list[Segment] \| None` | identical | match |
| `git_subcommand(tokens: tuple[str, ...]) -> tuple[str, tuple[str, ...]]` | identical | match |
| `push_targets_main(args: tuple[str, ...], branch: str) -> bool` | identical | match |
| `switch_target(subcommand: str, args: tuple[str, ...]) -> str` | identical | match |
| `violation(command: str, branch: str) -> str` | identical | match |
| `main() -> None` | identical | match |

Public names defined in the module: exactly those seven, nothing unplanned. The three
helpers this round added — `_strip_substitution`, `_branch_name`, `_command_index` — are
private and absent from `STRUCTURE.md`, which the auditor confirmed.

### STRUCTURE.md audit

Six edits, and the first was a real miss rather than a polish:

1. **`switch_target`'s row documented two return values and the function now has three.**
   A reader would have taken the sentinel `UNRESOLVED` for a branch named `?`. Section 2 had
   explicitly decided to document it in that row, and the implementation did not go back and
   do it — exactly the signature drift the stop gate cannot see and the auditor exists for.
2. A third of the round's behaviour was undocumented: the prose covered the shell prefix,
   the wrappers and the unresolved policy, and said nothing about the refspec work. A reader
   asking whether `git push -o ci.skip origin` is caught would have concluded no.
3. The tests entry said "the defect that prompted the round" when there are now two rounds.
4. A clause describing a `segments` test sat inside the `switch_target` sentence, and the
   `switch_target` list omitted the option-left-without-a-value case.
5. The `docs/plans/` tree illustrated the layout with a `csv-export` feature that has never
   existed here; it now shows the two rounds that do.

Applying edit 4 collided with edit 3's rewrap and briefly left the `#` clause in the file
twice. Caught by re-reading the region rather than trusting the replacement count, and
fixed before the step closed.

### Standalone run

The hook exercised the way it runs — a JSON payload on stdin, against a throwaway
repository checked out on `main`:

```
GIT_EDITOR=true git commit -m "m"        -> exit 2, "this would commit to `main`"
sudo git push origin main                -> exit 2, "this would push to `main`"
echo git commit                          -> exit 0
git checkout -b feat/x && git commit     -> exit 0
```

The first two are B1 and B4 through the real entry point. The third is B8: the case that
would fail if this round had reached for the easy implementation.

---

## 5. Test log

291 tests, all passing. 70 are new in this round; the other 221 are round 1's, unchanged and
unbroken — not one had to be adjusted for the stricter guard, which is the first evidence
for B8.

| Intent | Test names | Result |
|---|---|---|
| U1 — assignment prefix | `test_violation_finds_a_commit_behind_an_assignment` (4 cases, including an empty value and a value containing `;`), `test_violation_finds_a_push_behind_an_assignment`, `test_violation_allows_an_assignment_prefixing_something_harmless` | pass |
| U2 — redirection prefix | `test_violation_finds_a_commit_behind_a_redirection` (5 cases: `>log`, `> log`, `>>log`, `2>&1`, `<in`), `test_violation_finds_a_commit_behind_both_prefixes` | pass |
| U3 — substitution | `test_violation_finds_a_push_inside_backticks`, `test_violation_finds_a_commit_inside_backticks`, `test_violation_finds_a_push_inside_a_dollar_substitution` | pass |
| U4 — wrappers | `test_violation_finds_a_push_under_each_wrapper` and `..._a_commit_under_each_wrapper` (5 wrappers each), `test_violation_steps_over_a_wrappers_own_flags`, `test_violation_misses_a_command_behind_a_wrapper_option_value`, `test_violation_allows_a_wrapper_running_something_else` | pass |
| U5 — spelling | `test_violation_matches_the_executable_without_regard_to_case` (5 spellings) | pass |
| U6 — refspecs | `test_violation_does_not_read_a_push_option_value_as_the_remote` (5 options), `test_push_targets_main_skips_an_option_value`, `test_push_targets_main_follows_both_spellings_of_head`, `test_violation_refuses_a_push_to_the_head_alias`, `test_switch_target_reduces_a_ref_to_its_branch` (4 ref shapes), `test_violation_refuses_a_commit_after_switching_to_main_by_full_ref` | pass |
| U7 — unresolvable switch | `test_switch_target_reports_an_unresolvable_target` (2 targets x 2 subcommands), `test_violation_refuses_a_commit_after_an_unresolvable_switch` (both branches), `test_violation_refuses_a_push_after_an_unresolvable_switch`, `test_violation_says_the_branch_is_undetermined_rather_than_main`, `test_violation_allows_a_harmless_command_after_an_unresolvable_switch`, `test_violation_does_not_carry_an_unresolvable_switch_across_a_weak_join` | pass |
| U8 — no false positives | `test_violation_allows_what_is_not_a_git_invocation` (9 cases), `test_violation_allows_those_same_commands_on_main` (5 cases), `test_violation_allows_a_commit_message_naming_git_and_sudo` | pass |
| U9 — differential | Not a pytest test; see below | pass |

### U9, and why it is not a test

U9 compares this module against the previous revision of itself, which a test cannot do
without vendoring a copy that would then rot. It was run as a verification activity, the way
round 1 evidenced A5, in two passes:

| Corpus | Comparisons | Round 1 refused, round 2 allows | Round 1 allowed, round 2 refuses |
|---|---|---|---|
| Round 1's generated corpus, re-run | 1,512 | **0** | 0 |
| Round 2's shapes — every prefix, wrapper and wrapping crossed with eight cores | 878 | **0** | 152 |

The first pass returning zero in *both* columns is the point worth reading carefully: it
says this round changed nothing about the commands round 1 was built to judge. It also says
that corpus proves nothing about what this round added, which is why the second exists. Run
alone, the first would have been half a test wearing the costume of a whole one.

The 152 are the eight holes closed, multiplied out across prefixes and wrappings.

### One bug the probe found before the tests did

`` `git push origin main` `` found the command — the backtick was stripped from
`` `git `` — and then read the refspec as ``main` ``, which is not `main`, and allowed the
push. Recorded in section 3. It is the same shape of error round 1 made: a check that stops
at "the command was recognised" passes while the command still gets through.

### Edge cases considered and deliberately skipped

- **A wrapper option that takes a value.** `sudo -u me git push origin main` is allowed, and
  there is a test asserting it, named so the limit is legible. Only options are skipped
  after a wrapper, never a bare word, because skipping bare words is exactly how a scan
  walks onto a `git` that is an argument. Fixing it means knowing every wrapper's option
  grammar; the failure direction is a miss, not a false refusal.
- **Nested interpreters and substitution as a value.** Out of scope in section 1, unchanged.
- **Exotic file descriptor redirections.** `2>&1` is covered because the probe showed how it
  lexes. Forms like `{fd}>file` are not; they are bash-only and lex differently.
- **`git checkout -` resolved for real.** Reading the reflog would answer it correctly and
  would make a pure function do I/O against a repository that may not be the one the command
  runs in. Refusing is the honest answer.

---

## 6. Concept check

Audited against section 1, read before section 2 and before the diff.

| # | Criterion | Met | Evidence |
|---|---|---|---|
| B1 | A commit or push behind variable assignments | yes | `test_violation_finds_a_commit_behind_an_assignment`, 4 cases including an empty value and one containing `;`; and through the real entry point, `GIT_EDITOR=true git commit` exits 2 against a throwaway repo on `main`. |
| B2 | Behind a redirection | yes | `test_violation_finds_a_commit_behind_a_redirection`, 5 forms including `2>&1`, whose three-token lexing the probe established rather than assumed. |
| B3 | Wrapped in backticks or `$( )` | yes | `test_violation_finds_a_push_inside_backticks` and the two siblings. `$( )` needed no code: `(` was already a separator, so it already refused — recorded in section 3 so the diff and the criterion can be reconciled. |
| B4 | Under a listed wrapper | yes | `test_violation_finds_a_push_under_each_wrapper` and `..._a_commit_under_each_wrapper`, 5 wrappers each; `sudo git push origin main` exits 2 through the entry point. |
| B5 | Executable matched without regard to case | yes | `test_violation_matches_the_executable_without_regard_to_case`, 5 spellings including `/usr/bin/GIT`. |
| B6 | The three unknown refspec shapes | yes | `test_violation_does_not_read_a_push_option_value_as_the_remote` (5 options), `test_push_targets_main_follows_both_spellings_of_head`, `test_switch_target_reduces_a_ref_to_its_branch` (4 shapes). |
| B7 | Unresolvable switch makes the branch unknown | yes | `test_violation_refuses_a_commit_after_an_unresolvable_switch` on both branches, and `test_violation_says_the_branch_is_undetermined_rather_than_main`, which asserts the reason does *not* contain the `main` wording — the criterion asked for a distinct message, not just a refusal. |
| B8 | No false positives introduced | yes | 12 parametrised allow-cases, plus the differential: 2,390 comparisons against round 1's module across two corpora, zero commands that round 1 refused and this round allows. Round 1's 221 tests also pass unmodified, which is independent evidence — not one had to be adjusted for a stricter guard. |

### Earlier rounds still hold

Re-checked against the code as it stands now, not by reading round 1's test names. Round 1's
criteria were written against a module this round rewrote the recognition path of, so their
tests passing is necessary and not sufficient.

| Round | # | Criterion | Still met | Evidence |
|---|---|---|---|---|
| 1 | A1 | Punctuation in a commit message refused on `main` | yes | Re-run directly for `;`, `\|`, `&&` and a newline. |
| 1 | A2 | Switch away allowed, switch to `main` refused | yes | Re-run both directions. |
| 1 | A3 | A switch counts only across `&&` and newlines | yes | Re-run for `;`, `\|\|`, `&`, newline, and the `&&`-ending-a-line case. The round 2 addition that an *unresolvable* switch is distrusted does not weaken this: a resolvable switch across `&&` still carries. |
| 1 | A4 | Unreadable input refused on `main`, allowed elsewhere | yes | Re-run all three branches of the rule, including the message wording. |
| 1 | A5 | Nothing that was refused before is allowed now | yes | The differential, which is the same instrument A5 was evidenced with: 0 regressions. |
| 1 | A6 | Suite imports the three hooks, green under plain `pytest` | yes | 291 passed; collection still resolves through the `pythonpath` entry. |
| 1 | A7 | Every public function covered | yes | No public function was added or removed this round; the three new helpers are private. |
| 1 | A8 | Four checks green, `STRUCTURE.md` complete | yes | All four green; `structure_problems(".")` empty. |
| 1 | A9 | A placeholder path read as prose | yes | Re-run against a throwaway repo whose `STRUCTURE.md` names `src/<package>/module.py`: no problems reported. |

Nothing round 1 delivered was broken by this round.

### Things the criteria do not cover

**Out of scope, checked.** Nothing on section 1's exclusion list was built: no nested
interpreter is followed (`bash -c`, `ssh`, `xargs` are all still allowed), substitution is
not evaluated, the wrapper set is the five named and no more, git aliases are untouched,
`PROTECTED` is still hardcoded, and the ninth hole — `HEAD` when `current_branch` returns
`""` — is deliberately absent.

**Section 1's promise about the other two hooks held this time.** `plan_state.py` and
`stop_gate.py` are byte-identical to where round 1 left them. Round 1 made the same promise
and broke it; this round's section 1 said what would happen if that recurred, and it did not
arise.

**Surface** is unchanged: the same seven public names, no additions, three new private
helpers correctly absent from `STRUCTURE.md`.

**Structure.** The auditor found the one thing that mattered — `switch_target` gained a
third return value and its row documented two — plus the undocumented refspec behaviour and
three smaller staleness items. All applied.

### Drift found, and what was done about it

**None that changes the concept.** Section 1 was written, the work was built to it, and
every criterion is met without amendment. That is worth saying plainly rather than
manufacturing a finding: round 1 needed its concept amended mid-audit, and the difference
here is that section 1 named the wrapper list as incomplete *before* the work started
instead of discovering the limit afterwards.

One thing is recorded rather than resolved, and it is not drift: `sudo -u me git push` is
allowed, and a test asserts it. The concept said the wrapper list is incomplete by
construction; this is what that costs, made visible instead of left to be found.

---

## 7. Ship log

| Field | Value |
|---|---|
| Commits | 4 for this round, on top of round 1's 11 |
| Pushed to | `claude/setup-recommendations-qoyxhf` on `origin` |

| Commit | Subject |
|---|---|
| `f0b6c1e` | Write round 2's concept: recognising the command |
| `4c19c33` | Close step 1 of round 2: concept confirmed |
| *(steps 2-4)* | Round 2 steps 2-4: plan, implement and verify command recognition |
| *(step 5)* | Round 2 step 5: 70 tests, and a bug the probe found first |
| *(this one)* | Close round 2: concept check passes, ship the round |

The round was again committed step by step rather than in one commit here, for the reason
round 1 recorded: a user-level stop hook refuses to end a turn on an uncommitted tree, and
this session runs in an ephemeral container where an uncommitted tree is lost work.

Gates confirmed immediately before shipping: `ruff check .` clean, `ruff format --check .`
clean, `mypy` clean across 11 files, `pytest` 291 passed. Steps 1 to 6 all `done`, section 6
carrying no unmet row and no unmet row in the earlier-rounds table either.

**This repository is public.** The diff is hook source, tests, plan prose and one
`STRUCTURE.md` revision. No credentials, no paths outside the repo, nothing about the user
beyond the authorship already in the history.

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
