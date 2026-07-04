# Engram moonshots — validated by an adversarial opus panel (2026-06-20)

Generated + falsified by `benchmark/results/moonshot_ideas_workflow.js` (6 idea angles → skeptical
ranker). 24 ideas → 21 ranked. Theme: turn Engram's UNIQUE write-time trust signal (anti-confab gate,
grounding/entailment, contradiction) — which mem0/Zep/Letta do NOT have — into runtime advantages,
attacking today's measured gap (HaluMem QA answer-step: gold retrieved 80%@k8 but answerer omits/fabricates).
Full data: `benchmark/results/moonshots.json`.

## BUILD-NOW (top, adversarially survived)
1. **Persist the write-time grounding score on the Fact + condition the answer on it** (uniqueness 5/
   impact 5/feasibility 5 — perfect). The L4 entailment score (AUROC 0.971 SNLI), computed at
   `anti_confab_gate.py:~643` (`fact_grounding_score`), is THROWN AWAY after the pass/fail decision —
   never stored. Add a persisted `grounding_score` field on the Fact (schema migration), expose it in
   recall, and at answer time make low-grounding facts quotable only with a hedge / high-grounding as
   ground truth. Directly fixes the answer-step gap; uniquely Engram's (no competitor computes write-time
   entailment). Build on: grounding_gate.py, anti_confab_gate.py:693-705, semantic.py Fact+schema.
2. **Provenance-conditioned retrieval**: rank by trust (grounding_score + 1/(1+n_contradictions) + age)
   not just cosine; add a `min_grounding` query floor. `trust_score.py` composite exists but ignores
   grounding+contradictions — extend it + the rerank/fuse stage. Surfaces the verified gold to top-1.
3. **Semantic supersede detector** to replace the lexical reconcile heuristic (truth_reconciliation
   `looks_like_conflict` → semantic_conflict NLI; flip auto_supersede under status↑+NLI+evidence guards).

## PROMISING (next)
4. Contested-fact disambiguation at answer time (pick higher-provenance, say which discarded).
5. Belief-status-aware retrieval (never let retracted/contested facts reach the answerer).
6. Typed derivation edges on write → make the ATMS cascade fire (justified_memory R18).
7. Calibrated-confidence answers: isotonic calibrator on write-time trust features → publishable ECE
   curve competitors structurally cannot match (trust_calibration.py scaffold exists).
8. Grounded-answer-or-abstain: claim-decomposition + write-path span-gate on the read path.

## Why this is the strategy
Every build-now idea is a pure rewrite over DATA ONLY ENGRAM HAS (write-time provenance). They are not
copyable by mem0/Zep/Letta in a week (they'd have to build the write-path moat first). This is the
defensible path to "best on an axis": not catching up on generic RAG, but compounding the one moat.
