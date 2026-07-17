"""Cycle 179 (2026-05-22) — corpus-scale recall latency bench.

Falsifies cycle 135's sub-linear-scaling invariant *empirically* using
synthetic embeddings (no model load, deterministic numpy RNG). Cycle
135 claims ``p50(2k) / p50(500) < 3x`` over the BLAS path. This
cycle adds a pure-function harness so anyone can verify the claim
on their machine without touching the real corpus.

Why not the real ``semantic.db``?
  * It mutates with use → bench numbers drift.
  * Loading sentence-transformers costs ~17s cold-start (fact
    ``b0ac1291108f``); irrelevant to the cosine-scaling claim.
  * Synthetic 384-dim float32 embeddings let us probe orders of
    magnitude (500 / 2k / 8k) on demand.

Contract
--------
``run_corpus_scale_bench(n_facts, n_queries, k=5, seed=42) -> dict``

Returns:
  * ``n_facts``: number of synthetic facts inserted
  * ``n_queries``: number of random queries timed
  * ``p50_ms`` / ``p95_ms`` / ``p99_ms`` / ``mean_ms`` / ``max_ms``
  * ``samples_total``: typically ``n_queries`` (no warm-up duplication)

Deterministic: ``seed`` fixes both the synthetic-corpus matrix and
the query vectors. Same seed → same numbers within numpy noise.

RED marker: ``from verimem.bench_corpus_scale import
run_corpus_scale_bench`` must fail on master.
"""
from __future__ import annotations

# RED MARKER
from verimem.bench_corpus_scale import run_corpus_scale_bench


class TestRunCorpusScaleBench:
    def test_returns_summary_with_required_keys(self) -> None:
        out = run_corpus_scale_bench(n_facts=50, n_queries=10, k=5)
        for key in (
            "n_facts", "n_queries", "p50_ms", "p95_ms", "p99_ms",
            "mean_ms", "max_ms", "samples_total",
        ):
            assert key in out, f"missing key {key!r}: {out}"

    def test_n_facts_n_queries_echoed(self) -> None:
        out = run_corpus_scale_bench(n_facts=100, n_queries=20, k=5)
        assert out["n_facts"] == 100
        assert out["n_queries"] == 20
        assert out["samples_total"] == 20

    def test_latencies_are_positive_floats(self) -> None:
        out = run_corpus_scale_bench(n_facts=50, n_queries=10, k=5)
        for key in ("p50_ms", "p95_ms", "p99_ms", "mean_ms", "max_ms"):
            v = out[key]
            assert isinstance(v, float), f"{key} not float: {type(v)}"
            assert v >= 0.0, f"{key} negative: {v}"

    def test_percentile_ordering(self) -> None:
        """p50 <= p95 <= p99 <= max (within numpy float noise)."""
        out = run_corpus_scale_bench(n_facts=200, n_queries=50, k=5)
        assert out["p50_ms"] <= out["p95_ms"] + 1e-6
        assert out["p95_ms"] <= out["p99_ms"] + 1e-6
        assert out["p99_ms"] <= out["max_ms"] + 1e-6

    def test_deterministic_under_fixed_seed(self) -> None:
        """Same seed → same n_facts/n_queries echoed (synthetic data
        deterministic; latency itself is noisy by nature so we assert
        on structure, not on milliseconds)."""
        a = run_corpus_scale_bench(n_facts=100, n_queries=20, k=5, seed=42)
        b = run_corpus_scale_bench(n_facts=100, n_queries=20, k=5, seed=42)
        assert a["n_facts"] == b["n_facts"]
        assert a["n_queries"] == b["n_queries"]
        assert a["samples_total"] == b["samples_total"]

    def test_scales_to_2k_facts(self) -> None:
        """The cycle-135 invariant claim is bench-able at 2k. Smoke
        test that the harness handles that magnitude without OOM
        or > 30s runtime."""
        import time as _time
        t0 = _time.perf_counter()
        out = run_corpus_scale_bench(
            n_facts=2_000, n_queries=30, k=5, seed=42,
        )
        wall_s = _time.perf_counter() - t0
        assert out["n_facts"] == 2_000
        assert wall_s < 30.0, (
            f"bench took {wall_s:.1f}s on 2k facts -- "
            f"performance regression?"
        )

    def test_k_param_does_not_change_count(self) -> None:
        """``k`` is the top-k cap inside each recall; it MUST NOT
        change how many recall calls we time."""
        out = run_corpus_scale_bench(n_facts=200, n_queries=15, k=10)
        assert out["samples_total"] == 15
