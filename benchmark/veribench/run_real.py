"""VeriBench real run — NET(λ) trust scores on a REAL external corpus (HaluEval QA).

    python -m benchmark.veribench.run_real --n 200 --tau 0.80

Not the toy demo: this ingests real HaluEval `knowledge` into one crowded store
and scores three systems on the SAME retrieval, over answerable + unanswerable
probes, mapping each to a NET(λ) scorecard:

  * verimem_abstain        — the product, abstention floor τ ON
  * no_abstention_baseline — identical retrieval with τ=0 (never abstains): the
    CONTROLLED stand-in for a coverage-blind / no-floor memory. Isolates the
    EFFECT of abstention with zero embedder/LLM confound.
  * scrambled_control      — validity negative control: query↔fact alignment is
    destroyed (deterministic shuffle) and the system still commits, so CORRECT
    must collapse. If it did not, the headline numbers would be an artifact.

Pre-registered in PREREGISTRATION.md (hypothesis + metric declared before the
run). Deterministic: fixed splits, fixed shuffle seed, model-free scoring. A real
mem0 comparison needs an external LLM key (which this project does not use) — the
adapter is in competitors.py for anyone who wants to run it; the controlled
baseline is the cleaner, confound-free comparison and is what we report.
"""
from __future__ import annotations

import argparse
import json
import random
import tempfile
import time
from pathlib import Path

from benchmark import external_readpath as ext

from .real_axis import outcomes_for_system
from .scoring import scorecard

_RESULTS = Path(__file__).resolve().parents[1] / "results"


def _eval(mem, items, fact_ids, unans_qs, *, tau, k):
    ans = ext.eval_answerable(mem, items, fact_ids, k=k, tau=tau)
    unans = ext.eval_unanswerable(mem, unans_qs, k=k, tau=tau)
    return outcomes_for_system(ans, unans)


def run(*, n: int, tau: float, k: int, corpus: str = "halueval_qa") -> dict:
    items = ext.load_split("heldout", limit=n, prefix=corpus)
    unans_qs = [it["question"]
                for it in ext.load_split("unanswerable", limit=n, prefix=corpus)]
    db = Path(tempfile.mkdtemp()) / "veribench_real.db"
    mem, fact_ids, ingest = ext.build_store(items, db)

    systems: dict[str, dict] = {}
    # 1) product: abstention floor ON
    systems["verimem_abstain"] = scorecard(
        _eval(mem, items, fact_ids, unans_qs, tau=tau, k=k))
    # 2) controlled baseline: same retrieval, NEVER abstains (τ=0)
    systems["no_abstention_baseline"] = scorecard(
        _eval(mem, items, fact_ids, unans_qs, tau=0.0, k=k))
    # 3) validity negative control: destroy query↔fact alignment, keep committing
    scrambled = list(fact_ids)
    random.Random(0).shuffle(scrambled)
    systems["scrambled_control"] = scorecard(
        _eval(mem, items, scrambled, unans_qs, tau=0.0, k=k))

    return {
        "benchmark": "VeriBench/real",
        "corpus": f"{corpus} (heldout + unanswerable-probe, disjoint splits)",
        "n_answerable": len(items), "n_unanswerable": len(unans_qs),
        "tau": tau, "k": k, "ingest": ingest,
        "note": ("no_abstention_baseline is the SAME store/retrieval with τ=0 "
                 "(confound-free stand-in for a no-floor memory); mem0 needs an "
                 "external LLM key not used here."),
        "systems": systems,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--tau", type=float, default=0.80)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--corpus", default="halueval_qa")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    result = run(n=args.n, tau=args.tau, k=args.k, corpus=args.corpus)
    print(json.dumps(result, indent=2))

    s = result["systems"]
    print("\n=== VeriBench/real — NET(λ) on HaluEval "
          f"({result['n_answerable']} answerable + {result['n_unanswerable']} "
          "unanswerable) ===")
    print(f"{'system':<26} {'cover':>6} {'λ=1':>8} {'λ=2':>8} {'λ=5':>8} "
          f"{'λ=10':>8} {'xover':>7}")
    for name, sc in s.items():
        net = sc["net"]
        xo = sc["crossover_lambda"]
        print(f"{name:<26} {sc['coverage']:>6.2f} {net['lambda_1']:>8.3f} "
              f"{net['lambda_2']:>8.3f} {net['lambda_5']:>8.3f} "
              f"{net['lambda_10']:>8.3f} {('∞' if xo is None else f'{xo:.2f}'):>7}")

    _tag = args.corpus.replace("_", "-")
    out = Path(args.out) if args.out else (
        _RESULTS / f"veribench_real_{_tag}_{time.strftime('%Y-%m-%d')}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()
