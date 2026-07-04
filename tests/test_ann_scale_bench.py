"""The ANN-vs-brute scale bench is the tracked, reproducible generator for the
scale claim (8x@100k / 27x@500k in benchmark/results/ann_scale_bench.json). Its
correctness invariant — the one the speedup is only meaningful under — is
RECALL-IN-POOL: the ANN candidate pool must almost always contain the exact
brute-force top-k, so the downstream filters/rerank see the same facts. These
tests pin that invariant at a small, fast scale (no 100k build)."""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("faiss")

from benchmark.ann_recall_scale_bench import (
    _clustered,
    bench_one,
    recall_at_k_in_pool,
)


def test_ann_pool_contains_true_topk() -> None:
    rng = np.random.default_rng(0)
    corpus = _clustered(3000, 256, rng)
    r = recall_at_k_in_pool(corpus, k=8, oversample=8, trials=40, rng=rng)
    assert r >= 0.95, "ANN pool must almost always hold the exact top-k"


def test_bench_one_reports_sane_numbers() -> None:
    rng = np.random.default_rng(1)
    r = bench_one(2000, dim=256, k=8, trials=5, oversample=8, rng=rng)
    assert r["n"] == 2000
    assert r["brute_p50_ms"] > 0 and r["ann_p50_ms"] > 0
    assert r["recall_in_pool"] >= 0.9
    assert r["build_s"] >= 0.0
    assert r["speedup"] > 0  # positive ratio (may be <1 at tiny N where brute wins)


def test_recall_in_pool_grows_with_oversample() -> None:
    corpus = _clustered(4000, 256, np.random.default_rng(2))
    # SAME query seed for both so the comparison is fair: a larger oversample pool
    # is a superset of the smaller, so pool-recall is monotone non-decreasing.
    lo = recall_at_k_in_pool(corpus, k=8, oversample=1, trials=30,
                             rng=np.random.default_rng(9))
    hi = recall_at_k_in_pool(corpus, k=8, oversample=8, trials=30,
                             rng=np.random.default_rng(9))
    assert hi >= lo, "more oversampling can only help pool recall"
    assert hi >= 0.95
