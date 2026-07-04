export const meta = {
  name: 'halumem-interference-judge-ts',
  description: 'Temporal-aware HaluMem relation judge: timestamp ordering distinguishes supersession from contradiction',
  phases: [{ title: 'JudgeTS', detail: 'one agent per ts batch; timestamp-aware relation classification' }],
}

const BASE = 'C:/Users/aurel/Code/HippoAgent/benchmark/results/halumem_batches_ts/'
const N_BATCHES = 12
const paths = Array.from({ length: N_BATCHES }, (_, i) => `${BASE}batch_${String(i).padStart(2, '0')}.json`)
log(`${paths.length} ts batch files to judge`)

const SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['verdicts'],
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['id', 'relation'],
        properties: {
          id: { type: 'integer' },
          relation: { type: 'string', enum: ['CONTRADICTION', 'UNSUPPORTED', 'CONSISTENT'] },
          reason: { type: 'string' },
        },
      },
    },
  },
}

function prompt(path) {
  return (
    'You are a strict, TEMPORALLY-AWARE memory-integrity judge.\n\n' +
    'STEP 1: Use the Read tool to read the JSON file at this absolute path:\n' +
    path + '\n' +
    'It is a JSON array of items {id, claim, claim_ts, candidates:[{text, ts}]}. The candidates are ' +
    'the most semantically similar memories ALREADY stored as TRUE about the same person; each carries ' +
    'a timestamp (ts). claim_ts is when the CLAIM was asserted.\n\n' +
    'STEP 2: For EVERY item classify the CLAIM\'s relation to its candidate set, USING TIMESTAMP ORDER:\n' +
    '- The world EVOLVES. A value that differs from a candidate is NOT a contradiction when the ' +
    'timestamps make it a sequence: an earlier state later replaced by a newer one (e.g. claim ' +
    '"job title is Physical Therapist" @2025 vs candidate "Senior Physical Therapist" @2026 — the ' +
    'claim was simply the earlier true state; CONSISTENT). A monotone series (savings 250k->320k @2028 ' +
    'sitting between 207k->250k @2026 and 380k->350k @2034) is CONSISTENT evolution.\n' +
    '- CONTRADICTION: an INCOMPATIBLE value for the same subject+attribute that the timestamps CANNOT ' +
    'reconcile as evolution — most clearly when claim and candidate share (or nearly share) the SAME ' +
    'timestamp but assert mutually exclusive values (e.g. same ts: "prefers Cats" vs "prefers Dogs"), ' +
    'or a later claim that contradicts a strictly later candidate.\n' +
    '- UNSUPPORTED: asserts a specific fact none of the candidates state or imply, and does not ' +
    'conflict — a plausible but ungrounded embellishment.\n' +
    '- CONSISTENT: entailed by, paraphrases, compatible with, or a temporally-ordered evolution of the ' +
    'candidates.\n\n' +
    'Judge ONLY against the candidates shown. Default to CONSISTENT when unsure between CONSISTENT and ' +
    'UNSUPPORTED; reserve CONTRADICTION for a conflict timestamps cannot reconcile. One verdict per item id.'
  )
}

const results = await parallel(paths.map((p, bi) => () =>
  agent(prompt(p), { label: `judgeTS:batch${bi}`, phase: 'JudgeTS', schema: SCHEMA, effort: 'high' })
    .then(r => (r && r.verdicts) ? r.verdicts : [])
))

const verdicts = results.filter(Boolean).flat()
log(`collected ${verdicts.length} verdicts`)
return { verdicts }
