"""VeriBench head-to-head: verimem vs the REAL mem0, offline, same corpus + embedder.

    python -m benchmark.veribench.run_mem0 --n 200 --tau 0.80

Closes the "you only measured a strawman baseline" criticism by driving mem0's
actual retrieval stack (Chroma + e5, same model & prefixes as verimem) on the same
HaluEval probes. Three systems, one NET(λ) scale:

  * verimem            — abstention floor τ (as shipped, calibrated)
  * mem0_as_shipped    — mem0 with NO abstention floor (its default): commits a
    nearest neighbour on every unanswerable probe
  * mem0_best_floor    — STEELMAN: mem0 given its own optimal abstention floor
    (swept to maximise mem0's NET(λ=5)). If verimem still leads here, the floor is
    the differentiator AND verimem ships it calibrated; if mem0 catches up, that is
    reported honestly — the floor is the mechanism, and VeriBench measures it.

Deterministic, offline, no API key. Requires mem0 + chromadb (skips with a clear
message otherwise).
"""
from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from benchmark import external_readpath as ext

from . import mem0_adapter as mz
from .real_axis import outcomes_for_system
from .scoring import DEFAULT_LAMBDAS, net_score, scorecard

_RESULTS = Path(__file__).resolve().parents[1] / "results"


def _sweep_best_floor(ans_raw, unans_raw, *, lam=5.0):
    """mem0's own best abstention floor: the one maximising its NET(λ=lam)."""
    best = (None, float("-inf"), None)
    f = 0.0
    while f <= 0.95 + 1e-9:
        ans, unans = mz.rows_at_floor(ans_raw, unans_raw, floor=f)
        net = net_score(outcomes_for_system(ans, unans), lam)
        if net > best[1]:
            best = (round(f, 2), net, (ans, unans))
        f += 0.05
    return best


def run(*, n: int, tau: float, k: int, corpus: str = "halueval_qa") -> dict:
    items = ext.load_split("heldout", limit=n, prefix=corpus)
    unans_qs = [it["question"]
                for it in ext.load_split("unanswerable", limit=n, prefix=corpus)]

    systems: dict[str, dict] = {}

    # verimem — raw scores once, floors applied post-hoc (symmetric with mem0)
    vmem, fact_ids, ingest = ext.build_store(
        items, Path(tempfile.mkdtemp()) / "vm.db")
    v_ans_raw, v_unans_raw = ext.eval_raw(vmem, items, fact_ids, unans_qs, k=k)
    va, vu = mz.rows_at_floor(v_ans_raw, v_unans_raw, floor=tau)
    systems["verimem_tau"] = scorecard(outcomes_for_system(va, vu))
    systems["verimem_tau"]["floor"] = tau
    vbest, _vn, (vba, vbu) = _sweep_best_floor(v_ans_raw, v_unans_raw)
    systems["verimem_best_floor"] = scorecard(outcomes_for_system(vba, vbu))
    systems["verimem_best_floor"]["floor"] = vbest

    # mem0 (real, offline) — same treatment
    m = mz.build_mem0_store(items, Path(tempfile.mkdtemp()) / "mem0")
    ans_raw, unans_raw = mz.eval_raw_mem0(m, items, unans_qs, k=k)
    a0, u0 = mz.rows_at_floor(ans_raw, unans_raw, floor=0.0)
    systems["mem0_as_shipped"] = scorecard(outcomes_for_system(a0, u0))
    mbest, _mn, (ab, ub) = _sweep_best_floor(ans_raw, unans_raw)
    systems["mem0_best_floor"] = scorecard(outcomes_for_system(ab, ub))
    systems["mem0_best_floor"]["floor"] = mbest

    return {
        "benchmark": "VeriBench/mem0-head-to-head",
        "corpus": f"{corpus} (heldout + unanswerable-probe)",
        "n_answerable": len(items), "n_unanswerable": len(unans_qs),
        "verimem_tau": tau, "k": k,
        "embedder": "intfloat/multilingual-e5-base (identical for both)",
        "mem0": {"version": _mem0_version(), "store": "chroma", "infer": False,
                 "note": "same e5 model + query:/passage: prefixes; LLM never "
                         "called (no external key); floor bolted on mem0's own "
                         "score scale, 0 = as shipped."},
        "ingest": ingest, "systems": systems,
    }


def _mem0_version() -> str:
    try:
        import mem0
        return getattr(mem0, "__version__", "?")
    except Exception:  # noqa: BLE001
        return "unavailable"


def _print(result: dict) -> None:
    print(json.dumps(result, indent=2))
    print(f"\n=== VeriBench head-to-head — NET(λ) on {result['corpus']} "
          f"({result['n_answerable']}+{result['n_unanswerable']}), "
          f"same e5 embedder ===")
    print(f"{'system':<20} {'cover':>6} {'r@k':>6} "
          f"{'λ=1':>8} {'λ=2':>8} {'λ=5':>8} {'λ=10':>8} {'xover':>7}")
    for name, sc in result["systems"].items():
        rk = round(sc["correct"] / sc["n"], 3) if sc["n"] else 0.0
        xo = sc["crossover_lambda"]
        tag = f"{name} (f={sc['floor']})" if "floor" in sc else name
        print(f"{tag:<20} {sc['coverage']:>6.2f} {rk:>6.3f} "
              f"{sc['net']['lambda_1']:>8.3f} {sc['net']['lambda_2']:>8.3f} "
              f"{sc['net']['lambda_5']:>8.3f} {sc['net']['lambda_10']:>8.3f} "
              f"{('∞' if xo is None else f'{xo:.2f}'):>7}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--tau", type=float, default=0.80)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--corpus", default="halueval_qa")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if not mz.mem0_available():
        raise SystemExit("mem0 / chromadb not installed — cannot run head-to-head.")
    result = run(n=args.n, tau=args.tau, k=args.k, corpus=args.corpus)
    _print(result)
    _tag = args.corpus.replace("_", "-")
    out = Path(args.out) if args.out else (
        _RESULTS / f"veribench_mem0_{_tag}_{time.strftime('%Y-%m-%d')}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()
