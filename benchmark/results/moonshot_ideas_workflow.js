export const meta = {
  name: 'engram-moonshots',
  description: 'Generate + adversarially falsify bold ideas to make Engram UNIQUELY the best memory layer',
  phases: [
    { title: 'Ideate', detail: 'diverse-angle idea generators (opus)' },
    { title: 'Falsify', detail: 'adversarial judge: kill the weak, rank the strong' },
  ],
}

const ANGLES = [
  { key: 'provenance-superpower', hint: 'Exploit Engram\'s UNIQUE write-time trust signal (per-fact grounding score, status, contradiction count) that mem0/Zep/Letta do NOT have. Ideas that turn write-time provenance into a runtime advantage (provenance-conditioned retrieval/answering, calibrated-confidence answers, cite-or-abstain).' },
  { key: 'defensive-immune', hint: 'Memory as an immune system: actively resist poisoning (prompt-injection facts, gradual drift, contradiction floods), detect+quarantine+heal. A defensive moat nobody markets. (bench_poisoning_resistance.py + contradiction.py + anti_confab_gate exist.)' },
  { key: 'belief-revision', hint: 'Truth-maintenance / ATMS: when a fact is later falsified, automatically revise dependent facts & past answers (justified_memory R18 + lineage + supersede exist). "Memory that changes its mind when evidence changes."' },
  { key: 'self-improving', hint: 'Memory that learns its own retrieval/answering from OUTCOMES: log which recalled facts led to Correct vs Hallucinated answers (the C/H/O signal), learn a per-corpus reranker / seed-weighting (outcome_predict, skill ROI exist).' },
  { key: 'trust-as-product', hint: 'Differentiate via honesty/transparency (Engram\'s ethos): the only reproducible open multi-system memory benchmark; provenance/lineage exposed to the user; "memory you can audit". DX + trust as the moat vs self-reported competitor numbers.' },
  { key: 'absurd-scientific', hint: 'Two deliberately wild but scientifically-grounded moonshots (e.g. sleep-time dreaming that synthesizes adversarial hard-negatives to immunize the gate; or treating memory as a falsifiable belief system with Popperian severity scores per fact).' },
]

const IDEA_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['ideas'],
  properties: {
    ideas: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['title', 'what', 'why_unique', 'falsifiable_test', 'buildable_on', 'effort'],
        properties: {
          title: { type: 'string' },
          what: { type: 'string', description: 'the idea in 2-3 sentences' },
          why_unique: { type: 'string', description: 'why no competitor (mem0/Zep/Letta/Cognee/MemOS) can do this' },
          falsifiable_test: { type: 'string', description: 'the experiment that would prove or kill it' },
          buildable_on: { type: 'string', description: 'existing engram/ modules to build on' },
          effort: { type: 'string', enum: ['S', 'M', 'L'] },
        },
      },
    },
  },
}

phase('Ideate')
const ideas = (await parallel(ANGLES.map((a) => () =>
  agent(
    `You are an inventive memory-systems researcher. The project is Engram/HippoAgent (repo ` +
    `C:/Users/aurel/Code/HippoAgent), whose VERIFIED unique moat is a write-path anti-confabulation gate ` +
    `(grounding/entailment + contradiction detection) that NO competitor has; today's measured gap is the ` +
    `ANSWER step (retrieval surfaces the gold fact 80%@k8 but the answerer omits/fabricates). Generate 3-4 ` +
    `BOLD, FALSIFIABLE, buildable ideas to make Engram UNIQUELY the best, from this angle: ${a.hint}\n` +
    `Use Grep/Read on engram/ to ground each idea in real modules. Each idea: what, why-no-competitor-can, ` +
    `the falsifiable test, the engram/ modules to build on, effort. No vaporware; no "add an LLM" hand-waving.`,
    { label: `ideate:${a.key}`, phase: 'Ideate', schema: IDEA_SCHEMA, effort: 'high' }
  )
))).filter(Boolean).flatMap((r) => r.ideas || [])

log(`generated ${ideas.length} ideas`)

phase('Falsify')
const RANK_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['ranked'],
  properties: {
    ranked: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['title', 'verdict', 'uniqueness', 'impact', 'feasibility', 'rank', 'note'],
        properties: {
          title: { type: 'string' },
          verdict: { type: 'string', enum: ['build-now', 'promising', 'kill'] },
          uniqueness: { type: 'integer' }, impact: { type: 'integer' }, feasibility: { type: 'integer' },
          rank: { type: 'integer' }, note: { type: 'string', description: 'the adversarial critique' },
        },
      },
    },
  },
}
const ranked = await agent(
  'You are a SKEPTICAL CTO. Here are moonshot ideas for Engram. KILL the ones that are vaporware, not ' +
  'actually unique (a competitor could copy in a week), or not falsifiable. RANK the survivors by ' +
  'uniqueness(1-5) x impact(1-5) x feasibility(1-5). Mark build-now / promising / kill. Be ruthless; the ' +
  'goal is the 2-3 ideas that genuinely make Engram best on a DEFENSIBLE axis.\n\nIDEAS:\n' +
  JSON.stringify(ideas, null, 1),
  { label: 'falsify', phase: 'Falsify', schema: RANK_SCHEMA, effort: 'high' }
)

return { ideas, ranked }
