"""ANN auto-enable prerequisite: BACKGROUND build with brute-until-ready.

Iter-23 made ANN byte-identical; the remaining blocker for a default-ON was the
synchronous first build (50s@100k, 690s@1M) stalling the first recall. Background
mode: query_pool never builds inline — it kicks a builder thread and returns None
(caller stays exact brute) until the index for the CURRENT corpus version is
ready. It NEVER serves an index built for a different version (no stale-row
hazard); a version bump triggers a debounced background rebuild.
"""
from __future__ import annotations

import time

import numpy as np
import pytest

faiss = pytest.importorskip("faiss")

from engram.ann_cache import ANNCache


def _unit(n, d=64, seed=0):
    rng = np.random.default_rng(seed)
    m = rng.standard_normal((n, d)).astype(np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def _wait_ready(cache, timeout=10.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not cache.building:
            return True
        time.sleep(0.02)
    return False


def test_background_first_call_returns_none_then_serves() -> None:
    m = _unit(300)
    c = ANNCache(min_n=100)
    assert c.query_pool(m, m[0], k=4, version=1, background=True) is None
    assert _wait_ready(c), "background build never finished"
    pool = c.query_pool(m, m[0], k=4, version=1, background=True)
    assert pool is not None and 0 in pool.tolist()
    assert c.builds == 1


def test_background_never_serves_mismatched_version() -> None:
    m = _unit(300)
    c = ANNCache(min_n=100)
    c.query_pool(m, m[0], k=4, version=1, background=True)
    assert _wait_ready(c)
    m2 = np.vstack([m, _unit(20, seed=9)])
    # version bumped: must NOT serve the v1 index for v2 rows
    assert c.query_pool(m2, m2[0], k=4, version=2, background=True) is None


def test_background_rebuild_is_debounced() -> None:
    m = _unit(300)
    c = ANNCache(min_n=100, rebuild_debounce_s=30.0)
    c.query_pool(m, m[0], k=4, version=1, background=True)
    assert _wait_ready(c)
    # bump version repeatedly: only ONE new build may start within the debounce
    for v in range(2, 8):
        c.query_pool(m, m[0], k=4, version=v, background=True)
    _wait_ready(c)
    assert c.builds <= 2, f"debounce failed: {c.builds} builds"


def test_below_gate_stays_none_and_never_builds() -> None:
    m = _unit(50)
    c = ANNCache(min_n=100)
    assert c.query_pool(m, m[0], k=4, version=1, background=True) is None
    assert c.builds == 0 and not c.building


def test_synchronous_path_unchanged() -> None:
    m = _unit(300)
    c = ANNCache(min_n=100)
    pool = c.query_pool(m, m[0], k=4, version=1)   # no background flag
    assert pool is not None and c.builds == 1
