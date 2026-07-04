# SOTA — Embedding compression for memory scale (HippoAgent)

**Status**: documentation; NEW (no pre-existing task id).
**Date**: 2026-05-23 (cycle 206).
**Scope**: gap analysis on **reducing the disk + RAM footprint** of
the per-fact 384-dim float32 embeddings as the corpus grows beyond
a handful of thousand entries. Companion to the SOTA quintet
180/185/188/190/192/203.

---

## 1. Motivation

HippoAgent stores one embedding per alive fact as a float32 blob in
the `embedding` column. Current numbers (cycle 179 audit):

- 1672 alive facts × 1536 bytes = **2.57 MB** raw embedding payload.
- semantic.db total = ~7.5 MB (so embeddings are ~34% of disk).
- Cycle 179 BLAS bench: cosine top-K on 1.7k vectors = 0.14 ms p50.

Scaling proportions:
- 10k facts → ~15 MB embedding payload + ~5 ms cosine.
- 100k facts → **150 MB** payload + ~50 ms cosine.
- 1M facts → 1.5 GB payload + ~500 ms cosine.

The corpus is small TODAY but the trajectory (Auto-Dream + skill
synthesis + multi-agent collaboration) suggests reaching 10-100k
facts within months. The **memory wall** is real, the **CPU wall**
is real, both are tractable with embedding compression.

---

## 2. SOTA compression techniques

| Technique | Compression ratio | Recall loss | Library |
|----------|-------------------|-------------|---------|
| **float32 → float16** | 2× | ~0.5% | `np.float16` (stdlib numpy) |
| **float32 → int8 scalar quant** | 4× | 1-2% | `faiss.IndexScalarQuantizer` |
| **Product Quantization (PQ)** | 8-32× | 2-5% | `faiss.IndexIVFPQ` |
| **Binary embeddings (1-bit)** | 32× | 5-15% | `sentence_transformers` quantize |
| **Matryoshka truncation (384→64)** | 6× | 1-3% | Native if model supports it |

**Recommended for HippoAgent**:

1. **Cycle 207** — float16 quantization (simplest, smallest accuracy
   hit). 2× space, sub-1% recall loss. NO new dependency.
2. **Cycle 215** — Matryoshka truncation IF the sentence-transformers
   model used supports it. ms-MiniLM-L6-v2 (current) does NOT — would
   need a model swap.
3. **DEFER** — int8 SQ / PQ / binary embeddings require `faiss` C++
   library (~150 MB binary). Heavy dep, only justified at >100k corpus
   scale.

---

## 3. Backwards-compatibility plan

Two-column schema migration (cycle 207):

```sql
ALTER TABLE facts ADD COLUMN embedding_f16 BLOB;
```

Backfill in batches: read `embedding` (float32) → cast to float16 →
write `embedding_f16`. Keep both columns for one release cycle, then
drop `embedding` in cycle 208.

Read path (cycle 209): prefer `embedding_f16` if present (cast to
float32 in-RAM for cosine), fall back to `embedding`. Cycle 135 sub-
linear invariant remains satisfied because the cast is a single
contiguous numpy view (no copy).

---

## 4. Design — `engram/embedding_quantize.py` (proposed cycle 207)

API sketch:

```python
def quantize_float16(embedding: bytes) -> bytes:
    """Convert a float32 embedding blob to float16. Lossy."""

def dequantize_float16(embedding_f16: bytes) -> bytes:
    """Reverse of quantize_float16. Returns float32 blob."""

def backfill_float16_column(
    semantic_db: Path, *, batch_size: int = 500,
) -> dict[str, int]:
    """Walk facts, populate embedding_f16 where missing."""
```

---

## 5. Gap analysis (follow-up cycles)

| Gap | Severity | Cycle |
|-----|----------|-------|
| **float16 primitive + tests** | MEDIUM | cycle 207 — pure-numpy, ~30 LOC + TDD |
| **Schema v6 migration** | MEDIUM | cycle 208 — ALTER + backfill |
| **Read path swap** | MAJOR | cycle 209 — `_get_corpus_cache` prefers f16 |
| **Recall@k bench: f32 vs f16** | MEDIUM | cycle 210 — synthetic + real, ≥ 99% match required |
| **Matryoshka model swap** | LOW (defer) | cycle 215+ — needs operator opt-in |

### 5.1 Acceptance — cycle 207

- TDD: round-trip `quantize → dequantize` preserves shape + 99% values.
- Empirical: 1.7k-fact backfill < 200 ms.
- Defensive: empty / wrong-size input → return as-is.

### 5.2 Falsifiable hypothesis H7

After cycle-207-209 wiring, recall@5 on the cycle-200 50-query
held-out benchmark drops by ≤ 1% absolute against f32 baseline,
while semantic.db total size drops by ≥ 30%. Falsification: recall
drop > 2% OR size reduction < 25% → keep f32.

---

## 6. Caveat A1 onesti

- Document is **descriptive + design**; cycles 207-210 are PROPOSALS.
- "Sub-1% recall loss" for float16 is community wisdom — needs
  HippoAgent-specific bench (cycle 210).
- All size estimates assume the current ms-MiniLM-L6-v2 model
  (384-dim). If the model changes, the projections change.
- `faiss` deps deferred — even though faiss-cpu is ~150 MB, that's
  larger than ALL current HippoAgent disk footprint. NOT a free
  decision at this scale.

---

## 7. References

- `engram/semantic.py` — current embedding storage path.
- `engram/embedding.py` — encoder wrapper.
- `docs/sota/community-detection-channel-pattern.md` (cycle 185).
- Johnson, Douze, Jegou 2019 — Faiss billion-scale paper.
- Kusupati et al. 2022 — Matryoshka Representation Learning (arxiv
  2205.13147).
- Movshovitz-Attias et al. 2024 — int8 retrieval bench at Cohere.
