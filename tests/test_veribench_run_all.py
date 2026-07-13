"""VeriBench run_all — the single reproducibility entrypoint. Pins the wiring and
the one-liner consolidation without paying for the heavy end-to-end runs (those
are exercised by the real runs + the committed result JSONs)."""
from __future__ import annotations

from benchmark.veribench import run_all


def test_run_all_exposes_the_entrypoint():
    assert callable(run_all.run) and callable(run_all.main)


def test_one_liners_consolidate_every_system():
    stub = {"parts": {
        "mem0_halueval": {"systems": {
            "verimem_tau": {"n": 300, "correct": 182, "coverage": 0.62,
                            "net": {"lambda_5": 0.54}},
            "mem0_as_shipped": {"n": 300, "correct": 200, "coverage": 1.0,
                                "net": {"lambda_5": -1.0}}}}}}
    lines = run_all._one_liners(stub)
    assert len(lines) == 2
    assert any("verimem_tau" in ln and "NET5=+0.540" in ln for ln in lines)
    assert any("mem0_as_shipped" in ln and "NET5=-1.000" in ln for ln in lines)
