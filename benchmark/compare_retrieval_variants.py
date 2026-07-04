"""Cycle #113.A + #113.C — A/B compare retrieval variants with Wilson CI.

Consuma due eval JSON envelope (baseline + experimental) prodotti
da ``eval_retrieval_with_gt.py`` e applica Wilson CI per dire se la
differenza per-query e' statisticamente significativa.

Binarizziamo le metric per il Wilson CI binomial:

* ``hit_at_1``  := MRR == 1.0 (il primo retrieved e' relevant)
* ``hit_at_5``  := MRR >= 1/5 (almeno 1 relevant nei top-5)
* ``recall_full`` := recall_at_k == 1.0 (tutti i relevant trovati)

Per ogni metric binarizzata, contiamo successi (#query dove vero) e
calcoliamo Wilson CI al 95%. Se gli intervalli baseline e
experimental NON si sovrappongono, la differenza e' significativa.

Per metric continue (P@k, R@k, MRR), riportiamo anche delta means e
una paired-difference confidence interval via normal approximation
(quando n >= 30 il CLT regge per medie di [0,1]).

CLI usage::

    python -m benchmark.compare_retrieval_variants \
        --baseline benchmark/results/eval-baseline.json \
        --experimental benchmark/results/eval-experimental.json \
        --baseline-path facts_cosine_with_legacy \
        --experimental-path facts_rrf_cosine_tokens \
        --output benchmark/results/compare.json
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from benchmark.retrieval_metrics import _z_for_confidence, wilson_ci


def _per_query_metrics(
    eval_envelope: dict[str, Any], path_name: str,
) -> list[dict[str, Any]]:
    """Extract the per_query list for a given path."""
    paths = eval_envelope.get("per_path", {})
    if path_name not in paths:
        raise KeyError(
            f"path {path_name!r} not in eval envelope; "
            f"available: {sorted(paths)}"
        )
    return paths[path_name]["per_query"]


def _binarize(
    per_query: list[dict[str, Any]],
    *,
    metric: str,
    threshold: float = 0.0,
    geq: bool = True,
) -> tuple[int, int]:
    """Count (successes, trials) where ``per_query[i][metric]`` is
    above (geq=True) or at-least-equal-to ``threshold``."""
    trials = len(per_query)
    if geq:
        successes = sum(1 for q in per_query if q.get(metric, 0.0) >= threshold)
    else:
        successes = sum(1 for q in per_query if q.get(metric, 0.0) > threshold)
    return successes, trials


def _mean_with_normal_ci(
    values: list[float], *, confidence: float = 0.95,
) -> dict[str, float]:
    """Mean + normal-approximation CI for the mean of values in [0,1].

    Valid when n >= 30 (CLT regge per medie bounded). For smaller n
    the interval will be returned but the docstring warns the caller.
    """
    if not values:
        return {"mean": 0.0, "ci_lo": 0.0, "ci_hi": 0.0, "n": 0}
    n = len(values)
    mean = statistics.fmean(values)
    if n < 2:
        return {"mean": mean, "ci_lo": mean, "ci_hi": mean, "n": n}
    sd = statistics.stdev(values)
    se = sd / math.sqrt(n)
    z = _z_for_confidence(confidence)
    half = z * se
    return {
        "mean": round(mean, 4),
        "ci_lo": round(max(0.0, mean - half), 4),
        "ci_hi": round(min(1.0, mean + half), 4),
        "n": n,
    }


def _ci_non_overlap(
    lo_a: float, hi_a: float, lo_b: float, hi_b: float,
) -> bool:
    """True if the two intervals do NOT overlap (clear significance)."""
    return hi_a < lo_b or hi_b < lo_a


def compare(
    baseline_per_query: list[dict[str, Any]],
    experimental_per_query: list[dict[str, Any]],
    *,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Run the A/B compare and return the per-metric verdict envelope."""
    if len(baseline_per_query) != len(experimental_per_query):
        # Misalignment is a real bug — refuse to compute.
        raise ValueError(
            f"per_query length mismatch: baseline={len(baseline_per_query)} "
            f"experimental={len(experimental_per_query)}"
        )

    metrics: dict[str, Any] = {}

    # Binary "hit@1" via MRR == 1.0
    for label, mrr_thresh in (("hit_at_1", 1.0), ("hit_at_top5", 0.2)):
        s_b, n_b = _binarize(baseline_per_query, metric="mrr", threshold=mrr_thresh)
        s_e, n_e = _binarize(experimental_per_query, metric="mrr", threshold=mrr_thresh)
        lo_b, hi_b = wilson_ci(s_b, n_b, confidence=confidence)
        lo_e, hi_e = wilson_ci(s_e, n_e, confidence=confidence)
        metrics[label] = {
            "baseline": {
                "successes": s_b, "trials": n_b,
                "rate": round(s_b / n_b, 4) if n_b else 0.0,
                "ci_lo": round(lo_b, 4), "ci_hi": round(hi_b, 4),
            },
            "experimental": {
                "successes": s_e, "trials": n_e,
                "rate": round(s_e / n_e, 4) if n_e else 0.0,
                "ci_lo": round(lo_e, 4), "ci_hi": round(hi_e, 4),
            },
            "delta": round(s_e / n_e - s_b / n_b, 4) if n_b and n_e else 0.0,
            "intervals_non_overlap": _ci_non_overlap(lo_b, hi_b, lo_e, hi_e),
        }

    # Recall@k == 1.0 (full recall — found every relevant)
    s_b, n_b = _binarize(baseline_per_query, metric="recall_at_k", threshold=1.0)
    s_e, n_e = _binarize(experimental_per_query, metric="recall_at_k", threshold=1.0)
    lo_b, hi_b = wilson_ci(s_b, n_b, confidence=confidence)
    lo_e, hi_e = wilson_ci(s_e, n_e, confidence=confidence)
    metrics["recall_full"] = {
        "baseline": {
            "successes": s_b, "trials": n_b,
            "rate": round(s_b / n_b, 4) if n_b else 0.0,
            "ci_lo": round(lo_b, 4), "ci_hi": round(hi_b, 4),
        },
        "experimental": {
            "successes": s_e, "trials": n_e,
            "rate": round(s_e / n_e, 4) if n_e else 0.0,
            "ci_lo": round(lo_e, 4), "ci_hi": round(hi_e, 4),
        },
        "delta": round(s_e / n_e - s_b / n_b, 4) if n_b and n_e else 0.0,
        "intervals_non_overlap": _ci_non_overlap(lo_b, hi_b, lo_e, hi_e),
    }

    # Continuous metric means with normal-approx CI.
    for metric_name in ("precision_at_k", "recall_at_k", "mrr"):
        b_vals = [q[metric_name] for q in baseline_per_query]
        e_vals = [q[metric_name] for q in experimental_per_query]
        b_stat = _mean_with_normal_ci(b_vals, confidence=confidence)
        e_stat = _mean_with_normal_ci(e_vals, confidence=confidence)
        metrics[f"{metric_name}_mean"] = {
            "baseline": b_stat,
            "experimental": e_stat,
            "delta_mean": round(e_stat["mean"] - b_stat["mean"], 4),
            "intervals_non_overlap": _ci_non_overlap(
                b_stat["ci_lo"], b_stat["ci_hi"],
                e_stat["ci_lo"], e_stat["ci_hi"],
            ),
        }

    return {
        "compared_at": time.time(),
        "confidence": confidence,
        "n_queries": len(baseline_per_query),
        "metrics": metrics,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="A/B compare two retrieval eval envelopes with Wilson CI.",
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--experimental", type=Path, required=True)
    parser.add_argument("--baseline-path", required=True)
    parser.add_argument("--experimental-path", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confidence", type=float, default=0.95)
    args = parser.parse_args(argv)

    base_env = json.loads(args.baseline.read_text(encoding="utf-8"))
    exp_env = json.loads(args.experimental.read_text(encoding="utf-8"))
    base_pq = _per_query_metrics(base_env, args.baseline_path)
    exp_pq = _per_query_metrics(exp_env, args.experimental_path)

    result = compare(base_pq, exp_pq, confidence=args.confidence)
    result["baseline_path"] = args.baseline_path
    result["experimental_path"] = args.experimental_path
    result["baseline_file"] = str(args.baseline)
    result["experimental_file"] = str(args.experimental)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote compare envelope to {args.output}")
    print(f"n_queries={result['n_queries']} confidence={result['confidence']}")
    print(f"BASELINE     = {args.baseline_path}")
    print(f"EXPERIMENTAL = {args.experimental_path}")
    print()
    for name, m in result["metrics"].items():
        if "delta" in m:
            sign = "+" if m["delta"] >= 0 else ""
            sig = "  *SIGNIFICANT*" if m["intervals_non_overlap"] else ""
            print(
                f"  {name:24s}  baseline={m['baseline']['rate']:.3f}  "
                f"experimental={m['experimental']['rate']:.3f}  "
                f"delta={sign}{m['delta']:.3f}{sig}"
            )
        elif "delta_mean" in m:
            sign = "+" if m["delta_mean"] >= 0 else ""
            sig = "  *SIGNIFICANT*" if m["intervals_non_overlap"] else ""
            print(
                f"  {name:24s}  baseline={m['baseline']['mean']:.3f}  "
                f"experimental={m['experimental']['mean']:.3f}  "
                f"delta={sign}{m['delta_mean']:.3f}{sig}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
