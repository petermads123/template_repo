# Model and effort per step

Every skill pins a model and effort in its frontmatter, so a step runs on what it needs
rather than on whatever the session happens to be set to. A skill's override lasts the
turn, which is exactly why steps 3 to 7 run as **subagents**: chained in one turn they
would all run on the first skill's model. `/build` passes each step's model to its
subagent; effort cannot be passed, so the subagent reads it from its skill file as intent.

| Step | Model | Effort | Why |
|---|---|---|---|
| `/fix` diagnosis | `opus` | `high` | A wrong root cause costs the whole build and ships a fix that does not fix |
| 1 Conceptualize | `opus` | `high` | Shaping the concept is the most expensive thing to get wrong |
| 2 Plan | `opus` | `high` | The design fork, and signatures step 4 checks literally |
| 3–7 `/build` | `opus` | `medium` | Orchestration: reads the marker, spawns, relays, halts |
| 3 Implement | `sonnet` | `high` | Transcribing a plan that has already done the thinking |
| 4 Verify | `sonnet` | `high` | Mechanical checks plus classifying each mismatch |
| 5 Test | `sonnet` | `high` | Edge cases and the bugs they expose |
| 6 Concept check | `sonnet` | `high` | A different model from the one that wrote the plan |
| 7 Ship | `sonnet` | `high` | Gates on the whole round, diff review; procedural |
| 8 Recommend | `opus` | `high` | Judging whether anything is critical enough to hold the pull request |
| 9 Pull request | `sonnet` | `high` | Verification and writing, both well-specified |
| 10 Review | `sonnet` | `medium` | Most check-ins find nothing; the judgment is fix-or-new-round |

`/feature` carries step 1's settings because it opens step 1 in the same turn, and so does
`/fix`, whose diagnosis is the same judgment made one step earlier. For the same reason
`/recommend`, opened by `/build`, and the `/create-pr` it hands on to run on the build's
turn model; their rows apply when the user invokes them directly.
`/small-change` runs `opus` at `medium`: bypassing the pipeline is a judgment call made
without any of its safety nets, so the step that decides whether a change really is small
gets the clever model.

Every Sonnet step runs at `high`, and `max` (the top level) is unused. Aliases rather than pinned IDs, so
a newer Opus or Sonnet is picked up without editing a dozen files. `ultracode` is a
session-level effort setting and not valid in frontmatter, where the levels are `low`,
`medium`, `high`, `xhigh` and `max`.
