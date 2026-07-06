"""TrustMem-Bench — the benchmark we impose (generator + deterministic oracles).

Design doc: docs/TRUSTMEM_BENCH_DESIGN.md. This is the first EXECUTABLE piece:
a seeded synthetic generator (personas with dated timelines, updates, traps;
EN+IT) and the axes whose verdict is DETERMINISTIC — measurable with no LLM and
no network (abstention-under-absence, destructive-update, temporal integrity,
GDPR forget, provenance honesty). The LLM-judged axes (answer quality) are
layered on later; keeping the deterministic core LLM-free means anyone can
reproduce the trust scorecard offline with one command.

Credibility guard (design §2): the generator is pure and seeded, so the dataset
is auditable and identical run-to-run; the harness reports the score AS MEASURED
including our own failures.
"""
from __future__ import annotations

import pytest


def test_generator_is_deterministic_and_seeded() -> None:
    from benchmark.trustmem_bench import generate_dataset
    a = generate_dataset(n_personas=5, seed=7)
    b = generate_dataset(n_personas=5, seed=7)
    c = generate_dataset(n_personas=5, seed=8)
    assert a == b, "same seed -> identical dataset (auditable, reproducible)"
    assert a != c, "different seed -> different dataset"


def test_dataset_shape_and_bilingual() -> None:
    from benchmark.trustmem_bench import AXES, generate_dataset
    ds = generate_dataset(n_personas=6, seed=1)
    assert len(ds["personas"]) == 6
    locales = {p["locale"] for p in ds["personas"]}
    assert locales == {"en", "it"}, "EN+IT both present (no memory bench is IT)"
    # every declared deterministic axis has at least one probe
    axes_seen = {q["axis"] for q in ds["probes"]}
    for ax in AXES:
        assert ax in axes_seen, f"axis {ax} has no probe"
    # each probe carries a machine-checkable gold
    for q in ds["probes"]:
        assert "axis" in q and "persona_id" in q and "gold" in q


def test_run_verimem_scorecard_deterministic_axes(tmp_path) -> None:
    """Run the deterministic axes against OUR engine and get a scorecard. These
    verdicts need no LLM: abstain-or-not, a superseded row, an as-of value, a
    resurrection after purge, a provenance dossier — all directly observable."""
    from benchmark.trustmem_bench import generate_dataset, run_verimem
    ds = generate_dataset(n_personas=6, seed=3)
    card = run_verimem(ds, workdir=tmp_path)

    assert set(card["per_axis"]) >= {
        "fabrication_under_absence", "destructive_update",
        "temporal_integrity", "forget_integrity", "provenance_honesty",
        "sycophancy_resistance"}
    # our engine is built to pass these — a regression here is a real defect,
    # so the bench doubles as an integration guard on the trust surfaces.
    for axis, res in card["per_axis"].items():
        assert res["n"] > 0, f"{axis} ran no probes"
        assert res["passed"] == res["n"], (
            f"{axis}: {res['passed']}/{res['n']} — Verimem must pass its own "
            f"deterministic trust axes; failures: {res.get('failures')}")
    assert card["overall"]["passed"] == card["overall"]["n"]


def test_scorecard_reports_failures_honestly() -> None:
    """Design §2: an author who scores 100/100 is not credible. The harness must
    be ABLE to report a real miss — verified by feeding a deliberately broken
    adapter and checking the failure is counted, not swallowed."""
    from benchmark.trustmem_bench import generate_dataset, score_axis
    ds = generate_dataset(n_personas=3, seed=5)
    fab = [q for q in ds["probes"] if q["axis"] == "fabrication_under_absence"]

    # a broken adapter that ALWAYS answers (never abstains) must score 0 here
    def always_answers(_probe):
        return {"abstained": False}

    res = score_axis("fabrication_under_absence", fab, always_answers)
    assert res["passed"] == 0 and res["n"] == len(fab)
    assert res["failures"], "a real miss must be listed, not hidden"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
