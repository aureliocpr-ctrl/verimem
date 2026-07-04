"""Cycle 319.3 (2026-05-23) — multi-subsample bench at fixed corpus size.

Tests the cycle 319.2 open prediction: at fixed corpus size N, the
SOS effect $E$ depends primarily on the baseline Louvain noise of
the resulting topology (a property of the subsampled topology), NOT
on absolute N or k/N ratio.

Protocol:
  1. Fix target_size = 1000 (the cycle 319 sweet-spot where E=+0.055
     was H1-supported and baseline=0.032 was low).
  2. Draw M=5 random subsamples with different sub_seeds (1..5),
     each producing a distinct topology of same size.
  3. For each subsample, run observer-shift bench (N_seed=10, k=50).
  4. Tabulate per-subsample baseline + treatment + effect.
  5. Correlation analysis: Pearson(baseline, effect).

Falsifiable prediction:
  - H_d: baseline noise is the DOMINANT determinant of E at fixed N.
    Predicted: |corr(baseline, E)| > 0.7 (strong negative — high noise
    masks effect).
  - If |corr| < 0.4 → H_d FALSIFIED, baseline noise is not the
    dominant factor.

Output JSON:
    {
      "target_size": int, "n_subsamples": int, "n_seeds": int,
      "k_writes": int,
      "subsamples": [
        {"sub_seed": int, "baseline": float, "treatment": float,
         "effect": float, "ci": [low, high], "verdict": str,
         "n_facts_pre": int}
      ],
      "pearson_corr_baseline_effect": float,
      "effect_range": [min, max],
      "verdict_hd": "H_d_supported|H_d_falsified|inconclusive"
    }

Usage:
    python -m scripts.bench_multi_sample_same_size \\
      --semantic-db ~/.engram/semantic/semantic.db \\
      --size 1000 --M 5 --N 10 --k 50 --output bench_multi.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path


def _pearson(x: list[float], y: list[float]) -> float:
    """Pearson correlation. Returns 0.0 if insufficient variance."""
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y, strict=False))
    dx2 = sum((xi - mx) ** 2 for xi in x)
    dy2 = sum((yi - my) ** 2 for yi in y)
    den = (dx2 * dy2) ** 0.5
    if den < 1e-12:
        return 0.0
    return num / den


def _run_single_sample(semantic_db: Path, target_size: int,
                       sub_seed: int, n_seeds: int,
                       k_writes: int) -> dict:
    """Subsample DB with given sub_seed, then bench observer-shift."""
    from scripts.bench_observer_shift import run_bench
    from scripts.bench_scaling_corpus_size import _subsample_db
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"engram_multisub_{sub_seed}_"))
    try:
        sub_db = tmp_dir / "semantic.db"
        _subsample_db(semantic_db, sub_db, target_size, seed=sub_seed)
        result = run_bench(
            sub_db, n_seeds=n_seeds, k_writes=k_writes,
            effect_threshold=0.05,
        )
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
    parser.add_argument("--size", type=int, default=1000, dest="target_size")
    parser.add_argument("--M", type=int, default=5, dest="n_subsamples")
    parser.add_argument("--N", type=int, default=10, dest="n_seeds")
    parser.add_argument("--k", type=int, default=50, dest="k_writes")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not args.semantic_db.exists():
        print(f"[error] DB not found: {args.semantic_db}", file=sys.stderr)
        return 1

    t_start = time.time()
    subsamples = []
    for sub_seed in range(1, args.n_subsamples + 1):
        print(f"[run] sub_seed={sub_seed}...", file=sys.stderr)
        r = _run_single_sample(
            args.semantic_db, args.target_size,
            sub_seed, args.n_seeds, args.k_writes,
        )
        subsamples.append({
            "sub_seed": sub_seed,
            "baseline": r.get("baseline_mean", 0.0),
            "treatment": r.get("treatment_mean", 0.0),
            "effect": r.get("effect", 0.0),
            "ci": r.get("bootstrap_ci_95", [0.0, 0.0]),
            "verdict": r.get("verdict", "error"),
            "n_facts_pre": r.get("n_facts_pre", 0),
            "n_facts_post": r.get("n_facts_post", 0),
        })
        print(
            f"[done] sub_seed={sub_seed} baseline={r.get('baseline_mean', 0):.4f} "
            f"effect={r.get('effect', 0):.4f} {r.get('verdict', '')}",
            file=sys.stderr,
        )

    baselines = [s["baseline"] for s in subsamples]
    effects = [s["effect"] for s in subsamples]
    corr = _pearson(baselines, effects)

    # Verdict H_d: |corr| > 0.7 → supported, < 0.4 → falsified
    abs_corr = abs(corr)
    if abs_corr > 0.7:
        verdict_hd = "H_d_supported"
    elif abs_corr < 0.4:
        verdict_hd = "H_d_falsified"
    else:
        verdict_hd = "inconclusive"

    payload = {
        "target_size": args.target_size,
        "n_subsamples": args.n_subsamples,
        "n_seeds": args.n_seeds,
        "k_writes": args.k_writes,
        "subsamples": subsamples,
        "pearson_corr_baseline_effect": float(corr),
        "effect_range": [min(effects), max(effects)] if effects else [0, 0],
        "baseline_range": [min(baselines), max(baselines)] if baselines else [0, 0],
        "verdict_hd": verdict_hd,
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
