# Development notes

Development-side open questions and things to fix later: what the code does not do yet, a
question nobody can answer yet, an idea that fell short of a recommendation. Not a design
document and not a changelog.

**Adding an entry:** a heading, the date and the branch/round it came from, the item itself,
and its next step or where it is configured. **Resolving an entry:** the change that
resolves it deletes it — this file only ever shows what is still open. Step 8 of every round
ends by cleaning it: entries the branch resolved are removed, duplicates are merged, and
only open items are left. Before an entry is deleted or renamed, anything that points at it
by heading is updated in the same change.

## `fix/guard-git-shell-lexing`, round 1 (2026-10-03)

- **No bash oracle in the guard's suite.** The round's differential compared the new guard with the old one, so a hole both share was invisible (that is how R1 and R2 of this round's section 8 survived). A permanent test that runs real bash with `git` shadowed over `git commit`/`git push origin main` placed in every syntactic position, skipped where bash is absent, would catch the next one. Next step: a test-only round on `tests/test_guard_git.py`. Round 2 confirmed it twice: both step-6 send-backs were found only by a differential that wrapped corpus commands in `"$( )"`, which lived in the scratchpad and ran at step 6, not step 5.
- **Commits hidden behind a program's string argument** — `bash -c "git commit"`, `sh -c`, `eval`, aliases and functions — and wrappers missing from `WRAPPERS` (`xargs`, `timeout`, `nice`, `command`, `exec`) are still allowed on `main`. Out of scope by design (the docstring's slips-not-adversaries trade-off); revisit if one shows up in practice.
- **Spelled-out subcommands** behind an unmodelled construct (`git $'\x63ommit'`, `git co""mmit`) evade the raw-text search. Adversarial rather than a slip; pinned as a recorded miss in `tests/test_guard_git.py`.

## `fix/guard-git-shell-lexing`, round 2 (2026-10-03)

- **The substitution placeholder is read as "could be anything" only by `switch_target`.** A command name, git subcommand or push destination made by a substitution reads as a harmless word: `"$(which git)" commit -m x` and `git "$(echo commit)" -m x` on `main` are allowed (evasive spellings, the same class as `git co""mmit`), and `git push origin "$(git branch --show-current)"` on `main` is allowed — the idiom an agent would write by accident, backstopped today only by the remote's protection of `main`. Next step: treat the placeholder as unknown in `git_subcommand`/`push_targets_main`, keeping the same push from a branch allowed.
- **Nesting past 30 levels off `main` is not judged**, and the unmodelled/budget fallback plays safe only when the *current* branch is `main`, so a `git checkout main` buried that deep is missed from a branch. Adversarial input only; pinned in the suite.
- **`RISKY_SUBCOMMANDS` is `commit` and `push` only.** `git merge`, `cherry-pick`, `revert` and `am` on `main` also write commits to local `main` and are allowed. A scope question for the user, not a lexing defect.
