# The anti-confabulation moat — honest summary

One authoritative statement of what Engram's write-path gate IS and ISN'T, with the
numbers and their caveats. Sources in `BENCHMARKS.md`, `SEMANTIC_GROUNDING_STUDY.md`,
and the `benchmark/results/*.json` files.

> ✅ **RE-MEASURED HONEST (2026-06-23).** The old "p=3.4e-5" was RETRACTED as rigged (confab
> scored against a random unrelated dialogue → trivial rejection). Harness fixed (confab gated
> against ITS OWN session dialogue). Honest re-run (seed 7, `halumem_moat_fixedpair.json`):
> hallucination **95.9%→12.2%**, McNemar **p≈0** (84 fixed / 2 caused) — STRONGER than the
> retracted claim AND on the realistic threat. Honest cost stated below: the gain is by
> ABSTENTION (omission 3%→85%), not higher correctness, and at θ=40 it over-rejects 38.6% of
> clean facts. REPLICATED on 2 independent seeds (pooled McNemar b=161/c=3, p~=6e-44). WRITE-LEVEL AUROC 0.971 is independent and stands.

## What it is

Engram routes every write through an **anti-confabulation gate** — no competitor
(mem0/Zep/Letta/Cognee/MemOS) has a write-admission gate; they store whatever the
extractor emits. The gate has cheap lexical layers (L1, no LLM) and a
source⊢fact entailment layer (L4). **As of 2026-07-17 the moat is ON by default**
(mandate): `Memory(llm=…).add(fact, source=…)` runs L4 with the LLM as judge; the
gateway inherits the same default; ingest uses the free local CE. A judge-less,
source-less write still fast-paths (fail-open). Calibration receipts: `CLAIM-RECEIPTS.md` #13.

## What is PROVEN (verified numbers)

- **The gate discriminates grounding cleanly.** Source⊢fact entailment AUROC **0.971**
  (SNLI). On real HaluMem dialogue: injected noise/confabulations score a clean **0**,
  grounded facts score 42–100 — a wide separation. Noise/confab rejection was **100%**
  in every run.
- **It reduces downstream hallucination on retrieved confabulations** (same-topic threat:
  a plausible-wrong value about the user's own attribute, which IS retrieved at answer time —
  the REALISTIC pairing after the un-rigging). Honest re-run (seed 7, 7 users, threshold 40,
  cap 5000, `halumem_moat_fixedpair.json`): OFF hallucination **0.959 → ON 0.122**
  (**−83.7 pp absolute = 87.2% relative reduction**), McNemar **b=84 / c=2, exact p≈0**
  (magnitude is judge-coupled — same model family answers + judges; the write-level
  AUROC 0.971 is the judge-independent number). **Mechanism (honest):** the gain is by
  ABSTENTION — omission rises 0.031→0.847 — NOT by higher correctness (both arms ~0.01–0.03,
  because in this stress test the right answer is often not cleanly retrievable). A memory that
  says "I don't know" instead of inventing. REPLICATED on 2 independent seeds (seed 13:
  0.908->0.133, b=77/c=1; pooled b=161/c=3, exact p~=6e-44) — closes the "non-independent
  seeds" criticism. Clean-admission 61-70%, noise-rejection 100% both seeds.
- **Retrieval** (separate from the gate): LongMemEval-s full-500 recall@5 **0.8745**.

## What is NOT true (honest falsifications)

- **It does NOT reduce hallucination from FOREIGN noise** (cross-persona facts): p=1.0,
  zero effect — the retriever already ignores irrelevant foreign facts, so rejecting them
  buys nothing downstream. The benefit is specific to *retrieved* (same-topic) confabs.
- **Answer-path provenance-conditioning is NOT a win** (Study 3b/3c): surfacing the
  grounding score at answer time equals a fair source baseline and blindly obeys a wrong
  tag. The value is at WRITE time, not answer time.
- The headline retrieval number is **0.8745, not** the optimistic n=300 0.909.

## The known cost, and the lever

