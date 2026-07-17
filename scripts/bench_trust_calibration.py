"""R&D 2026-06-16 — trust-signal calibration benchmark (judge-free, 100% local).

Reports how well Engram's trust-signal is calibrated, and — the scientific
point — how that calibration depends on how completely Engram observed the
changes in its world. The dial is `unobserved_p`: the fraction of
knowledge-updates Engram never recorded (a fact went obsolete in the world, the
memory never saw it). The Brier-vs-p curve is the argument for a
truth-reconciliation loop: the signal is only as calibrated as its observation.

Run: python scripts/bench_trust_calibration.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from verimem.contradiction import ContradictionStore
from verimem.semantic import SemanticMemory
from verimem.trust_calibration_eval import (
    VERDICT_TO_PROB,
    evaluate_calibration,
    make_calibration_dataset,
    register_contradictions,
)

_NOW = 1_000_000_000.0
_N = 1000
_SEEDS = [1, 2, 3]
_PS = [0.0, 0.25, 0.50, 0.75, 1.0]


def _cell(tmpdir: Path, p: float, seed: int):
    db = tmpdir / f"run_{int(p * 100)}_{seed}.db"
    sm = SemanticMemory(db_path=db)
    cs = ContradictionStore(db)
    ds = make_calibration_dataset(_N, unobserved_p=p, now=_NOW, seed=seed)
    register_contradictions(ds, cs)
    return evaluate_calibration(ds, now=_NOW, contradiction_store=cs, sm=sm)


def main() -> None:
    print("=" * 70)
    print("Trust-signal calibration vs observation completeness")
    print(f"n={_N}/cell, mean of {len(_SEEDS)} seeds, verdict->prob={VERDICT_TO_PROB}")
    print("=" * 70)
    print(f"{'unobserved_p':>12} | {'Brier':>6} | {'ECE':>6} | "
          f"{'over-trust':>10} | {'over-caution':>12}")
    print("-" * 70)
    mid_reliability = None
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        for p in _PS:
            rs = [_cell(tmpdir, p, s) for s in _SEEDS]
            brier = sum(r.brier for r in rs) / len(rs)
            ece = sum(r.ece for r in rs) / len(rs)
            ot = sum(r.over_trust_rate for r in rs) / len(rs)
            oc = sum(r.over_caution_rate for r in rs) / len(rs)
            print(f"{p:>12.2f} | {brier:>6.3f} | {ece:>6.3f} | "
                  f"{ot:>10.3f} | {oc:>12.3f}")
            if p == 0.50:
                mid_reliability = rs[0]
    print("=" * 70)
    print("Reading: over-trust = fraction of TRULY-unreliable facts the signal")
    print("implied >=0.70 (the dangerous, confabulation-enabling error).")
    print("over-caution = fraction of TRULY-reliable facts implied <=0.50.")
    print()
    if mid_reliability is not None:
        print(f"Reliability diagram @ unobserved_p=0.50 (seed {_SEEDS[0]}):")
        print(f"  {'bin':>12} | {'n':>4} | {'mean_pred':>9} | {'frac_reliable':>13}")
        for row in mid_reliability.reliability:
            if row["n"]:
                print(f"  [{row['bin_lo']:.1f},{row['bin_hi']:.1f}) "
                      f"| {row['n']:>4} | {row['mean_pred']:>9.3f} "
                      f"| {row['frac_positive']:>13.3f}")
        print(f"\n  verdict counts @ p=0.50: {mid_reliability.verdict_counts}")


if __name__ == "__main__":
    main()
