"""ANNCache — keep one HNSW index alive across recall calls.

The ANN wins only if the index is BUILT ONCE and reused (build is ~52s @100k);
rebuilding per query would be far slower than brute-force. ANNCache holds an
ANNIndex keyed by a caller-supplied corpus VERSION: same version -> reuse;
bumped version -> rebuild (or, when the corpus only grew, incremental add).
Gated: below _ANN_MIN_N it returns None so the caller keeps the exact
brute-force path.
"""
from __future__ import annotations

import numpy as np
import pytest

faiss = pytest.importorskip("faiss")

from engram.ann_cache import ANNCache
from engram.ann_index import _ANN_MIN_N


def _unit(rng, n, d=768):
    m = rng.standard_normal((n, d)).astype(np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def test_gated_below_threshold_returns_none():
    rng = np.random.default_rng(0)
    c = ANNCache()
    assert c.query_pool(_unit(rng, 1000), _unit(rng, 1)[0], k=8, version=1) is None


def test_pool_contains_true_topk_above_threshold():
    rng = np.random.default_rng(1)
    m = _unit(rng, 500)
    c = ANNCache(min_n=100)   # lower gate for the test
    K = 8
    hits = 0
    qs = rng.choice(500, 40, replace=False)
    for i in qs:
        pool = c.query_pool(m, m[i], k=K, oversample=8, version=1)
        assert pool is not None
        true_topk = set(np.argpartition(-(m @ m[i]), K)[:K].tolist())
        hits += len(true_topk & set(pool.tolist())) / K
    assert hits / len(qs) >= 0.95


def test_index_reused_on_same_version_rebuilt_on_bump():
    rng = np.random.default_rng(2)
    m = _unit(rng, 300)
    c = ANNCache(min_n=100)
    c.query_pool(m, m[0], k=4, version=7)
    first = c._idx
    c.query_pool(m, m[1], k=4, version=7)   # same version -> reuse
    assert c._idx is first
    c.query_pool(m, m[2], k=4, version=8)   # bumped -> rebuild
    assert c._idx is not first
    assert c.builds == 2


def test_grow_only_uses_incremental_add_not_rebuild():
    rng = np.random.default_rng(3)
    m = _unit(rng, 300)
    c = ANNCache(min_n=100)
    c.query_pool(m, m[0], k=4, version=1)
    idx0 = c._idx
    m2 = np.vstack([m, _unit(rng, 20)])     # same rows + 20 appended
    pool = c.query_pool(m2, m2[315], k=1, version=2, grew_from=300)
    assert c._idx is idx0            # incremental: same index object
    assert c._idx.size == 320
    assert 315 in pool.tolist()      # the appended vector is findable
    assert c.builds == 1 and c.adds == 1
