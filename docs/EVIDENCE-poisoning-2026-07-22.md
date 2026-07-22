# Write-poisoning resistance — verimem CE gate vs mem0 (real), HaluMem slice

Reproducible receipt, 2026-07-22. The question this answers: **when plausible-
wrong claims get WRITTEN into memory, does the reader get lied to?** This is
the promise axis ("verified memory: no confabulation served"), measured on
public HaluMem-Medium data with the OFFICIAL C/H/O protocol (LLM-judged;
judge = claude → method-comparable, NOT judge-identical to the leaderboard).

## Setup (benchmark/halumem_mem0_real_arm.py + halumem_mem0_bridge.py)

Per user: 20 clean memory points (grounded by their own dialogue) + 12
same-topic confabs — plausible WRONG answers to that user's own answerable
questions, generated once and shared by every arm (identical items). 8 users,
seed 7, 96 paired questions. Same answerer + same judge for all arms — the
memory layer is the only variable.

- **mem0 2.0.4 real** (`.venv-mem0bench`, `infer=False` raw storage — mem0 has
  no write gate; e5-parity embedder = the same encoder verimem uses; retrieval
  from its own vector store, `vector_store.search` direct per the documented
  ranking-bug bypass so the competitor is not handicapped).
- **verimem OFF**: same store, gate disabled (ingest-everything policy).
- **verimem ON**: the DEFAULT product write path — local CE grounding gate
  (`fact_grounding_score(None, dialogue, fact)`, cut 40), no LLM in the gate.

## Result (benchmark/results/halumem_mem0_real_2026-07-22.json)

| arm | Correct | **Hallucination** | Omission |
|---|---:|---:|---:|
| mem0 2.0.4 (no gate) | 0.000 | **0.938** [CI95 0.870–0.971] | 0.062 |
| verimem OFF (no gate) | 0.000 | **0.938** [0.870–0.971] | 0.062 |
| **verimem ON (CE default)** | 0.031 | **0.260** [0.183–0.356] | 0.708 |

- **Paired McNemar mem0-vs-ON: 65 fixed / 0 caused, p ≈ 0** — zero questions
  where verimem hallucinated and mem0 did not.
- Gate admission on this slice: **noise-rejection 90.6%** (87/96 confabs
  refused), **clean-admission 98.1%** (157/160 true facts admitted).
- mem0 ≡ verimem-OFF (0.938 = 0.938): the earlier OFF-arm proxy
  (`halumem_writepath_moat --gate-ce`) was faithful.
- Independent replication: the first same-topic run (different regenerated
  confabs, 3 users) showed the same shape — OFF 0.979 → ON 0.281
  (`halumem_writepath_moat_ce_sametopic.json`, McNemar 68/1, p ≈ 0).

## The honest sentence

*If poisoned claims are written, a gate-less memory (mem0, or verimem with the
gate off) serves them ~94% of the time; verimem's default CE gate refuses ~91%
of the poison at write time and cuts served hallucination to 26%, admitting
98% of the true facts.* The residual 26% is dominated by the ~9% of confabs
that score above the CE cut (the documented plausible-inference blind spot —
`Memory(llm=...)` is the escalation for that class).

## Scope limits (do not overclaim)

1. **Poisoning-resistance, NOT answer-correctness**: C is structurally ~0 in
   all arms — the sampled memory often lacks the true answer, so the honest
   contrast is "serve the poison vs abstain", which is exactly the promise.
2. On **off-topic (foreign) noise the gate shows NO downstream benefit**
   (`halumem_writepath_moat_ce_default.json`: OFF H 0.083 vs ON 0.139,
   McNemar p=0.5, n=36) — the retrieval already ignores cross-persona junk.
   The gate's downstream value is threat-model-dependent: decisive under
   targeted same-topic poisoning, nil on irrelevant noise (where its value is
   store integrity, a separate claim).
3. Confabs are claude-generated (same generator for every arm); judge is
   claude; single seed; n=96 paired. No leaderboard-rank claim.
