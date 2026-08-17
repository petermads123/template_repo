export const meta = {
  name: 'implement-feature',
  description: 'Design a feature three ways, pick the best, implement it, then adversarially verify',
  whenToUse: 'Substantial work with a genuine design fork: several modules, a public API, or an approach that is not obvious. Not for adding a third function to an existing module.',
  phases: [
    { title: 'Survey', detail: 'read STRUCTURE.md and the touched modules' },
    { title: 'Design', detail: 'three independent approaches' },
    { title: 'Judge', detail: 'score them against the repo conventions' },
    { title: 'Verify', detail: 'adversarial review of the chosen design' },
  ],
}

const TASK = typeof args === 'string' ? args : JSON.stringify(args ?? 'unspecified task')

const CONVENTIONS = `
Repo conventions (from .claude/rules/python.md):
- Ruff and mypy must pass; config lives in pyproject.toml.
- Google-convention docstrings, full type annotations including -> None.
- Every module except __init__.py, tests/** and conftest.py defines
  main() -> None as a printed showcase, plus an if __name__ == "__main__" guard.
- Every public function gets tests in tests/test_<module>.py covering empty inputs,
  boundaries, numbers, optionals, text/unicode, purity, idempotency and Raises branches.
- STRUCTURE.md must be updated in the same change as any module or signature change.
`

phase('Survey')
const survey = await agent(
  `Read STRUCTURE.md and the package source in this repo. For the task below, report:
   (a) which existing modules are relevant and what they currently do,
   (b) where the new code most naturally belongs and why,
   (c) any existing function that already does part of this and should be reused.
   Be concrete: name files and functions. Do not propose a design yet.

   TASK: ${TASK}`,
  { label: 'survey', phase: 'Survey' },
)

const APPROACHES = [
  { key: 'minimal', angle: 'the smallest change that fully solves it — reuse aggressively, add as little surface as possible' },
  { key: 'structural', angle: 'the cleanest long-term structure — willing to add a module or refactor an existing one if it pays off' },
  { key: 'defensive', angle: 'hardest to misuse — explicit errors, narrow types, awkward states made unrepresentable' },
]

const DESIGN_SCHEMA = {
  type: 'object',
  required: ['summary', 'files', 'publicApi', 'tradeoffs', 'risks'],
  properties: {
    summary: { type: 'string', description: 'The approach in 3-4 sentences' },
    files: {
      type: 'array',
      items: {
        type: 'object',
        required: ['path', 'change'],
        properties: {
          path: { type: 'string' },
          change: { type: 'string', description: 'new | modified, and what changes' },
        },
      },
    },
    publicApi: {
      type: 'array',
      description: 'Full signatures of every new or changed public name',
      items: { type: 'string' },
    },
    tradeoffs: { type: 'string' },
    risks: { type: 'array', items: { type: 'string' } },
  },
}

phase('Design')
const designs = (
  await parallel(
    APPROACHES.map((a) => () =>
      agent(
        `Design an implementation for the task below, from this angle: ${a.angle}.

         Commit to the angle even where another would be more balanced — a later stage
         compares them, and a design that hedges is useless for that comparison.

         ${CONVENTIONS}

         SURVEY OF THE EXISTING CODE:
         ${survey}

         TASK: ${TASK}`,
        { label: `design:${a.key}`, phase: 'Design', schema: DESIGN_SCHEMA },
      ).then((d) => (d ? { ...d, key: a.key } : null)),
    ),
  )
).filter(Boolean)

if (designs.length === 0) {
  return { error: 'All design agents failed. Nothing to judge.' }
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['ranking', 'winner', 'reasoning', 'graftFromLosers'],
  properties: {
    ranking: { type: 'array', items: { type: 'string' }, description: 'Approach keys, best first' },
    winner: { type: 'string' },
    reasoning: { type: 'string' },
    graftFromLosers: {
      type: 'array',
      description: 'Specific good ideas from the non-winning designs worth folding in',
      items: { type: 'string' },
    },
  },
}

phase('Judge')
const verdict = await agent(
  `Score these designs against the repo conventions and pick a winner.

   Judge on: correctness, how well it fits the existing code, testability, and how hard it
   is to misuse. Ignore which one sounds most impressive. If two are close, prefer the one
   that adds less public surface.

   ${CONVENTIONS}

   DESIGNS:
   ${JSON.stringify(designs, null, 2)}

   TASK: ${TASK}`,
  { label: 'judge', phase: 'Judge', schema: VERDICT_SCHEMA },
)

if (!verdict) {
  return { survey, designs, error: 'Judging failed. Designs are returned unranked.' }
}

const winner = designs.find((d) => d.key === verdict.winner) ?? designs[0]

phase('Verify')
const LENSES = [
  'correctness — will this actually produce right answers, including at the boundaries?',
  'conventions — does it satisfy every rule in .claude/rules/python.md, main() and tests included?',
  'integration — does it fit the existing modules, or does it duplicate or contradict them?',
]

const CRITIQUE_SCHEMA = {
  type: 'object',
  required: ['blocking', 'concerns'],
  properties: {
    blocking: {
      type: 'array',
      description: 'Problems that must be fixed before implementing. Empty if none.',
      items: {
        type: 'object',
        required: ['problem', 'fix'],
        properties: { problem: { type: 'string' }, fix: { type: 'string' } },
      },
    },
    concerns: { type: 'array', items: { type: 'string' } },
  },
}

const critiques = (
  await parallel(
    LENSES.map((lens, i) => () =>
      agent(
        `Try to find what is wrong with this design, through one lens: ${lens}

         Be adversarial. Read the actual repo source to check your claims — do not object to
         something the code already handles. Report only problems you can point at
         concretely. An empty blocking list is the correct answer for a sound design.

         ${CONVENTIONS}

         DESIGN:
         ${JSON.stringify(winner, null, 2)}

         TASK: ${TASK}`,
        { label: `verify:${i}`, phase: 'Verify', schema: CRITIQUE_SCHEMA },
      ),
    ),
  )
).filter(Boolean)

const blocking = critiques.flatMap((c) => c.blocking ?? [])
const concerns = critiques.flatMap((c) => c.concerns ?? [])

log(`Winner: ${winner.key}. ${blocking.length} blocking issue(s), ${concerns.length} concern(s).`)

return {
  task: TASK,
  survey,
  chosen: winner,
  ranking: verdict.ranking,
  reasoning: verdict.reasoning,
  graftFromLosers: verdict.graftFromLosers,
  blocking,
  concerns,
  rejected: designs.filter((d) => d.key !== winner.key),
}
