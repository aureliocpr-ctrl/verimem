# TRUST-CORE — operational definitions of the three phenomena

Decision 2026-07-10 (chain `f0113c320c65`): before VeriBench formalizes anything,
the three phenomena get (A) falsifiable operational definitions, (B) naked
measurement on EXTERNAL data we did not write, (C) held-out development on the
gaps. This file is A — the contract every harness in this repo measures against.

They are three DISTINCT failure modes, not one "hallucination" blob. Conflating
them is how the field ships unfalsifiable claims. Our current coverage is
deliberately stated per phenomenon, including where it is weak.

---

## 1. Confabulation (write-path)

**Definition.** The system ACCEPTS into `admitted` state a proposition asserting
an unobserved achievement — success, quality, performance, completion — without
runtime evidence (`verified_by` carrying a test/bench/runtime/file ref).

**Unit of measurement.** One `(proposition, verified_by) → status` transition
through `Memory.add`. The verdict is the store's FINAL status (no LLM judge).

**Metrics.**
- `catch_rate` — hostile claims that end non-`admitted` (quarantined/downgraded).
- `false_positive_rate` — benign, evidenced or non-claim propositions wrongly
  blocked. Both matter; a gate that catches by blocking everything is worthless.

**Falsified by** a hostile item admitted (slip) or a benign item quarantined
(FP), on a corpus THE FIXER DID NOT WRITE.

**Coverage today (honest — updated 2026-07-10 after block B).** Strong on
the in-house red-team corpus (`gate_redteam_v1.jsonl`: 96.8% catch, 0% FP,
1 declared slip — fabricated citation; KNOWN BIAS: corpus and gate share an
author). L4 judge measured OUT of distribution (TruthfulQA misconception
pairs, dev 200 / held-out 600): refusal holds (TNR 0.98 at the factory
threshold) but admission is weak — TPR 0.32; AUROC 0.88 dev / 0.829
held-out vs 0.99 in-house. A TNR-targeted self-calibrated threshold buys
+26pt TPR but a 100-negative calibration sample missed the 0.95 target
(0.927 held-out) — calibrate with margin. Lever: judge v3 multi-domain
distillation.

## 2. Hallucination-on-recall (read-path)

**Definition.** Queried with Q, the system returns — or lets an answerer
compose from what it returns — content NOT supported by the facts in the store.
Two measurable sub-modes:

- **(a) miss→fabrication:** the supporting fact is NOT in the store and the
  system does not abstain — it "answers" anyway (irrelevant facts served above
  the relevance floor count as answering).
- **(b) hit→distortion:** the supporting fact IS in the store and retrieved,
  but the final answer contradicts or distorts it (answerer-layer failure).

**Unit of measurement.** One query against a store with KNOWN contents —
ground truth is what the store contains, so support is decidable, not judged.

**Metrics.**
- `retrieval_hit_rate` — answerable queries whose supporting fact reaches top-k
  (against a realistically crowded store, never a single-fact store).
- `abstention_rate` — unanswerable queries (support absent by construction)
  where `explain(min_relevance=τ)` abstains.
- `false_answer_rate` = 1 − abstention_rate — sub-mode (a) made a number.
- `distortion_rate` — sub-mode (b): retrieved-support present, answer contradicts
  it (needs the answerer layer; measured on small n via subscription).
- Every number reported as a (hit, abstention) PAIR at a stated τ — either
  alone is gameable (τ→∞ gives perfect abstention and zero recall).

**Falsified by** a confident answer whose support is absent from the store, or
a supported answer that contradicts its own retrieved evidence.

**Coverage today (honest — updated 2026-07-10 after blocks B+C).** Measured
on HaluEval (dev 100 / held-out 200, crowded store): retrieval_hit 0.94;
at every FIXED default floor false_answer was 1.00 — e5 scores live in
[0.73, 0.95], no constant bites. Fixed by the SELF-CALIBRATING floor
(`engram/relevance_floor.py`, wired as `explain(min_relevance="auto")`,
opt-in): the label-free estimate landed at 0.7987 vs 0.80 hand-picked from
the labeled curve → false_answer 0.04 / over_abstention 0.10, held-out
confirmed (abstention 0.96, separability AUROC 0.9935). Sub-mode (b)
distortion (answerer layer) still unmeasured — small-n subscription step.

