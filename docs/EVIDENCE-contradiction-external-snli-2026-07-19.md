# External certification of the contradiction judge — SNLI, 2026-07-19

Larger-n, external-dataset receipt for the write-path contradiction JUDGE (the free local
NLI `LocalRelationJudge`, MoritzLaurer DeBERTa-v3-large), complementing the 18 hand-labeled
pairs in `docs/EVIDENCE-phase1.1-contradiction-moat-2026-07-19.md`. Reproduce:

```
python -m benchmark.semantic_conflict_external --per-label 150
# result: benchmark/results/semantic_conflict_snli.json
```

## Result — SNLI test, n=450 (150 per gold label)

| metric | value | reading |
|---|---:|---|
| **contradiction recall** | **0.92** | 138/150 gold-contradictions called CONTRADICTION |
| **false-contradiction rate** | **0.03** | 9/300 gold-{entailment,neutral} WRONGLY called CONTRADICTION |
| entailment recall | 0.047 | see note — this is the intended semantics, not a miss |

Confusion (gold → judge verdict):

- **contradiction** (150): 138 contradiction · 12 neutral · 0 entailment
- **neutral** (150): 136 neutral · **9 contradiction** · 5 entailment
- **entailment** (150): 143 neutral · 7 entailment · **0 contradiction**

## Honest reading

- **Strong, precision-biased contradiction detection.** 0.92 recall with a **3%**
  false-contradiction rate is exactly the asymmetry the moat is designed for (a wrong
  CONTRADICTION impugns a true fact, so precision matters most). The 9 false-contradictions
  are ALL on the *neutral* class (6% of neutrals); **0** on entailment. This confirms the
  n=18 `3336d56` result (12/12 conflicts caught, 0 false-positive on complementary pairs)
  **at scale, on an external dataset**.
- **The low entailment-recall (0.047) is BY DESIGN, not a weakness.** The judge flags
  ENTAILMENT (a *duplicate*) only when BOTH directions entail — a true paraphrase. SNLI
  entailment is DIRECTIONAL (premise ⊨ hypothesis, but the hypothesis usually does NOT
  entail the premise, e.g. a narrower→broader restatement), so those correctly resolve to
  NEUTRAL, not "duplicate". The moat is not trying to detect one-way entailment; it detects
  duplicates + contradictions. A directional-entailment metric would be the wrong yardstick.

## Caveat (do not over-read)

**SNLI is NEAR-IN-DOMAIN for this model** — MoritzLaurer trained on MNLI/FEVER/ANLI/ling/
wanli, the same NLI distribution (not SNLI itself). So 0.92/0.03 are OPTIMISTIC vs a truly
out-of-distribution corpus — the same caveat Phase 0 published for the 0.96-0.97 SNLI
grounding number (`docs/EVIDENCE-external-2026-07-19.md`). This certifies the judge's NLI
competence at scale; it is NOT an OOD guarantee. On the write path the judge runs in
**observe** mode by default precisely so its real-tenant false-positive rate is measured
before it ever enforces.
