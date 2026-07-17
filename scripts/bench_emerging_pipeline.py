"""Cycle 226 (2026-05-23) — empirical bench: emergence + draft pipeline.

Measures latency of the cycle 213 + 217 chain on the live corpus.
Writes a summary JSON under ``~/.engram/bench_emerging_pipeline.json``
for cross-session comparison.

Usage::

    python -m scripts.bench_emerging_pipeline [N]

Default N = 20 trials. Each trial:

  1. detect_emerging_skills (Louvain + topic purity + cohesion)
  2. draft_skill_from_community over the returned candidates

Outputs p50 / p95 / p99 / mean / min / max in milliseconds + the
number of candidates / drafts produced.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any


def _percentile(samples_sorted: list[float], p: float) -> float:
    if not samples_sorted:
        return 0.0
    n = len(samples_sorted)
    idx = max(0, min(n - 1, int(round((p / 100.0) * (n - 1)))))
    return samples_sorted[idx]


def run_bench(n_trials: int, *, db_path: Path) -> dict[str, Any]:
    from verimem.skill_drafter import draft_skill_from_community
    from verimem.skill_emergence_detector import detect_emerging_skills

    latencies_ms: list[float] = []
    n_candidates_seen: list[int] = []
    n_drafts_seen: list[int] = []
    for _ in range(int(n_trials)):
        t0 = time.perf_counter_ns()
        candidates = detect_emerging_skills(
            db_path, min_community_size=4, min_topic_purity=0.4,
            min_cohesion=0.1, max_n=5,
        )
        drafts = [
            draft_skill_from_community(db_path, c) for c in candidates
        ]
        elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        latencies_ms.append(elapsed_ms)
        n_candidates_seen.append(len(candidates))
        n_drafts_seen.append(len(drafts))
    samples = sorted(latencies_ms)
    return {
        "n_trials": int(n_trials),
        "db_path": str(db_path),
        "latency_ms": {
            "p50": _percentile(samples, 50),
            "p95": _percentile(samples, 95),
            "p99": _percentile(samples, 99),
            "mean": statistics.fmean(samples) if samples else 0.0,
            "min": samples[0] if samples else 0.0,
            "max": samples[-1] if samples else 0.0,
        },
        "candidates": {
            "min": min(n_candidates_seen) if n_candidates_seen else 0,
            "max": max(n_candidates_seen) if n_candidates_seen else 0,
            "mean": statistics.fmean(n_candidates_seen) if n_candidates_seen else 0.0,
        },
        "drafts": {
            "min": min(n_drafts_seen) if n_drafts_seen else 0,
            "max": max(n_drafts_seen) if n_drafts_seen else 0,
            "mean": statistics.fmean(n_drafts_seen) if n_drafts_seen else 0.0,
        },
        "timestamp": time.strftime(
            "%Y-%m-%dT%H:%M:%S",
            time.localtime(),
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("n_trials", type=int, nargs="?", default=20)
    parser.add_argument(
        "--db",
        default=str(Path.home() / ".engram" / "semantic" / "semantic.db"),
    )
    parser.add_argument(
        "--out",
        default=str(
            Path.home() / ".engram" / "bench_emerging_pipeline.json",
        ),
    )
    args = parser.parse_args(argv)

    db = Path(args.db)
    if not db.exists():
        print(f"DB not found: {db}", file=sys.stderr)
        return 2

    summary = run_bench(args.n_trials, db_path=db)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
