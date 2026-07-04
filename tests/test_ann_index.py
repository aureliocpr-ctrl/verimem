"""ANN (HNSW) index for global recall at scale — brute-force is O(N) and dies
past ~100k facts. Ported from the validated arch-lab prototype (recall-pool
->~1.0 with oversample), with the piece SCALE.md flagged as the hard part:
INCREMENTAL add (faiss IndexHNSWFlat.add appends without a full rebuild).

The ANN returns a candidate POOL (k*oversample); the live recall path then
applies the exact same cosine/decay/status/valid-time filters + fusion + rerank
+ write-gate INSIDE the pool — so ANN swaps only the top-k selection, never the
trust logic. Gated: below _ANN_MIN_N brute-force wins (no build/sync overhead).
"""
from __future__ import annotations

import numpy as np
import pytest

faiss = pytest.importorskip("faiss")

from engram.ann_index import ANNIndex, should_use_ann


def _unit(rng, n, d=768):
    m = rng.standard_normal((n, d)).astype(np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def test_gating_threshold():
    assert should_use_ann(200_000, enabled=True) is True
    assert should_use_ann(50_000, enabled=True) is False   # brute-force wins
    assert should_use_ann(200_000, enabled=False) is False  # opt-in only


def test_pool_recall_recovers_true_topk():
    """The oversampled pool must contain the true brute-force top-k (the
    prototype's verdict: recall-in-pool -> ~1.0)."""
    rng = np.random.default_rng(0)
    corpus = _unit(rng, 3000)
    idx = ANNIndex(corpus, ef_search=128)
    K = 8
    hits = 0
    for i in rng.choice(3000, 50, replace=False):
        q = corpus[i]
        true_topk = set(np.argpartition(-(corpus @ q), K)[:K].tolist())
        pool = set(idx.query(q, K, oversample=8).tolist())
        hits += len(true_topk & pool) / K
    assert hits / 50 >= 0.95   # pool recall ~1.0


def test_query_returns_k_times_oversample():
    rng = np.random.default_rng(1)
    idx = ANNIndex(_unit(rng, 500))
    out = idx.query(_unit(rng, 1)[0], k=5, oversample=4)
    assert len(out) == 20


def test_incremental_add_finds_new_vectors_without_rebuild():
    """The hard part (SCALE.md): a new fact must be findable after .add(),
    without rebuilding the whole index."""
    rng = np.random.default_rng(2)
    idx = ANNIndex(_unit(rng, 1000))
    assert idx.size == 1000
    newv = _unit(rng, 5)
    idx.add(newv)
    assert idx.size == 1005
    # each freshly-added vector is its own nearest neighbour
    for j in range(5):
        pool = idx.query(newv[j], k=1, oversample=4).tolist()
        assert 1000 + j in pool


def test_empty_and_tiny_are_safe():
    rng = np.random.default_rng(3)
    idx = ANNIndex(_unit(rng, 3))
    out = idx.query(_unit(rng, 1)[0], k=8, oversample=4)
    assert len(out) >= 1  # never crashes on k>size
