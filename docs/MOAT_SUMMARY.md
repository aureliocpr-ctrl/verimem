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
extractor emits. The gate has cheap lexical layers (L1, no LLM) and an optional
source⊢fact entailment layer (L4, opt-in via `ENGRAM_GROUNDING_WRITE`).

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
semantic (not verbatim) entailment. Until clean-admission is high, the L4 gate is
correctly **OFF by default**.

## Bottom line

The write-gate is a **strong grounding discriminator** (AUROC 0.971, 100% noise rejection)
and, on the realistic retrieved-confab threat, **measurably lowers downstream hallucination
0.959→0.122 (McNemar p≈0, seed 7) — by making the agent ABSTAIN rather than confabulate**, not
by raising correctness. It is not a universal hallucination cure (foreign noise: no effect;
answer-path conditioning: no win), and at θ=40 its 38.6% clean over-rejection means the gain
in trustworthiness is paid in recall — tune before default-on. Every number here is
reproducible from `benchmark/` — no leaderboard placement is claimed.
