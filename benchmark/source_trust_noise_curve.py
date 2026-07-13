"""Honest-noise robustness curve for the real-corpus trust reproduction (fork B,
"irrobustisci il regime del rumore" — Aurelio 2026-07-13).

The single-point finding (source_trust_realcorpus, noise=0.15) showed the
consistency channel degrading under honest write-noise. MECHANISM (verified in the
numbers, not assumed): 2+ honest sources slipping on the same key are GENUINELY
independent witnesses of a falsehood — no independence/deconfound test can filter
them, because they are not colluders; they are honest errors. That is the
consistency channel's DECLARED hole, and the product already ships its cover: the
OUTCOME channel (observe_outcome, trust = min(channels)) — the Vivarium
"complementarity" law. This sweep measures both curves on real HaluEval content:

  OFF            no trust               (baseline liar recall)
  DECONF         consistency-only       (independence + P88 deconfound)
  DECONF+OUT     the full product policy (both channels, min combination)

PRE-REGISTERED (2026-07-13, before any sweep run — see curve_verdict):
  H2 no-inversion   honest > cartel under DECONF at EVERY (noise, seed) point;
  H3 outcome-rescue for noise <= 0.20: wrong_liar(DECONF+OUT) <= 0.5*OFF and the
                    worst deceiver's min-channel trust < 0.25 (retro-demotion armed).
  noise = 0.25 is reported, not claimed. Declared assumption: outcome exists only
  where use reveals truth; without use-feedback the DECONF curve is the honest one.

    python -m benchmark.source_trust_noise_curve --seed 11
    python -m benchmark.source_trust_noise_curve --aggregate   # after all seeds
"""
from __future__ import annotations

import argparse
import json
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from benchmark.source_trust_realcorpus import (
    RealCorpusConfig,
    curve_verdict,
    load_corpus,
    run_condition,
)

RESULTS_DIR = Path(__file__).parent / "results"
_CORPUS = Path(__file__).parent / "data" / "external" / "halueval_qa_heldout.jsonl"
NOISES = (0.0, 0.05, 0.10, 0.15, 0.20, 0.25)
_STAMP = "2026-07-13"


def _per_seed_path(seed: int) -> Path:
    return RESULTS_DIR / f"source_trust_noise_curve_seed{seed}_{_STAMP}.json"


def run_seed(seed: int, *, n_keys: int = 40) -> list[dict]:
    # MEASUREMENT REGIME (declared): CE rerank OFF for the whole sweep. The
    # cross-encoder becomes resident on a background thread, so whether a given
    # query is reranked depends on process timing/CPU load — observed as
    # wl_off 0.25 vs 0.425 on the SAME seed between a solo and a contended run.
    # Bi-encoder-only makes every condition and seed comparable and reproducible.
    import os
    os.environ["ENGRAM_RECALL_RERANK"] = "0"
    points: list[dict] = []
    for noise in NOISES:
        facts = load_corpus(str(_CORPUS), n=n_keys, seed=seed)
        cfg = RealCorpusConfig(cartel_keys=8, n_colluders=4,
                               p_honest_noise=noise, seed=seed)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            td = Path(td)
            off = run_condition(facts, cfg, td / "o.db", trust_on=False,
                                independence=False, deconfound=False)
            dec = run_condition(facts, cfg, td / "d.db", trust_on=True,
                                independence=True, deconfound=True)
            out = run_condition(facts, cfg, td / "u.db", trust_on=True,
                                independence=True, deconfound=True,
                                outcome_feedback=True)
        points.append({"noise": noise, "seed": seed, "config": asdict(cfg),
                       "off": off, "on_indep_deconf": dec, "deconf_outcome": out})
        wb = out["wrong_by_writer"]
        print(f"seed={seed} noise={noise:.2f} "
              f"wl[off/dec/out]={off['wrong_liar_rate']:.3f}/"
              f"{dec['wrong_liar_rate']:.3f}/{out['wrong_liar_rate']:.3f} "
              f"hon/car(dec)={dec['honest_consistency']:.2f}/"
              f"{dec['cartel_consistency']:.2f} "
              f"liar_min(out)={out['liar_trust_min']:.3f} "
              f"wrong_by(out)=D{wb['deceiver']}/H{wb['honest_slip']}", flush=True)
    RESULTS_DIR.mkdir(exist_ok=True)
    _per_seed_path(seed).write_text(json.dumps(points, indent=2), encoding="utf-8")
    print(f"saved -> {_per_seed_path(seed)}")
    return points


def aggregate(seeds: list[int]) -> dict:
    """Merge per-seed curves; the pre-registered gate judges EVERY point, and the
    per-noise means are reported for the curve table."""
    points: list[dict] = []
    for s in seeds:
        points.extend(json.loads(_per_seed_path(s).read_text(encoding="utf-8")))
    v = curve_verdict(points)
    by_noise: dict[float, list[dict]] = {}
    for p in points:
        by_noise.setdefault(p["noise"], []).append(p)
    table = []
    for noise in sorted(by_noise):
        ps = by_noise[noise]
        m = lambda path: round(  # noqa: E731 — tiny local mean over the seeds
            sum(p[path[0]][path[1]] for p in ps) / len(ps), 4)
        table.append({
            "noise": noise, "n_seeds": len(ps),
            "wrong_liar_off": m(("off", "wrong_liar_rate")),
            "wrong_liar_deconf": m(("on_indep_deconf", "wrong_liar_rate")),
            "wrong_liar_outcome": m(("deconf_outcome", "wrong_liar_rate")),
            "honest_deconf": m(("on_indep_deconf", "honest_consistency")),
            "cartel_deconf": m(("on_indep_deconf", "cartel_consistency")),
            "liar_trust_min_outcome": m(("deconf_outcome", "liar_trust_min")),
        })
    report = {"seeds": seeds, "curve": table, "verdict": v,
              "regime": "ENGRAM_RECALL_RERANK=0 (bi-encoder only, deterministic; "
                        "CE warm-up timing was a measured confound: wl_off 0.25 "
                        "vs 0.425 same-seed between solo and contended runs)",
              "criterion": "PRE-REGISTERED 2026-07-13: H2 honest>cartel (deconf) at "
                           "every point; H3 for noise<=0.20 wrong_liar(out)<=0.5*OFF "
                           "and liar_trust_min<0.25; noise .25 reported not claimed",
              "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    agg = RESULTS_DIR / f"source_trust_noise_curve_agg_{_STAMP}.json"
    agg.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"curve": table, "verdict": v}, indent=2))
    print(f"saved -> {agg}")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--n-keys", type=int, default=40)
    ap.add_argument("--aggregate", action="store_true",
                    help="merge per-seed JSONs and apply the pre-registered gate")
    ap.add_argument("--seeds", default="11,12,13",
                    help="seeds to aggregate (with --aggregate)")
    args = ap.parse_args()
    if args.aggregate:
        aggregate([int(s) for s in args.seeds.split(",")])
    else:
        run_seed(args.seed, n_keys=args.n_keys)


if __name__ == "__main__":
    main()
