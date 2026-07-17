"""Scale probe for the facts-recall hot path: is brute-force ``corpus @ query`` +
argsort actually a bottleneck, and at what N? Measures latency + RSS for the EXACT
op SemanticMemory.recall runs, across N. No DB, no model — pure numpy — so it's
hermetic and throttle-safe. Decides whether ANN is warranted or premature.

Run: python -m benchmark.facts_recall_scale_probe [--dim 1024] [--ns 1000,10000,...]
"""
from __future__ import annotations

import argparse
import gc
import time

import numpy as np

from verimem.embedding import cosine_matrix


def _rss_mb() -> float:
    try:
        import psutil  # type: ignore

        return psutil.Process().memory_info().rss / 1e6
    except Exception:
        return float("nan")


def _normalized(n: int, dim: int, rng: np.random.Generator) -> np.ndarray:
    m = rng.standard_normal((n, dim)).astype(np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-8
    return m


def probe_one(n: int, dim: int, k: int, trials: int, rng: np.random.Generator) -> dict:
    corpus = _normalized(n, dim, rng)
    q = _normalized(1, dim, rng)[0]
    mat_mb = corpus.nbytes / 1e6
    # warmup (BLAS thread spin-up, page-in)
    _ = np.argsort(-cosine_matrix(q, corpus))[:k]
    lat = []
    for _ in range(trials):
        t0 = time.perf_counter()
        sims = cosine_matrix(q, corpus)
        _top = np.argsort(-sims)[:k]
        lat.append((time.perf_counter() - t0) * 1000.0)
    rss = _rss_mb()
    del corpus
    gc.collect()
    lat.sort()
    return {
        "n": n, "matrix_mb": round(mat_mb, 1),
        "p50_ms": round(lat[len(lat) // 2], 2),
        "p95_ms": round(lat[min(len(lat) - 1, int(len(lat) * 0.95))], 2),
        "rss_mb": round(rss, 0),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, default=1024)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--ns", type=str, default="1000,10000,50000,100000,500000,1000000")
    args = ap.parse_args()
    rng = np.random.default_rng(7)
    ns = [int(x) for x in args.ns.split(",")]
    print(f"facts-recall brute-force scale probe  dim={args.dim} k={args.k} trials={args.trials}")
    print(f"{'N':>10} {'matrix_MB':>10} {'p50_ms':>9} {'p95_ms':>9} {'rss_MB':>8}")
    for n in ns:
        try:
            r = probe_one(n, args.dim, args.k, args.trials, rng)
        except MemoryError:
            print(f"{n:>10} {'OOM':>10}")
            continue
        print(f"{r['n']:>10} {r['matrix_mb']:>10} {r['p50_ms']:>9} {r['p95_ms']:>9} {r['rss_mb']:>8}")


if __name__ == "__main__":
    main()
