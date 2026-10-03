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

- **No bash oracle in the guard's suite.** The round's differential compared the new guard with the old one, so a hole both share was invisible (that is how R1 and R2 of this round's section 8 survived). A permanent test that runs real bash with `git` shadowed over `git commit`/`git push origin main` placed in every syntactic position, skipped where bash is absent, would catch the next one. Next step: a test-only round on `tests/test_guard_git.py`.
- **Commits hidden behind a program's string argument** — `bash -c "git commit"`, `sh -c`, `eval`, aliases and functions — and wrappers missing from `WRAPPERS` (`xargs`, `timeout`, `nice`, `command`, `exec`) are still allowed on `main`. Out of scope by design (the docstring's slips-not-adversaries trade-off); revisit if one shows up in practice.
- **Spelled-out subcommands** behind an unmodelled construct (`git $'\x63ommit'`, `git co""mmit`) evade the raw-text search. Adversarial rather than a slip; pinned as a recorded miss in `tests/test_guard_git.py`.
