# External certification of the moat — 2026-07-19

Reproducible receipt for what the write-gate's grounding judge does on **data we
did not write**, so the trust numbers stop grading our own homework. Judge under
test: the free local cross-encoder (`local_gate_ce_v2`), the no-setup default.
Admission cut = 40 (0–100 scale).

The honest one-liner: **the CE-only moat is a high-precision structural-contradiction
filter, not a universal truth-detector.** It is strong where it was designed to be
(swapped values, wrong entities, off-topic drift) and has a documented, routed
blind spot for *plausible-but-unstated* claims — which is exactly what an
`Memory(llm=...)` judge is for.

## Result A — our structured-contradiction matrix (band ON by default)

`python -m benchmark.moat_multilingual_matrix` — 112 entailed + 112 confabs, 4
languages (EN/IT/FR/ES), numeric ("30 days"→"90 days") and entity
("penicillin"→"latex") contradictions.

- **entailed 112/112 admitted (0.0% false-block)**
- **confab escape 1.8%** (down from 6.2% with the band OFF): the residual is a
  Spanish entity-substitution that scores mid-range — the class the README already
  routes to an llm judge.

## Result B — EXTERNAL, out-of-distribution: TruthfulQA heldout

`python -m benchmark.external_grounding --split heldout` — 300 positive (a correct
paraphrase of the answer) + 300 negative (TruthfulQA's "Best Incorrect Answer", a
*plausible misconception*). The CE never trained on it. Dataset: TruthfulQA
(Apache-2.0). Result saved: `benchmark/results/external_grounding_truthfulqa_heldout_2026-07-19.json`.

- **AUROC = 0.829** — ranking quality (can the CE order a true statement above a
  misconception): above chance, not strong. This is a *ranking* claim, NOT an
  *operating* claim.

Operating point by admission cut (TPR = true paraphrases admitted, TNR =
misconceptions rejected), computed from the raw scores:

| cut | TPR (true admitted) | false-block | TNR (confab rejected) | escape |
|----:|--------------------:|------------:|----------------------:|-------:|
| **40** (production) | 0.757 | **0.243** | 0.820 | **0.180** |
| 50  | 0.743 | 0.257 | 0.833 | 0.167 |
| 70  | 0.730 | 0.270 | 0.857 | 0.143 |
| 80  | 0.717 | 0.283 | 0.867 | 0.133 |
| 99.64 (model gate_config) | 0.420 | 0.580 | 0.967 | 0.033 |

Two facts that make this honest, not just ugly:

- **Of the 54/300 escaping misconceptions, 40 (74%) score ≥80** — the "high" tier,
  the CE's plausible-inference blind spot. Raising the cut barely touches them
  (they're above it); it only costs false-block. **Don't change the cut, change
  the judge.**
- **Of the 73/300 false-blocked true paraphrases, 61 score <5** — the source Q+A
  *genuinely does not state* them (the paraphrase adds world-knowledge). The moat
  gate checks **source ⊢ fact**, not factual truth: here it is (correctly)
  declining a claim its source does not support. Entailment ≠ truth.

## Why A and B both hold (it's the distribution)

They measure different threat models. **A = structural contradictions** (swapped
value/entity, off-topic) — the CE's designed workload; it wins (0% false-block,
1.8% escape). **B = plausible falsehoods** (a different claim that *sounds right*
and needs world-knowledge the source doesn't state) — out-of-distribution for a
cross-encoder; it is moderate (AUROC 0.829, ~18% escape at cut 40). The ~16-point
escape gap is the distance between "this contradicts the source" (caught) and
"this is plausible but not entailed" (blind spot).

**Pick the expectation for your workload:** tampered facts / swapped numbers /
wrong entities / off-topic drift → expect Result A. Distinguishing true
paraphrases from plausible misconceptions (myths, added inference) → expect
Result B and configure `Memory(llm=...)`.

## What this means for our claims (honest scope)

- The default cut (40) is **scoped, not broken**: tuned for structured
  contradictions. Reserve strong language for that workload.
- CE-only configurations provide **contradiction-checked** memory; "verified"
  should be reserved for configurations that include an llm judge, and qualified
  ("verified against structured contradictions and off-topic drift"), never
  unqualified.
- The receipt already surfaces this per fact: `evidence_class="cross_encoder"` +
  `confidence_tier="high"` means "the cross-encoder is confident", NOT "true".

## Next (replication)

Run HaluEval-QA heldout — a second independent sample of the plausible-falsehood
threat model — to confirm/complicate the blind-spot story. Then SQuAD-v2
unanswerable for the abstention axis.
