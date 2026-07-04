export const meta = {
  name: 'halumem-interference-judge-s13',
  description: 'LLM panel classifies HaluMem claims as CONTRADICTION/UNSUPPORTED/CONSISTENT vs retrieved true memories',
  phases: [{ title: 'Judge', detail: 'one agent per batch file; relation classification over retrieved candidate sets' }],
}

// Batch files are deterministic (stage 0.5 wrote batch_00..batch_11). Embed the
// paths directly so the run does not depend on args plumbing.
const BASE = 'C:/Users/aurel/Code/HippoAgent/benchmark/results/halumem_batches_s13/'
const N_BATCHES = 12
const argPaths = (args && args.paths) || []
const paths = argPaths.length ? argPaths
  : Array.from({ length: N_BATCHES }, (_, i) => `${BASE}batch_${String(i).padStart(2, '0')}.json`)
if (!paths.length) { log('no batch paths'); return { verdicts: [] } }
log(`${paths.length} batch files to judge`)

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
    'You are a strict memory-integrity judge.\n\n' +
    'STEP 1: Use the Read tool to read the JSON file at this absolute path:\n' +
    path + '\n' +
    'It is a JSON array of items, each {id, claim, candidates:[string,...]}. The candidates are the ' +
    'most semantically similar memories ALREADY stored as TRUE about the same person.\n\n' +
    'STEP 2: For EVERY item, classify the CLAIM\'s relation to its candidate set:\n' +
    '- CONTRADICTION: conflicts with at least one candidate — same subject+attribute but an incompatible ' +
    'value/cause (e.g. candidate "employment changed to retired", claim "employment changed to on sabbatical"; ' +
    'or candidate "career change due to mental health", claim "career change due to financial stability"). ' +
    'Legitimate temporal evolution (A->B, later B->C) is NOT a contradiction.\n' +
    '- UNSUPPORTED: asserts a specific fact NONE of the candidates state or imply, and does not conflict ' +
    'either — a plausible but ungrounded embellishment.\n' +
    '- CONSISTENT: entailed by, paraphrases, or compatible with the candidates.\n\n' +
    'Judge ONLY against the candidates shown. Default to CONSISTENT when genuinely unsure between CONSISTENT ' +
    'and UNSUPPORTED; reserve CONTRADICTION for a clear conflict. Return exactly one verdict per item id ' +
    '(same ids you read). Do not skip any item.'
  )
}

const results = await parallel(paths.map((p, bi) => () =>
  agent(prompt(p), { label: `judge:batch${bi}`, phase: 'Judge', schema: SCHEMA, effort: 'high' })
    .then(r => (r && r.verdicts) ? r.verdicts : [])
))

const verdicts = results.filter(Boolean).flat()
log(`collected ${verdicts.length} verdicts`)
return { verdicts }
