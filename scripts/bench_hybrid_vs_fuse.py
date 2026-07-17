"""Cycle 202 (2026-05-23) — bench cycle-161 hybrid vs cycle-197 fuse_recall.

Latency-only comparison (NO recall@k ground truth available yet).
Operator-facing micro-bench on the live ~/.engram/semantic.db corpus.

Run:
    python scripts/bench_hybrid_vs_fuse.py

Notes
-----
* cycle-161 hybrid (``SemanticMemory.recall_hybrid``) needs a query
  string + computes semantic cosine + keyword overlap — uses
  sentence-transformers, paying ~10ms warm-cache cosine.
* cycle-197 fuse_recall (``verimem.fuse_recall.fuse_recall``) uses SQL-
  only signals (recency / confidence / recency_decayed) by default —
  no embedding model required.

So this bench measures the LATENCY trade-off, not the accuracy. A
real recall@k bench needs ground-truth labels (cycle 200+).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path


def _bench_hybrid(
    db_path: Path, queries: list[str], n_runs: int = 3, k: int = 10,
) -> dict:
    from verimem.semantic import SemanticMemory
    sm = SemanticMemory(db_path=db_path)
    # Warm-up (load model).
    sm.recall(queries[0], k=k)

    latencies_ms: list[float] = []
    for _ in range(int(n_runs)):
        for q in queries:
            t0 = time.perf_counter_ns()
            try:
                sm.recall_hybrid(q, k=k)
            except Exception:
                # Older signature variants; skip silently
                continue
            latencies_ms.append((time.perf_counter_ns() - t0) / 1e6)
    if not latencies_ms:
        return {"label": "cycle161_hybrid", "samples": 0, "p50_ms": 0,
                "p95_ms": 0, "mean_ms": 0}
    latencies_ms.sort()
    n = len(latencies_ms)
    return {
        "label": "cycle161_hybrid",
        "samples": n,
        "p50_ms": latencies_ms[n // 2],
        "p95_ms": latencies_ms[min(n - 1, int(n * 0.95))],
        "mean_ms": sum(latencies_ms) / n,
    }


def _bench_fuse(
    db_path: Path, queries: list[str], n_runs: int = 3, k: int = 10,
) -> dict:
    from verimem.fuse_recall import fuse_recall

    latencies_ms: list[float] = []
    for _ in range(int(n_runs)):
        for _q in queries:
            t0 = time.perf_counter_ns()
            fuse_recall(db_path, limit=k)
            latencies_ms.append((time.perf_counter_ns() - t0) / 1e6)
    latencies_ms.sort()
    n = len(latencies_ms)
    return {
        "label": "cycle197_fuse",
        "samples": n,
        "p50_ms": latencies_ms[n // 2],
        "p95_ms": latencies_ms[min(n - 1, int(n * 0.95))],
        "mean_ms": sum(latencies_ms) / n,
    }


def main() -> int:
    db = Path.home() / ".engram" / "semantic" / "semantic.db"
    if not db.exists():
        sys.stderr.write(f"semantic.db not found at {db}\n")
        return 1

    sample_queries = [
        "active learning select_stuck_candidates",
        "cycle 175 dream stuck hook",
        "MCP selective loading prefix filter",
        "Louvain community detection",
        "RRF reciprocal rank fusion",
        "highway nodes betweenness",
        "ghost typing PowerShell",
        "embedding daemon warm-up",
        "Aurelio mandate",
        "anti confab gate L1",
    ]

    print("=== cycle 202 bench: cycle-161 hybrid vs cycle-197 fuse_recall ===")
    print(f"db: {db}")
    print(f"n_queries: {len(sample_queries)}, runs: 3, k: 10")
    print()

    res_hybrid = _bench_hybrid(db, sample_queries)
    res_fuse = _bench_fuse(db, sample_queries)

    print(f"{res_hybrid['label']:20s}  "
          f"p50={res_hybrid['p50_ms']:.2f}ms  "
          f"p95={res_hybrid['p95_ms']:.2f}ms  "
          f"mean={res_hybrid['mean_ms']:.2f}ms  "
          f"samples={res_hybrid['samples']}")
    print(f"{res_fuse['label']:20s}  "
          f"p50={res_fuse['p50_ms']:.2f}ms  "
          f"p95={res_fuse['p95_ms']:.2f}ms  "
          f"mean={res_fuse['mean_ms']:.2f}ms  "
          f"samples={res_fuse['samples']}")

    if res_hybrid["p50_ms"] > 0 and res_fuse["p50_ms"] > 0:
        ratio = res_hybrid["p50_ms"] / res_fuse["p50_ms"]
        print()
        print(f"p50 ratio (hybrid / fuse) = {ratio:.2f}x")
        print("Caveat: latency-only — recall@k accuracy needs ground-truth labels.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