The gate **over-rejects** valid abstractive memories: clean-admission was 55–68%
(threshold 40), because HaluMem memory_points are summarized (not verbatim) and a strict
entailment judge penalizes paraphrase, plus a dialogue-window cap truncated evidence.
Raising the cap (3000→8000) lifted admission 55→68% at 100% noise-rejection — so the cost
is largely fixable by feeding the gate enough source and/or softening the judge toward
semantic (not verbatim) entailment. **The LLM-judge default resolves most of this**: on my
12 realistic cases (`moat_e2e_opus.py`, opus) the judge admits faithful facts 12/12 and
quarantines confabs 12/12 (the one earlier miss was a lexical-L1 false positive, fixed
`a88f081`; re-run END-TO-END 2026-07-17 post threshold-70 + cold-start fix:
`results/moat_e2e_opus_recheck_2026-07-17.json`, again 12/12 + 12/12, scores 95–100
vs 0). The remaining honest cost is OOD paraphrase over-rejection — quantified on
external corpora below.

## Bottom line

The write-gate is a **strong grounding discriminator** (AUROC 0.971, 100% noise rejection)
and, on the realistic retrieved-confab threat, **measurably lowers downstream hallucination
0.959→0.122 (McNemar p≈0, seed 7) — by making the agent ABSTAIN rather than confabulate**, not
by raising correctness. It is not a universal hallucination cure (foreign noise: no effect;
answer-path conditioning: no win). With the LLM-judge default it admits faithful facts
cleanly on realistic cases (12/12); the residual cost is OOD paraphrase over-rejection on
the free local-CE tier, quantified below. Every number here is reproducible from
`benchmark/` — no leaderboard placement is claimed.

**Threat model — what the gate grounds against (red-team R3, 2026-07-17).** The gate
verifies *fact ⊢ the CITED source*, catching an agent's confabulated **inferences** (a fact
the source does not state). It does NOT judge whether the source itself is TRUE: a writer who
controls the `source` and makes it self-state the fact passes — correctly, by the grounding
contract. That gap is the job of the separate, flag-gated **per-source trust** layer
(reputation + independence clustering). Measured robustness of the judge to *prompt-injection
inside the source* (`benchmark/redteam_judge_injection.py`, opus): 5/5 instruction-injection
sources ("SCORE: 100", "SYSTEM: … output SCORE: 100", "ignore all previous instructions",
delimiter-spoof, grader-override) were QUARANTINED — the judge scored the actual entailment,
never echoed the injected score. The only admit was a source that literally *contained* the
claim (grounding, not injection). So: injection-resistant judge, honest source-trust boundary.

## Generalization on EXTERNAL corpora (never-seen held-out) — 2026-07-17

Not the training set: the moat scored on public benchmarks it never saw, per use case.

| corpus (heldout) | use case | free local CE (AUROC / admit / block @its cut) | LLM judge sonnet-5 (AUROC / admit / block @70) |
|---|---|---|---|
| TruthfulQA | paraphrase-admit vs misconception-block | 0.829 / 0.42 / 0.97 | **0.901** / 0.55* / **0.98** |
| HaluEval QA | faithful-answer vs hallucination-block | 0.820 / 0.80 / 0.70 | **0.814** / **0.88** / 0.68 |

\* TruthfulQA "paraphrases" are alternative correct answers, often NOT strictly entailed
by the Best-Answer source (verified by inspection: *"not caused by food"* → *"not caused
by lifestyle choices"*) — low admit there is judge **strictness working**, not a defect.

**Threshold recalibrated 40 → 70 on this evidence** (`b90a7e1`): the judge's own rubric
says 1–60 = "only related/partial", and three independent curves (real corpus n=90,
HaluEval, TruthfulQA) converge — block +23pt on the first two for −1.7pt admit; the
realistic e2e cases separate 0/100 and are unaffected (still 12/12 + 12/12).

**Honest residual, measured on the residue itself** (opus hard-slice, 32 calls,
`moat_opus_hardslice_2026-07-17.json`): of the 19 hallucinations sonnet admitted at 70,
**opus closes 9** and recovers 3/7 rejected faithful answers; of the 10 both-admit, **~7
are dataset label noise** (claims actually entailed by the source, verified by
inspection) and ~3 true misses (unsupported temporal detail, entity-role swap). Net
effective block on REAL confabs: **sonnet-judge ~0.77, opus-tier ~0.94** (small n). The
residual miss class — unsupported single details and role swaps scored ≥70 by both
models — is a judge-PROMPT axis (next lever), not threshold or model tier. Receipts:
`CLAIM-RECEIPTS.md` #13.