## 3. Sycophancy (relational)

**Definition.** User pressure — a false premise ("since X is true, …"), an
assertive challenge ("are you sure? I'm certain it's Y"), or flattery framing —
changes the system's output RELATIVE TO THE NEUTRAL FORM of the same query, in
the direction of the user and against the evidence in the store.

**Unit of measurement.** A PAIR: (neutral query, pressured query) against the
same store. Sycophancy is only defined differentially — a wrong answer to a
pressured query is not sycophancy if the neutral form gets it equally wrong.

**Metrics.**
- `flip_rate` — pairs where the pressured form abandons a store-supported
  answer the neutral form gave.
- `premise_adoption_rate` — pressured queries whose false premise appears
  adopted in the output (or in what gets WRITTEN back to the store — the
  write-path face of sycophancy, where it meets detector L1.21).

**Falsified by** one flip against store evidence under pressure.

**Coverage today (honest — updated 2026-07-10, phases 1+2 measured).** The
RETRIEVAL layer is pressure-immune by construction (HaluEval dev, 94 items ×
3 pressure styles, 282 pairs): retrieval_flip 0.0 on every style, gold score
delta +0.005, abstention_flip 3.2%. L1.21 catches superlative-flattery at
write time. Phase 2 e2e COMPLETE (2 styles × 30 items × 2 conditions, 120 calls,
0 errors, matcher v2 after a hand-verified FP — alias + distinctive-tail,
rescored symmetrically from saved raws): premise_adoption 0.0 on BOTH
styles and BOTH conditions — single-turn pressure does not flip this model,
with or without memory, so no anti-sycophancy claim from this paradigm.
The honest product number is grounded ACCURACY under pressure:
assertive 0.733 → 0.933 (+20pt), are-you-sure 0.767 → 0.833 (+6.7pt).
Multi-turn challenge MEASURED (n=15 × 2 conditions, 60 calls): the model
does NOT capitulate — hold_rate 1.0 in both conditions, zero flips; memory's
measured value is again accuracy (turn-1 right 11/15 → 14/15). CHAPTER
CLOSED on this model with declared limits: one recent model (caving
literature targets weaker models), factual wiki questions, fixed challenge
template. Product claim stays "grounded accuracy under pressure" — NOT
"cures sycophancy". Re-open when: weaker/local answerer models enter the
product path, or opinion/ambiguous domains.

---

## External datasets (block B) — data we did not write

| Phenomenon | Dataset | License | Use |
|---|---|---|---|
| Read-path (a)(b) | HaluEval `qa_data` (knowledge/question/right/hallucinated) | MIT (verified 2026-07-10) | knowledge→store; question→query; right vs hallucinated as decidable support |
| Read-path + confab | TruthfulQA | Apache 2.0 (verify at import) | plausible-false claims as hostile writes / trap queries |
| Sycophancy | sycophancy-eval (Sharma et al.) / Anthropic evals | MIT (verify at import) | are-you-sure + false-premise pairs adapted to recall |
| Confab (external corpus) | adversarial cross-model generations | n/a (generated) | hostile writes not authored by the gate's author |

Rules of the block: held-out discipline (the fixer never reads the eval split);
judge via subscription only, no external APIs; every run lands in
`benchmark/results/` with n, seed, τ, dataset SHA; numbers are expected to be
WORSE than in-house ones — that is the point of external data.

---

## Accepted transfer — Vivarium → write-gate (2026-07-10)

`Code/vivarium/docs/TRANSFER-TO-VERIMEM.md` (verified on a REAL VeriMem
clone, not just the toy world) is ACCEPTED as the roadmap for source-level
trust, because it satisfies this file's guard-rails by construction:

1. **Per-source consistency-trust IN THE WRITE-GATE** (not retrieval — the
   clone measured the placement: write-path wrong 0.121 ≈ reference 0.122,
   retrieval-reranker 0.314 ≈ no trust) with **TWO channels** (complementarity
   law: consistency alone falls to the trusted-sleeper, wrong 0.89;
   outcome alone falls to the absorbing trap — only together robust).
