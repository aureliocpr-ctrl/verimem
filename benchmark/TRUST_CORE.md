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

**Coverage today (honest).** Strong on the in-house red-team corpus
(`gate_redteam_v1.jsonl`: 96.8% catch, 0% FP, 1 declared slip — fabricated
citation). KNOWN BIAS: corpus and gate share an author. Cure = external/
cross-model corpora + held-out discipline, not more self-written tests.

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

**Coverage today (honest).** WEAKEST front, highest customer exposure — this is
what a user touches on every query. `explain()` + `min_relevance` + abstention
exist (read-path 0.759 / abstention 1.0 on in-house sets) but were never
stressed on external data. Priority of block B.

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

**Coverage today (honest).** Barely started: L1.21 catches superlative-flattery
at write time; the read-path differential (neutral vs pressured recall) has
NEVER been measured.

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

## Design guard-rails imported from measured failures elsewhere

**Reputation inversion (Vivarium lab, 2026-07-10, chain fact
`058662b9e6c5`).** A trust ledger driven ONLY by outcomes, with blind
staleness attribution and no independent rehabilitation signal, has a
stochastic catastrophic failure mode up to full reputation INVERSION (good
sources scored bad, bad scored good). Measured remedy there: INTER-SOURCE
AGREEMENT as the dense signal, not outcome alone. Binding consequence for
Verimem: if/when the ledger starts weighting SOURCES by track record
(source-reputation, decision-outcome loops), it must (a) never use
outcome-only updates, (b) attribute staleness to the specific claim, not the
source wholesale, (c) provide a rehabilitation path (agreement with
independently-verified facts re-earns trust). Until those three exist,
per-fact status stays the only reputation object — no source-level scoring.
