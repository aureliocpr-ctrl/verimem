"""Cycle 179 (2026-05-22) — corpus-scale recall latency bench harness.

Synthetic-corpus cosine-similarity recall bench. Probes the cycle-135
sub-linear-scaling invariant (``p50(2k) / p50(500) < 3x``) without
loading the real ``semantic.db`` or sentence-transformers (the
17.7-second cold-start documented in fact ``b0ac1291108f``).

Why synthetic?
--------------
  * Real corpus mutates -> bench numbers drift.
  * sentence-transformers import alone costs ~17s cold (irrelevant
    to the cosine-scaling claim).
  * 384-dim float32 random vectors are *worst-case* for cosine
    similarity (uncorrelated, full-rank), so a latency curve here
    is a conservative upper bound on what the real corpus does.

Implementation
--------------
  1. RNG-deterministic numpy ``standard_normal`` corpus + query
     matrices, L2-normalised so the dot product *is* cosine.
  2. Per-query loop: matmul + ``argpartition`` top-k (the same
     primitive ``SemanticMemory.recall`` uses on the BLAS path).
  3. ``time.perf_counter_ns`` per query, sorted, percentiles.

Pure: no DB, no I/O, no LLM. Subscription-irrelevant -- bench is
about numpy + BLAS, neither of which costs anything.
"""
from __future__ import annotations

import time
from typing import Any

import numpy as np


def run_corpus_scale_bench(
    n_facts: int,
    n_queries: int,
    *,
    k: int = 5,
    seed: int = 42,
    dim: int = 384,
) -> dict[str, Any]:
    """Run a synthetic-corpus cosine-similarity recall bench.

    Args:
        n_facts: number of synthetic facts in the corpus matrix.
        n_queries: number of random query vectors to time.
        k: top-k cap (default 5, matches ``SemanticMemory.recall``).
        seed: numpy RNG seed (default 42) -- both corpus + queries
            derive from this single seed for full reproducibility.
        dim: embedding dimensionality (default 384, matching
            ``sentence-transformers/all-MiniLM-L6-v2``).

    Returns:
        Summary dict with integer counts (``n_facts``, ``n_queries``,
        ``samples_total``) and float-millisecond latency percentiles
        (``p50_ms``, ``p95_ms``, ``p99_ms``, ``mean_ms``, ``max_ms``).
    """
    rng = np.random.default_rng(int(seed))

    corpus = rng.standard_normal(size=(int(n_facts), int(dim))).astype(
        np.float32,
    )
    norms = np.linalg.norm(corpus, axis=1, keepdims=True) + 1e-9
    corpus = corpus / norms

    queries = rng.standard_normal(
        size=(int(n_queries), int(dim)),
    ).astype(np.float32)
    q_norms = np.linalg.norm(queries, axis=1, keepdims=True) + 1e-9
    queries = queries / q_norms

    latencies_ms: list[float] = []
    k_eff = max(1, min(int(k), int(n_facts) - 1))
    for i in range(int(n_queries)):
        q = queries[i]
        t0 = time.perf_counter_ns()
        scores = corpus @ q
        # argpartition gives unordered top-k indices in O(n);
        # argsort on the slice orders them. This matches what
        # SemanticMemory.recall does on the numpy BLAS path.
        top_k_idx = np.argpartition(-scores, k_eff - 1)[:k_eff]
        _ = top_k_idx[np.argsort(-scores[top_k_idx])]
        latencies_ms.append((time.perf_counter_ns() - t0) / 1e6)

    latencies_ms.sort()
    n = len(latencies_ms)
    p95_i = min(n - 1, int(n * 0.95))
    p99_i = min(n - 1, int(n * 0.99))
    return {
        "n_facts": int(n_facts),
        "n_queries": int(n_queries),
        "samples_total": n,
        "p50_ms": float(latencies_ms[n // 2]),
        "p95_ms": float(latencies_ms[p95_i]),
        "p99_ms": float(latencies_ms[p99_i]),
        "mean_ms": float(sum(latencies_ms) / n),
        "max_ms": float(latencies_ms[-1]),
    }


__all__ = ["run_corpus_scale_bench"]
