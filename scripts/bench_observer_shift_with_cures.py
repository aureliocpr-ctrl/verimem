"""Cycle 330 (2026-05-23) — SOS bench with cure modes enabled.

Tests whether the cure modes (stable_partition, second_pass_louvain,
HYBRID) actually REDUCE the SOS Jaccard distance, not just produce
more emergence candidates.

Per cycle 257-260 finding: second_pass_louvain operates downstream of
the partition layer → no expected SOS-layer change. Per cycle 261:
stable_partition operates AT the partition layer → expected to
collapse Jaccard for unchanged nodes.

Falsifiable predictions:
- vanilla: E baseline (cycle 326 production: +0.078)
- stable_partition: E ≈ 0 for unchanged nodes (cycle 261 test).
  This bench measures whole-partition Jaccard including new nodes.
  Expected E < vanilla / 5.
- second_pass: E ≈ vanilla (no partition-layer change).
- HYBRID: E ≈ stable_partition (HYBRID uses stable as backbone).

Output JSON:
    {
      "n_seeds": int, "k_writes": int, "n_facts_pre": int,
      "modes": [
        {"mode": "vanilla|stable|second_pass|hybrid",
         "baseline_mean": float, "treatment_mean": float, "effect": float,
         "ci": [low, high], "verdict": str}
      ],
      "elapsed_s": float
    }

Usage:
    python -m scripts.bench_observer_shift_with_cures \\
      --semantic-db ~/.engram/semantic/semantic.db --N 10 --k 100 \\
      --auto-copy --output bench_cures.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path


def _partition_to_sets(p) -> list[set[str]]:
    """Convert Partition (from stable_partition) to list[set[str]] format."""
    if hasattr(p, "values_as_sets"):
        return p.values_as_sets()
    if hasattr(p, "node_to_community"):
        # group by community
        groups: dict[str, set[str]] = {}
        for node, comm in p.node_to_community.items():
            groups.setdefault(comm, set()).add(node)
        return list(groups.values())
    return list(p) if isinstance(p, list) else []


def _stable_partition_run(db_path: Path, seed: int, prior=None):
    """Run stable_partition; returns Partition object."""
    from engram.stable_partition import stable_partition
    return stable_partition(db_path, seed=seed, prior_assignment=prior)


def run_bench_mode(semantic_db: Path, mode: str,
                   n_seeds: int, k_writes: int) -> dict:
    """Run observer-shift bench in a single mode.

    Args:
        mode: "vanilla" | "stable" | "second_pass" | "hybrid"
    """
    import sqlite3

    from scripts.bench_observer_shift import (
        _bootstrap_ci,
        _inject_writes,
        _louvain_partition,
        _partition_jaccard,
    )

    conn = sqlite3.connect(str(semantic_db))
    try:
        n_facts_pre = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
        ).fetchone()[0]
    finally:
        conn.close()

    seeds = list(range(1, n_seeds + 1))
    pre_partitions: dict[int, list[set[str]]] = {}
    pre_partition_objs: dict[int, object] = {}

    # Phase 1: pre-write partitions
    if mode == "stable":
        for s in seeds:
            p = _stable_partition_run(semantic_db, seed=s)
            pre_partition_objs[s] = p
            pre_partitions[s] = _partition_to_sets(p)
    else:
        # vanilla / second_pass / hybrid all use plain Louvain at the
        # partition layer; cures operate downstream of partition.
        for s in seeds:
            pre_partitions[s] = _louvain_partition(semantic_db, seed=s)

    # Phase 1.5: baseline (different seeds, same graph)
    baseline_jaccards: list[float] = []
    for i in range(len(seeds)):
        for j in range(i + 1, len(seeds)):
            d = _partition_jaccard(pre_partitions[seeds[i]],
                                    pre_partitions[seeds[j]])
            baseline_jaccards.append(d)

    # Phase 2: inject writes
    _inject_writes(semantic_db, k_writes, seed=99)

    conn = sqlite3.connect(str(semantic_db))
    try:
        n_facts_post = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
        ).fetchone()[0]
    finally:
        conn.close()

    # Phase 3: post-write partitions
    post_partitions: dict[int, list[set[str]]] = {}
    if mode == "stable":
        for s in seeds:
            p = _stable_partition_run(
                semantic_db, seed=s, prior=pre_partition_objs[s],
            )
            post_partitions[s] = _partition_to_sets(p)
    else:
        for s in seeds:
            post_partitions[s] = _louvain_partition(semantic_db, seed=s)

    # Phase 4: paired treatment Jaccards
    treatment_jaccards: list[float] = []
    for s in seeds:
        d = _partition_jaccard(pre_partitions[s], post_partitions[s])
        treatment_jaccards.append(d)

    import numpy as np
    baseline_mean = (
        float(np.mean(baseline_jaccards)) if baseline_jaccards else 0.0
    )
    treatment_mean = (
        float(np.mean(treatment_jaccards)) if treatment_jaccards else 0.0
    )
    effect = treatment_mean - baseline_mean

    paired_effects = [
        t - baseline_mean for t in treatment_jaccards
    ] if treatment_jaccards else []
    ci_low, ci_high = _bootstrap_ci(paired_effects)

    if ci_low > 0 and effect > 0.05:
        verdict = "H1_supported"
    elif ci_high <= 0.05:
        verdict = "H0_supported"
    else:
        verdict = "inconclusive"

    return {
        "mode": mode,
        "n_facts_pre": int(n_facts_pre),
        "n_facts_post": int(n_facts_post),
        "baseline_mean": baseline_mean,
        "treatment_mean": treatment_mean,
        "effect": float(effect),
        "ci": [float(ci_low), float(ci_high)],
        "verdict": verdict,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--semantic-db",
        type=Path,
        default=Path.home() / ".engram" / "semantic" / "semantic.db",
    )
    parser.add_argument("--N", type=int, default=10, dest="n_seeds")
    parser.add_argument("--k", type=int, default=100, dest="k_writes")
    parser.add_argument(
        "--modes", type=str, default="vanilla,stable",
        help="Comma-separated modes to run",
    )
    parser.add_argument("--auto-copy", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not args.semantic_db.exists():
        print(f"[error] DB not found: {args.semantic_db}", file=sys.stderr)
        return 1

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    t_start = time.time()
    all_results = []

    for mode in modes:
        # Each mode runs on a FRESH safe-copy so injections don't pollute
        # the next mode's measurement.
        if args.auto_copy:
            tmp_dir = Path(tempfile.mkdtemp(prefix=f"engram_cure_{mode}_"))
            db = tmp_dir / "semantic.db"
            shutil.copy2(args.semantic_db, db)
        else:
            db = args.semantic_db
            tmp_dir = None

        try:
            print(f"[run] mode={mode}...", file=sys.stderr)
            result = run_bench_mode(db, mode, args.n_seeds, args.k_writes)
            all_results.append(result)
            print(
                f"[done] mode={mode} E={result['effect']:+.4f} "
                f"verdict={result['verdict']}",
                file=sys.stderr,
            )
        finally:
            if tmp_dir is not None:
                shutil.rmtree(tmp_dir, ignore_errors=True)

    payload = {
        "n_seeds": args.n_seeds,
        "k_writes": args.k_writes,
        "modes": all_results,
        "elapsed_s": float(time.time() - t_start),
    }
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
