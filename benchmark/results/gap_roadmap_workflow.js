export const meta = {
  name: 'gap-to-number-one-roadmap',
  description: 'Synthesize all recon/audit findings into ONE ranked execution roadmap to "best real memory"',
  phases: [{ title: 'Synthesize', detail: 'read the committed findings, produce the ranked plan' }],
}

const SCHEMA = {
  type: 'object', additionalProperties: false, required: ['done', 'roadmap', 'verdict'],
  properties: {
    done: { type: 'array', items: { type: 'string' }, description: 'what is already shipped/proven (do not redo)' },
    roadmap: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['item', 'category', 'priority', 'effort', 'impact', 'where'],
        properties: {
          item: { type: 'string' },
          category: { type: 'string', enum: ['differentiator', 'benchmark', 'retrieval', 'durability', 'perf', 'dx', 'bugfix', 'dormant-activate'] },
          priority: { type: 'string', enum: ['P0', 'P1', 'P2'] },
          effort: { type: 'string', enum: ['S', 'M', 'L'] },
          impact: { type: 'string' },
          where: { type: 'string', description: 'engram/ wire-point or harness' },
        },
      },
    },
    verdict: { type: 'string', description: 'honest one-paragraph: how far from "best", and the single highest-leverage move' },
  },
}

const ctx = (
  'You are the CTO of Engram/HippoAgent (repo C:/Users/aurel/Code/HippoAgent), driving it to "best real ' +
  'memory layer". A multi-workflow recon already ran. READ these committed artifacts for the findings:\n' +
  '- docs/COMPETITIVE_LANDSCAPE.md (competitor reverse + GitHub adoption roadmap with wire-points)\n' +
  '- docs/BENCHMARKS.md (measured numbers: HaluMem interference TPR~0.66/FPR~0.075, LongMemEval recall@5 0.909, ' +
  'stratified QA ~0.39, temporal/preference were small-n artifacts ~0.4-0.5)\n' +
  '- benchmark/results/github_deepdive_result.json (source-level adoptions ranked)\n\n' +
  'ALREADY SHIPPED THIS PASS (do NOT re-list as todo): timestamp-aware semantic_conflict (HaluMem FPR 0.10->0.0125) ' +
  'wired into the gate; recall `when` dates on all MCP recall tools; 3 verified bug fixes (requalify injection-topic ' +
  'security, replay data-loss durability, daemon model-blind); dormant apply_topic_penalty wired (env-gated); ' +
  'ENGRAM_SQLITE_SYNCHRONOUS durability knob; RRF tie-break. Engram\'s MOAT (write-path anti-confab grounding/NLI ' +
  'gate) is confirmed unique vs mem0/Zep/Letta.\n\n' +
  'Produce: (1) `done` — the proven wins to defend; (2) `roadmap` — the ranked remaining work to be #1 ' +
  '(P0/P1/P2, effort S/M/L, impact, engram/ where), favoring the differentiator (HaluMem-official harness, ' +
  'the one honest "best-on-X") + a like-for-like LongMemEval-500 number + the highest-leverage core/retrieval ' +
  'gains; (3) `verdict` — honest distance-to-best + the single highest-leverage next move. No hype.'
)

const r = await agent(ctx, { label: 'gap-roadmap', phase: 'Synthesize', schema: SCHEMA, effort: 'high' })
return r