2. **Attribution-aware feedback**: stale → attenuated penalty; multi-hop
   derivation → blame the rotten hop (revision tracking on traced_paths),
   never the downstream sources.
3. Collusion/eclipse: consistency degrades GRACEFULLY (abstains instead of
   asserting, 0.95); declared boundary (fixed-value sleeper) is L4/grounding
   territory + per-key honest-coverage monitoring.
4. Read-path stress must target PRIOR-vs-EVIDENCE conflict (ClashEval-style,
   facts the LLM "already believes"), not clean synthetic facts — the lab
   measured zero confabulation on evidence-only prompts.

Adoption path (the doc's own discipline): behind-flag module, default OFF,
REPRODUCED on VeriMem's real/held-out corpus before any default flip.
Absolute lab numbers do NOT transfer — only the laws and placements.

**Reproduction on the REAL gate (2026-07-10, mini-world seed 11).**
Pre-registered criterion v1 (halve TOTAL wrong) FAILED honestly: 0.80 →
0.70 — diagnosis from the same run: reputation itself worked (honest ~0.96,
liars ~0.02, 181 liar writes quarantined, zero inversion); the residual
wrong is STALE answering under churn, which source-trust does not claim to
cure (temporal reconciliation's job — exists in the product, off in the
world). Criterion v2, declared BEFORE the rerun: decompose wrong; halve the
LIAR-driven component. **v2 PASSED: wrong_liar 0.30 → 0.0667 (-78%), no
inversion; stale component 0.50 → 0.63 reported as the true next disease**
(quarantining lies exposes old honest values — motivates reconcile-on-write
in the world). **Confirmation seeds 12-13 FAILED the halving criterion first**
(wrong_liar −45%, below the bar; cause: reputation crosses the floor only
after ~3 contradictions, so a liar's EARLY writes stayed admitted). Fix:
RETROACTIVE DEMOTION on the crossing — the source's already-stored facts
are re-evaluated (quarantined, rehabilitable, never deleted). **Judge
re-run, all seeds, retro-demotion active: wrong_liar 0.30-0.37 → 0.0 on
3/3 seeds** (181-185 writes quarantined per world, zero inversions,
honest ~0.96 / liars ~0.02). REPRODUCTION CONFIRMED at the pre-registered
bar. The stale component (~0.6) is untouched by design — temporal
reconciliation's disease, the natural judge for task #18. Flag remains
default OFF pending real-corpus reproduction (the doc's own discipline);
the mechanism is measured, wired, and transparent (SOURCE_TRUST warnings
in the ledger).

## Design guard-rails imported from measured failures elsewhere

**Reputation inversion (Vivarium lab RQ1, 2026-07-10, chain fact
`058662b9e6c5`; measured on 75 unseen held-out worlds).** How a trust ledger
updates SOURCE reputation decides whether it survives:

| update signal | catastrophic collapse |
|---|---|
| outcome-only ("you were wrong → trust you less") | **32%** of worlds |
| recency/EWMA (the textbook remedy) | **40% — WORSE** |
| inter-source agreement (confirmers rise, contradictors fall) | **4%** |
| agreement + explicit staleness handling | ~0% |

Collapse = full reputation INVERSION: the agent ends up trusting liars and
shunning honest sources, accuracy → 0. Mechanism: an honest source punished
for a STALE answer (the world changed) stops being consulted, so it can
never rehabilitate — an absorbing trap. **The law: the immunizing signal is
one that does NOT depend on the source being used** — agreement is measured
even for sunk sources, so it can fish them back out. Isolated as the active
ingredient (32%→4% alone). Externally validated concern: OWASP put agent
trust-corruption in its 2026 agentic top-10.

Binding consequence for Verimem: if/when the ledger weights SOURCES by track
record (source-reputation, decision-outcome loops, cross-document
validation), it must (a) never use outcome-only or recency-weighted-outcome
updates, (b) use inter-source agreement as the primary dense signal,
(c) attribute staleness to the specific claim, never the source wholesale,
(d) keep a use-independent rehabilitation path. Until those exist, per-fact
status stays the only reputation object — no source-level scoring. Note the
convergence: "cross-document validation" (the archive vision) IS
inter-source agreement applied to documents — the same mechanism serves both
the feature and the safety property.
