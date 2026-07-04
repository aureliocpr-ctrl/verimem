"""Cycle 319 (2026-05-23) — SOS effect scaling law by corpus size.

Empirical question: does the structural observer-shift effect $E$
scale with corpus size $N$? B4 ANTICONFORMISMO SCIENTIFICO falsifiable
predizione: $E$ decreases monotonically with $N$ at fixed $k$ writes,
because the ratio $k/N \to 0$ dilutes the partition perturbation.

Counter-hypothesis: $E$ stays flat (SOS is a structural property
not a ratio property) — then the prediction is falsified.

Protocol:
  1. Subsample alive facts at sizes [500, 1000, 2000, 2400 (all)].
  2. For each size, run bench_observer_shift logic with N_seeds=10
     and k_writes=50 (fixed across sizes for fair comparison).
  3. Extract effect $E_N$ + bootstrap 95% CI per size.
  4. Test monotonicity: $E_500 > E_1000 > E_2000 > E_full$?

Output JSON schema:
    {
      "sizes": [int],
      "n_seeds": int, "k_writes": int,
      "results": [
        {"size": int, "effect": float, "ci": [low, high],
         "baseline_mean": float, "treatment_mean": float,
         "verdict": "H1_supported|H0_supported|inconclusive"}
      ],
      "monotonic_decrease": bool,
      "elapsed_s": float
    }

Usage:
    python -m scripts.bench_scaling_corpus_size \\
      --semantic-db ~/.engram/semantic/semantic.db \\
      --sizes 500,1000,2000 --N 10 --k 50 \\
      --output bench_scaling_size.json
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path


def _subsample_db(src: Path, dst: Path, target_size: int, *,
                  seed: int = 42) -> int:
    """Copy src DB then thin alive facts to target_size random sample.

    Returns the actual size after subsample (capped at alive count).
    """
    shutil.copy2(src, dst)
    conn = sqlite3.connect(str(dst))
    try:
        # Get alive fact ids
        rows = conn.execute(
            "SELECT id FROM facts WHERE superseded_by IS NULL "
            "AND embedding IS NOT NULL AND length(embedding) > 0"
        ).fetchall()
        ids = [r[0] for r in rows]
        if len(ids) <= target_size:
            return len(ids)
        rng = random.Random(seed)
        keep = set(rng.sample(ids, target_size))
        # Delete rows NOT in keep
        to_delete = [i for i in ids if i not in keep]
        # SQLite has parameter-limit ~32k; chunk if needed
        chunk = 500
        for i in range(0, len(to_delete), chunk):
            batch = to_delete[i:i + chunk]
            placeholders = ",".join("?" * len(batch))
            conn.execute(
                f"DELETE FROM facts WHERE id IN ({placeholders})",
                batch,
            )
        # Also clean causal_edges referencing deleted facts
        try:
            conn.execute(
                "DELETE FROM causal_edges WHERE src NOT IN "
                "(SELECT id FROM facts) OR dst NOT IN "
                "(SELECT id FROM facts)"
            )
        except sqlite3.OperationalError:
            pass  # No causal_edges table
        conn.commit()
        return target_size
    finally:
        conn.close()


def _run_single_size(semantic_db: Path, target_size: int,
                     n_seeds: int, k_writes: int) -> dict:
    """Run observer-shift bench on subsampled DB of given size."""
    from scripts.bench_observer_shift import run_bench
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"engram_scale_{target_size}_"))
    try:
        sub_db = tmp_dir / "semantic.db"
        actual_size = _subsample_db(semantic_db, sub_db, target_size)
        result = run_bench(
            sub_db,
            n_seeds=n_seeds,
            k_writes=k_writes,
            effect_threshold=0.05,
        )
        result["target_size"] = target_size
        result["actual_size"] = actual_size
        return result
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--semantic-db",
        type=Path,
        default=Path.home() / ".engram" / "semantic" / "semantic.db",
    )
    parser.add_argument(
        "--sizes",
        type=str,
        default="500,1000,2000",
        help="Comma-separated target sizes",
    )
    parser.add_argument("--N", type=int, default=10, dest="n_seeds")
    parser.add_argument("--k", type=int, default=50, dest="k_writes")
    parser.add_argument(
        "--k-ratio",
        type=float,
        default=None,
        help="If set, k_writes = max(2, int(size * ratio)) per size. "
             "Overrides --k. Used by cycle 319.2 to test the k/N "
             "constant-ratio hypothesis from cycle 319.1.",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not args.semantic_db.exists():
        print(f"[error] DB not found: {args.semantic_db}", file=sys.stderr)
        return 1

    sizes = [int(s.strip()) for s in args.sizes.split(",") if s.strip()]
    t_start = time.time()
    results = []
    for size in sizes:
        k_for_size = (
            max(2, int(size * args.k_ratio))
            if args.k_ratio is not None
            else args.k_writes
        )
        print(
            f"[run] size={size} k={k_for_size}"
            f"{' (ratio=' + str(args.k_ratio) + ')' if args.k_ratio else ''}...",
            file=sys.stderr,
        )
        r = _run_single_size(
            args.semantic_db, size, args.n_seeds, k_for_size,
        )
        results.append({
            "size": size,
            "k_writes_for_size": k_for_size,
            "actual_size": r.get("actual_size", size),
            "effect": r.get("effect", 0.0),
            "ci": r.get("bootstrap_ci_95", [0.0, 0.0]),
            "baseline_mean": r.get("baseline_mean", 0.0),
            "treatment_mean": r.get("treatment_mean", 0.0),
            "verdict": r.get("verdict", "error"),
            "n_facts_pre": r.get("n_facts_pre", 0),
            "n_facts_post": r.get("n_facts_post", 0),
        })
        print(
            f"[done] size={size} k={k_for_size} effect={r.get('effect', 0.0):.4f} "
            f"verdict={r.get('verdict', 'error')}",
            file=sys.stderr,
        )

    # Monotonic decrease check
    effects = [r["effect"] for r in results]
    monotonic = all(
        effects[i] >= effects[i + 1] for i in range(len(effects) - 1)
    ) if len(effects) >= 2 else None

    payload = {
        "sizes": sizes,
        "n_seeds": args.n_seeds,
        "k_writes": args.k_writes,
        "k_ratio": args.k_ratio,
        "results": results,
        "monotonic_decrease": monotonic,
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
