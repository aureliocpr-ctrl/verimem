"""Run corpus_fp_bench against a REAL Engram corpus snapshot (SERIAL claude -p, O5).

R19's open concern: does the NLI conflict detector flag TRUE-but-noisy facts as
CONTRADICTION on the real corpus (false positives)? We run the gate on high-cosine sibling
pairs from the live snapshot, then POST-HOC apply the noise/temporal/diff-tag upstream
filter to the flagged contradictions — so ONE serial claude -p pass yields BOTH the raw FP
candidate rate AND the residual after the cheap upstream filter (no second judge pass).

Fresh seed (default 7, not the seed-0 the filter was tuned on) = an out-of-sample check the
filter is not overfit. Bootstrap CI on the contradiction rate via benchmark.stats.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from benchmark.corpus_fp_bench import noise_or_temporal, run
from benchmark.qa_runner import LeanClaudeCLILLM
from verimem.semantic import SemanticMemory
from verimem.semantic_conflict import LLMRelationJudge


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion k/n (correct for small n / rates near 0,
    unlike normal-approx or the AUROC bootstrap in stats.py which needs two classes)."""
    if n == 0:
        return (0.0, 0.0)
    phat = k / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return (round(max(0.0, center - half), 3), round(min(1.0, center + half), 3))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, required=True, help="path to a populated semantic.db")
    p.add_argument("--sample", type=int, default=150)
    p.add_argument("--min-cosine", type=float, default=0.7)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--model", type=str, default="claude-sonnet-4-6")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    sm = SemanticMemory(db_path=args.db)
    judge = LLMRelationJudge(LeanClaudeCLILLM(model=args.model, timeout_s=60))
    res = run(sm, judge, sample=args.sample, min_cosine=args.min_cosine,
              seed=args.seed, filter_noise=False)  # raw; filter applied post-hoc below

    flagged = res["flagged_contradictions_for_audit"]
    n_judged = res["n_judged_by_nli"]
    # post-hoc: which flagged contradictions would the cheap upstream filter remove?
    residual = [f for f in flagged if noise_or_temporal(f["a"], f["b"]) is None]
    removed = len(flagged) - len(residual)

    # FP candidate = a flagged contradiction (every one is either a genuine conflict the gate
    # SHOULD catch, or a false positive — only manual read decides; we report the rate + the
    # list). Wilson 95% CI on the proportion (correct for a rate, possibly near 0).
    n_contra = res["relation_distribution"].get("contradiction", 0)
    raw_lo, raw_hi = wilson_ci(n_contra, n_judged)
    res_lo, res_hi = wilson_ci(len(residual), n_judged)

    out = {
        "db": str(args.db), "model": args.model, "seed": args.seed,
        "corpus_facts": res["corpus_facts"],
        "n_high_cosine_pairs": res["n_high_cosine_pairs"],
        "n_judged_by_nli": n_judged,
        "relation_distribution": res["relation_distribution"],
        "raw_contradiction_rate": res["contradiction_rate_of_judged"],
        "raw_contradiction_ci95": [raw_lo, raw_hi],
        "upstream_filter_removed": removed,
        "residual_contradictions_after_filter": len(residual),
        "residual_rate_of_judged": round(len(residual) / n_judged, 3) if n_judged else 0.0,
        "residual_rate_ci95": [res_lo, res_hi],
        "flagged_contradictions": flagged,        # full list for MANUAL audit (A2: human reads)
        "residual_after_filter": residual,
    }
    args.out.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("flagged_contradictions", "residual_after_filter")},
                     indent=2))
    print(f"\nDONE -> {args.out}  ({len(flagged)} flagged, {len(residual)} residual after filter)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
