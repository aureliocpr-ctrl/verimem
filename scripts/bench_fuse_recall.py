"""Cycle 199 (2026-05-23) — fuse_recall real-corpus micro-benchmark.

Standalone script that probes ``engram.fuse_recall.fuse_recall``
latency + top-K stability on the operator's live ~/.engram/semantic.db.

Run:
    python scripts/bench_fuse_recall.py

Output is to stdout — designed to be captured into a fact via
``hippo_remember`` for audit trails.

Scope cycle 199: a thin instrumentation harness. NO new primitives.
Closes the loop on the cycles 191/196/197 stack with empirical
latency numbers on a 1.7k-fact corpus.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any


def _bench_one(
    *, db_path: Path, label: str, kwargs: dict[str, Any], n_runs: int = 5,
) -> dict[str, Any]:
    from engram.fuse_recall import fuse_recall

    latencies_ms: list[float] = []
    last_out: list[str] = []
    for _ in range(int(n_runs)):
        t0 = time.perf_counter_ns()
        out = fuse_recall(db_path, **kwargs)
        latencies_ms.append((time.perf_counter_ns() - t0) / 1e6)
        last_out = out
    latencies_ms.sort()
    n = len(latencies_ms)
    return {
        "label": label,
        "n_runs": n,
        "p50_ms": latencies_ms[n // 2],
        "p95_ms": latencies_ms[min(n - 1, int(n * 0.95))],
        "min_ms": latencies_ms[0],
        "max_ms": latencies_ms[-1],
        "top_3_ids": last_out[:3],
        "result_count": len(last_out),
    }


def main(db_path: Path | None = None) -> int:
    db = db_path or (Path.home() / ".engram" / "semantic" / "semantic.db")
    if not db.exists():
        sys.stderr.write(f"semantic.db not found at {db}\n")
        return 1

    scenarios = [
        (
            "default_recency_plus_confidence",
            {"limit": 10},
        ),
        (
            "three_signal_with_decayed",
            {
                "limit": 10,
                "enabled_signals": frozenset(
                    {"recency", "confidence", "recency_decayed"}
                ),
            },
        ),
        (
            "only_recency_decayed_14d_half_life",
            {
                "limit": 10,
                "enabled_signals": frozenset({"recency_decayed"}),
                "half_life_days": 14.0,
            },
        ),
        (
            "only_confidence",
            {
                "limit": 10,
                "enabled_signals": frozenset({"confidence"}),
            },
        ),
    ]

    print(f"=== fuse_recall bench on {db} ===")
    print(f"corpus_size={_corpus_size(db)} alive facts")
    print()
    for label, kwargs in scenarios:
        res = _bench_one(
            db_path=db, label=label, kwargs=kwargs, n_runs=5,
        )
        print(
            f"{label}: "
            f"p50={res['p50_ms']:.2f}ms  "
            f"p95={res['p95_ms']:.2f}ms  "
            f"results={res['result_count']}"
        )
        print(f"  top_3: {res['top_3_ids']}")
    return 0


def _corpus_size(db_path: Path) -> int:
    import sqlite3
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
            ).fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()
    except sqlite3.Error:
        return -1


if __name__ == "__main__":
    sys.exit(main())
