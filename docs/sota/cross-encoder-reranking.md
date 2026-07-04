# SOTA — Cross-encoder reranking after bi-encoder recall (HippoAgent)

**Status**: documentation; NEW (proposed cycle, no task id yet).
**Date**: 2026-05-23 (cycle 203).
**Scope**: gap analysis on adding a cross-encoder reranker stage
**after** the bi-encoder cosine recall. Companion to the cycle-185
community / cycle-188 highway / cycle-190 multi-signal / cycle-192
temporal quartet.

---

## 1. Motivation

Current retrieval (`engram.semantic.recall` + `recall_hybrid`) uses a
**bi-encoder** model (sentence-transformers `all-MiniLM-L6-v2`,
384-dim float32). Bi-encoders are FAST because they embed query and
docs INDEPENDENTLY (offline doc embeddings + 1 query embedding at
query time). But they sacrifice accuracy: the model never sees
query and doc TOGETHER, so subtle relevance signals (negation,
co-reference, query-specific aspect) are lost.

**Cross-encoders** (e.g. BGE-reranker-v2-m3, ms-marco-MiniLM-L-12-v2)
re-score `(query, doc)` pairs **jointly**. They are ~2-3× more
accurate on MS-MARCO and similar benchmarks but ~100× slower because
each pair is a separate model forward pass.

The standard SOTA pattern: **two-stage retrieval**.
  1. Bi-encoder retrieves top-K candidates (fast, recall-oriented).
  2. Cross-encoder re-ranks the K candidates (slow, precision-oriented).
  3. Return top-N from re-ranked list (N ≤ K, typically N=5, K=50).

---

## 2. SOTA candidates

| Model | Params | Size on disk | Notes |
|------|------|------|------|
| `BGE-reranker-v2-m3` | 568M | ~1.1 GB | Best in class on MTEB Reranking |
| `cross-encoder/ms-marco-MiniLM-L-12-v2` | 33M | ~125 MB | Lightweight, strong baseline |
| `cross-encoder/ms-marco-electra-base` | 110M | ~440 MB | Mid-range, faster than BGE |
| `nlpaueb/legal-bert-cross-encoder` | 110M | ~440 MB | Domain-tuned (legal); not relevant here |

**Recommended for HippoAgent**: `ms-marco-MiniLM-L-12-v2` (125 MB).
The smaller MiniLM keeps the subscription-only constraint
"reasonable" (no Anthropic API needed; local inference via
sentence-transformers / `CrossEncoder` class). BGE-reranker is more
accurate but 1.1 GB is hard to justify for a 1.7k-fact corpus.

---

## 3. Latency budget

Empirical (cycle 179 bench + community knowledge):
- Bi-encoder query embed: ~10 ms cold, <1 ms warm.
- ms-marco-MiniLM-L-12-v2 cross-encoder forward on a single pair:
  ~5-10 ms warm (CPU-only Win11), ~1-2 ms with GPU.
- For K=50 candidates: ~250-500 ms cross-encoder rerank.
- Total two-stage: ~250-510 ms vs ~5-15 ms bi-encoder-only.

**Verdict for HippoAgent**: 250-500 ms is too slow for the hot recall
path (called multiple times per Claude Code turn). But ACCEPTABLE for:
  - Auto-Dream cycle (every 30 min, can pay 500 ms once)
  - High-stakes recall (operator explicitly asks for "best match")
  - Offline batch rerank to populate a precomputed ranking column

---

## 4. Design — `engram/cross_encoder_rerank.py` (proposed cycle 204)

API sketch:

```python
def rerank_candidates(
    query: str,
    candidate_fact_ids: list[str],
    *,
    semantic_db: Path,
    top_n: int = 5,
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-12-v2",
    batch_size: int = 16,
) -> list[tuple[str, float]]:
    """Re-score a candidate list using a cross-encoder.

    Returns ``[(fact_id, score), ...]`` of length ≤ top_n sorted
    desc by score. The scores are model logits — caller decides
    threshold semantics.

    Lazy-loads the CrossEncoder model (first call pays 1-3s cold).
    Subsequent calls reuse the cached model.
    """
```

**Composability**: this is a thin wrapper around
`sentence_transformers.CrossEncoder.predict`. Pure-function (model
state cached at module level — same pattern as cycle #24 eager
preload of bi-encoder).

---

## 5. Gap analysis (follow-up cycles)

| Gap | Severity | Cycle |
|-----|----------|-------|
| **`rerank_candidates` primitive** | MAJOR | cycle 204 — ~60 LOC + TDD strict with mock CrossEncoder fixture |
| **Wire into hot recall path** | MAJOR | cycle 205 — add `rerank_top_k` param to `recall_hybrid`, default OFF (cold path) |
| **Auto-Dream reranks pending tasks** | MEDIUM | cycle 206 — pre-rank the dream cluster candidates |
| **Precomputed rerank column** | LOW | cycle 207 — schema v6 adds `rerank_score` cached column |
| **GPU acceleration probe** | DEFER | cycle 220+ — needs CUDA detection + benchmark |

### 5.1 Acceptance — cycle 204 `rerank_candidates`

- TDD: mock CrossEncoder fixture → predict returns known scores →
  rerank returns ids in known order.
- Empirical: 10 candidates on real corpus → cross-encoder reranks
  in < 200 ms (after warm-up).
- Defensive: model load failure → returns input order unchanged
  (graceful degrade).

### 5.2 Falsifiable hypothesis H6

After enabling cycle-204 rerank on top-K=20 candidates from cycle-161
hybrid, recall@5 on a 50-query held-out set improves by ≥ 8% absolute
against hybrid-only baseline. Falsification: gain ≤ 3% → cross-encoder
not worth the 250-500 ms; revert to bi-encoder-only.

---

## 6. Caveat A1 onesti

- This doc is **descriptive + design**; cycle 204-207 are PROPOSED,
  not committed.
- The 125 MB model size for ms-marco-MiniLM-L-12-v2 is from
  Hugging Face Hub — must be confirmed on the operator's disk
  before claiming "lightweight" in production.
- "5-10 ms warm CPU forward pass" is anecdotal — needs real bench
  on Aurelio's hardware (cycle 204).
- The 50-query held-out benchmark (§5.2) DOES NOT EXIST YET — same
  caveat as the cycle-190 / 192 hypotheses. All "X% improvement"
  numbers are pending ground-truth labels.

---

## 7. References

- `engram/semantic.py` — current bi-encoder cosine recall.
- `docs/sota/multi-signal-fusion.md` (cycle 190) — RRF over the
  cross-encoder result as one signal.
- Reimers & Gurevych 2019 — "Sentence-BERT" foundational
  bi-encoder paper.
- Nogueira & Cho 2019 — "Passage Re-ranking with BERT" foundational
  two-stage retrieval paper.
- MTEB Reranking leaderboard — current SOTA benchmark scores.
