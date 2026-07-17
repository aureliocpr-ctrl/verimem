"""ANN-vs-brute scale bench for the facts-recall hot path — the tracked,
reproducible generator behind benchmark/results/ann_scale_bench.json (the
8x@100k / 27x@500k claim). Builds a faiss HNSW index over N unit vectors, times
brute-force (cosine_matrix + argsort top-k) vs the ANN query, and measures
recall-in-pool (does the oversampled ANN pool contain the exact top-k). Pure
numpy + faiss — no DB, no model, no LLM, no claude -p — hermetic and throttle-safe.
OOM-safe: a scale that does not fit records an error row and continues.

Run: python -m benchmark.ann_recall_scale_bench --ns 100000,500000,1000000 \
       --dim 768 --out benchmark/results/ann_scale_bench.json
"""
from __future__ import annotations

import argparse
import gc
import json
import time
from pathlib import Path

import numpy as np

from verimem.ann_index import ANNIndex
from verimem.embedding import cosine_matrix


def _unit(n: int, dim: int, rng: np.random.Generator) -> np.ndarray:
    m = rng.standard_normal((n, dim)).astype(np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-8
    return m


def _clustered(n: int, dim: int, rng: np.random.Generator, *,
               n_centers: int | None = None, spread: float = 0.12) -> np.ndarray:
    """Corpus WITH neighborhood structure — points drawn around unit centers, like
    a real semantic embedding corpus. Uniform-random unit vectors have NO nearest-
    neighbor structure in high dim (all ~equidistant), so ANN recall on them is a
    curse-of-dimensionality artifact (measured 0.42), NOT the recall on a real
    corpus. Latency/speedup is ~data-agnostic; recall is not — so the scale bench
    must use structured data to report a representative recall-in-pool."""
    n_centers = n_centers or max(8, n // 200)
    centers = _unit(n_centers, dim, rng)
    idx = rng.integers(0, n_centers, size=n)
    m = centers[idx] + spread * rng.standard_normal((n, dim)).astype(np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-8
    return m


def _brute_topk(q, corpus, k: int):
    return np.argsort(-cosine_matrix(q, corpus))[:k]


def _recall_in_pool(index, corpus, *, k: int, oversample: int, trials: int, rng) -> float:
    """Fraction of the exact brute-force top-k that the ANN pool contains, over
    `trials` random in-corpus queries, using a PREBUILT index (no rebuild)."""
    hits = tot = 0
    n = corpus.shape[0]
    for i in rng.choice(n, size=min(trials, n), replace=False):
        true_top = set(_brute_topk(corpus[i], corpus, k).tolist())
        pool = set(index.query(corpus[i], k, oversample=oversample).tolist())
        hits += len(true_top & pool)
        tot += len(true_top)
    return hits / tot if tot else 0.0


def recall_at_k_in_pool(corpus, *, k: int, oversample: int, trials: int, rng) -> float:
    """Build an index over `corpus` and measure recall-in-pool (standalone helper
    for tests). This is the invariant the speedup rides on: if the pool holds the
    exact top-k, the downstream exact filters/rerank pick the identical facts."""
    return _recall_in_pool(ANNIndex(corpus), corpus, k=k, oversample=oversample,
                           trials=trials, rng=rng)


def bench_one(n: int, *, dim: int, k: int, trials: int, oversample: int, rng) -> dict:
    corpus = _clustered(n, dim, rng)   # structured corpus -> representative recall
    q = corpus[int(rng.integers(0, n))]  # an in-corpus query has real neighbors
    _ = np.argsort(-cosine_matrix(q, corpus))[:k]                # warmup (BLAS spin-up)
    bl = []
    for _ in range(trials):
        t0 = time.perf_counter()
        _ = np.argsort(-cosine_matrix(q, corpus))[:k]
        bl.append((time.perf_counter() - t0) * 1000.0)
    t0 = time.perf_counter()
    index = ANNIndex(corpus)
    build_s = time.perf_counter() - t0
    _ = index.query(q, k, oversample=oversample)                # warmup
    al = []
    for _ in range(trials):
        t0 = time.perf_counter()
        _ = index.query(q, k, oversample=oversample)
        al.append((time.perf_counter() - t0) * 1000.0)
    rip = _recall_in_pool(index, corpus, k=k, oversample=oversample,
                          trials=min(40, n), rng=rng)
    bl.sort(); al.sort()
    b50, a50 = bl[len(bl) // 2], al[len(al) // 2]
    del corpus, index
    gc.collect()
    return {
        "n": n, "dim": dim, "k": k, "oversample": oversample,
        "brute_p50_ms": round(b50, 3), "ann_p50_ms": round(a50, 3),
        "speedup": round(b50 / a50, 1) if a50 else None,
        "recall_in_pool": round(rip, 4), "build_s": round(build_s, 1),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", default="100000,500000,1000000")
    ap.add_argument("--dim", type=int, default=768)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--oversample", type=int, default=8)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    rng = np.random.default_rng(7)
    ns = [int(x) for x in a.ns.split(",") if x.strip()]
    rows: list[dict] = []
    print(f"ANN-vs-brute scale  dim={a.dim} k={a.k} oversample={a.oversample} trials={a.trials}")
    print(f"{'N':>10} {'brute_ms':>9} {'ann_ms':>8} {'speedup':>8} {'recall':>7} {'build_s':>8}")
    for n in ns:
        try:
            r = bench_one(n, dim=a.dim, k=a.k, trials=a.trials,
                          oversample=a.oversample, rng=rng)
        except MemoryError:
            print(f"{n:>10} {'OOM':>9}")
            rows.append({"n": n, "error": "OOM"})
            gc.collect()
            continue
        rows.append(r)
        print(f"{r['n']:>10} {r['brute_p50_ms']:>9} {r['ann_p50_ms']:>8} "
              f"{str(r['speedup']) + 'x':>8} {r['recall_in_pool']:>7} {r['build_s']:>8}")
    out = {
        "config": {"dim": a.dim, "k": a.k, "oversample": a.oversample,
                   "trials": a.trials, "seed": 7},
        "rows": rows,
        "note": "SPEEDUP is the scale claim (brute cosine+argsort O(N) vs faiss HNSW "
                "sublinear query); it is ~data-agnostic and reproducible. recall_in_pool "
                "here is on SYNTHETIC clustered data = a sanity signal ONLY (synthetic "
                "geometry is not a faithful proxy for real-corpus recall); real-corpus "
                "behaviour-preservation (same top-k on e5) is proven in "
                "tests/test_ann_recall_equivalence.py. Pure numpy+faiss, seeded, OOM-safe.",
    }
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
