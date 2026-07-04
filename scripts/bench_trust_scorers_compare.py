"""R&D 2026-06-16 — compare three trust scorers on the SAME ground-truth.

  1. categorical      : the shipped trust-signal (verdict -> VERDICT_TO_PROB).
  2. continuous (R14)  : the shipped compute_trust_score (confidence * age_decay
                         * corroboration) — IGNORES supersession & contradictions.
  3. calibrated proto  : supersession + contradictions (like the signal) BUT no
                         age cliff for verified facts (the over-caution fix).

Two worlds: observed (unobserved_p=0) and half-blind (0.5). Judge-free, local.
Run: python scripts/bench_trust_scorers_compare.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from engram.contradiction import ContradictionStore
from engram.semantic import SemanticMemory
from engram.trust_calibration_eval import (
    evaluate_calibration,
    make_calibration_dataset,
    register_contradictions,
)
from engram.trust_score import compute_trust_score

_NOW = 1_000_000_000.0
_N = 1000
_SEEDS = [1, 2, 3]
_PS = [0.0, 0.5]


def _make_existing_scorer():
    def score(fact):
        return compute_trust_score(fact, now=_NOW)["trust"]
    return score


def _make_calibrated_scorer(cs):
    def score(fact):
        if getattr(fact, "superseded_by", None):
            return 0.02
        n = len(cs.list_unresolved_for_fact(fact.id))
        if n > 0:
            return max(0.05, 0.25 / (1 + n))
        status = getattr(fact, "status", "model_claim")
        if status == "verified":
            return 0.92          # age does NOT penalize a verified fact
        if status == "legacy_unverified":
            return 0.35
        return min(0.85, max(0.05, float(fact.confidence)))
    return score


def _avg(rs, attr):
    return sum(getattr(r, attr) for r in rs) / len(rs)


def _cell(tmpdir, p, seed, which):
    db = tmpdir / f"{which}_{int(p * 100)}_{seed}.db"
    sm = SemanticMemory(db_path=db)
    cs = ContradictionStore(db)
    ds = make_calibration_dataset(_N, unobserved_p=p, now=_NOW, seed=seed)
    register_contradictions(ds, cs)
    scorer = None
    if which == "existing":
        scorer = _make_existing_scorer()
    elif which == "calibrated":
        scorer = _make_calibrated_scorer(cs)
    return evaluate_calibration(
        ds, now=_NOW, contradiction_store=cs, sm=sm, scorer=scorer)


def main() -> None:
    scorers = ["categorical", "existing", "calibrated"]
    print("=" * 78)
    print(f"Trust scorer comparison — same ground-truth, n={_N}, {len(_SEEDS)} seeds")
    print("=" * 78)
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        for p in _PS:
            world = "observed" if p == 0.0 else "half-blind"
            print(f"\n-- world: {world} (unobserved_p={p}) --")
            print(f"{'scorer':>12} | {'Brier':>6} | {'ECE':>6} | "
                  f"{'over-trust':>10} | {'over-caution':>12}")
            print("-" * 64)
            for which in scorers:
                rs = [_cell(tmpdir, p, s, which) for s in _SEEDS]
                print(f"{which:>12} | {_avg(rs, 'brier'):>6.3f} | "
                      f"{_avg(rs, 'ece'):>6.3f} | "
                      f"{_avg(rs, 'over_trust_rate'):>10.3f} | "
                      f"{_avg(rs, 'over_caution_rate'):>12.3f}")
    print("\nLower is better on all four. over-trust is the dangerous one.")


if __name__ == "__main__":
    main()
