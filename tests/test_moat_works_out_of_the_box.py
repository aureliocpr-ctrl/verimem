"""The README quickstart's central claim, verified for a user WITHOUT an llm.

README "THE MOAT, live — the reason Verimem exists":
    m.add("Analytics runs on Postgres.", source=src)   # entailed  -> admitted
    r = m.add("Analytics runs on MongoDB.", source=src)  # confab   -> QUARANTINED
    assert r["status"] == "quarantined"

A brand-new user has no llm to pass. The moat MUST still work off the free local
cross-encoder (a core dependency, AUROC ~1.0 on this judgement) — otherwise the
documented quickstart raises AssertionError on first run.

Two bugs this pins (2026-07-18):
  1. default judge backend was "claude" (needs an injected llm) -> with none the
     gate fail-opened and admitted the confab.
  2. the direct-write CE path used the model's shipped gate_config threshold
     (99.641 — absurdly high) instead of a sane entailment cut, so it quarantined
     the TRUE fact too (Postgres, score 99.57).
"""
import tempfile
from pathlib import Path

from verimem.client import Memory


def _mem():
    # These tests exercise the REAL local CE moat judge with no llm. Skip cleanly
    # when the CE model isn't installed (e.g. CI that only warmed the embedding
    # model, not the moat CE at ~/.engram/models/local_gate_ce_v2) — the full
    # suite covers the moat wherever the model IS present. Stub-judge tests below
    # don't call _mem() and run everywhere.
    from verimem.local_grounding import local_ce_available
    if not local_ce_available():
        import pytest
        pytest.skip("local CE moat model not installed (run `verimem warmup` "
                    "or fetch local_gate_ce_v2)")
    return Memory(str(Path(tempfile.mkdtemp()) / "memory.db"))  # NO llm — like a new user


def test_readme_moat_quickstart_without_llm():
    m = _mem()
    src = "We migrated the analytics store to Postgres last quarter."
    a = m.add("Analytics runs on Postgres.", source=src)   # entailed
    r = m.add("Analytics runs on MongoDB.", source=src)    # confab
    # the confab must be quarantined — the exact README assertion
    assert r["status"] == "quarantined", f"moat did not fire: MongoDB status={r['status']!r}"
    # and the TRUE fact must NOT be quarantined by an over-tight threshold
    assert a["status"] != "quarantined", f"moat over-quarantined the true fact: {a['status']!r}"


def test_moat_admits_a_second_entailed_fact_without_llm():
    # guard against "just lower the threshold to 0" — a genuinely entailed but
    # differently-worded fact should still be admitted, a real confab rejected.
    m = _mem()
    src = "The Q3 revenue was 4.2 million euros, up from 3.1 million in Q2."
    ok = m.add("Q3 revenue reached 4.2 million euros.", source=src)   # entailed
    bad = m.add("Q3 revenue collapsed to zero.", source=src)          # confab
    assert ok["status"] != "quarantined", f"entailed fact quarantined: {ok['status']!r}"
    assert bad["status"] == "quarantined", f"confab admitted: {bad['status']!r}"


def test_broken_ce_at_score_time_admits_WITH_advisory_never_silently(monkeypatch):
    """opus review 2026-07-18, blocking finding D: if the CE is advertised present
    but raises at score-time, the write must be admitted WITH an explicit
    L4-skipped advisory — never a silent fail-open. This pins the exact hole the
    first fix left (dead `elif`)."""
    import verimem.anti_confab_gate as gate
    from verimem.grounding_gate import NoGroundingJudge
    # both are imported INSIDE run_validation_gate, so patch them at their source
    # module (the local import resolves the current attribute at call time).
    monkeypatch.setattr("verimem.local_grounding.local_ce_available", lambda: True)

    def _boom(*a, **k):
        raise NoGroundingJudge("simulated CE unloadable at score-time")
    monkeypatch.setattr("verimem.grounding_gate.fact_grounding_score_ex", _boom)

    r = gate.run_validation_gate(
        proposition="Analytics runs on Postgres.",
        verified_by=None, topic=None, agent=None,
        source="We migrated analytics to Postgres last quarter.",
        ground_write=True,
    )
    skips = [w for w in (r.warnings or []) if w.get("layer") == "L4-skipped"]
    assert skips, f"broken CE must leave an L4-skipped advisory, not silence: {r.warnings}"


def test_a_real_ml_fault_in_default_CE_path_propagates():
    """opus re-review 2026-07-18, finding B (round 3): the DEFAULT out-of-the-box
    judge is the local CE. A real INFERENCE fault there (torch RuntimeError: shape
    mismatch / CUDA OOM, model already loaded) must PROPAGATE, never be laundered
    into 'no judge → admit'. A MISSING model still fails over cleanly. This tests
    the REAL default path via try_local_score — not a mock of the wrapper, which
    is where round-2 fooled itself."""
    import pytest

    from verimem.local_grounding import (
        LocalGroundingJudge,
        reset_local_judge,
        set_local_judge,
        try_local_score,
    )

    def _bad_scorer(batch):  # model "loaded" (injected scorer) but inference faults
        raise RuntimeError("CUDA error: device-side assert triggered")
    set_local_judge(LocalGroundingJudge(model_dir="/nonexistent", scorer=_bad_scorer))
    try:
        with pytest.raises(RuntimeError, match="CUDA"):
            try_local_score("We migrated analytics to Postgres.", "Analytics on Postgres.")
    finally:
        reset_local_judge()


def test_a_missing_CE_model_fails_over_cleanly_not_raises():
    """Counterpart: a genuinely ABSENT/unloadable model must NOT raise from
    try_local_score — it fails over to None so the caller degrades to the injected
    llm or the honest L4-skipped advisory. Load-fault ≠ inference-fault."""
    from verimem.local_grounding import (
        LocalGroundingJudge,
        reset_local_judge,
        set_local_judge,
        try_local_score,
    )

    def _load_fails(*_a, **_k):  # _ensure_scorer builds via make_finetuned_scorer
        raise FileNotFoundError("no model on disk")
    j = LocalGroundingJudge(model_dir="/nonexistent")
    j._load_failed = True  # simulate a cached load failure
    set_local_judge(j)
    try:
        assert try_local_score("src", "fact") is None, "missing model must fail over to None"
    finally:
        reset_local_judge()


def test_inference_fault_propagates_END_TO_END_through_the_gate():
    """opus r4 recommendation: blind the catch at anti_confab_gate.py's L4 site
    (only FileNotFoundError/OSError/ImportError/NoGroundingJudge) against
    regression. A CE inference fault on the DEFAULT path must propagate OUT of
    run_validation_gate — not be absorbed into an admit. If someone re-adds
    RuntimeError to that catch, this goes red (the earlier round replaced the
    end-to-end test with try_local_score-only ones, leaving the real site
    un-pinned)."""
    import pytest

    import verimem.anti_confab_gate as gate
    from verimem.local_grounding import (
        LocalGroundingJudge,
        reset_local_judge,
        set_local_judge,
    )

    def _bad_scorer(batch):  # loaded model, inference faults with a REAL ML error
        raise RuntimeError("CUDA error: device-side assert triggered")
    set_local_judge(LocalGroundingJudge(model_dir="/x", scorer=_bad_scorer))
    try:
        with pytest.raises(RuntimeError, match="CUDA"):
            gate.run_validation_gate(
                proposition="Analytics runs on Postgres.",
                verified_by=None, topic=None, agent=None,
                source="We migrated analytics to Postgres last quarter.",
                ground_write=True,
            )
    finally:
        reset_local_judge()


def test_unrelated_confab_is_quarantined_without_llm():
    # a confab on a DIFFERENT subject than the source (not just the grossest
    # Postgres/MongoDB swap) must still be caught by the CE at cut 40.
    m = _mem()
    src = "The maintenance window is scheduled for Saturday at 02:00 UTC."
    bad = m.add("All customer passwords were rotated on Friday.", source=src)
    assert bad["status"] == "quarantined", f"unrelated confab admitted: {bad['status']!r}"


def test_HONEST_LIMIT_ce_does_not_catch_plausible_added_inferences_without_llm():
    """HONEST SCOPE of the CE-only moat (opus re-review 2026-07-18, finding D;
    measured): the local CE scores by topical entailment, not strict "the source
    STATES this". A confab that ADDS a plausible fact the source never asserts
    (latency, "managed", "AWS", "under budget") scores ~96-99 and is ADMITTED at
    any sane cut. The CE moat catches CONTRADICTIONS (MongoDB vs Postgres → 0.6)
    and off-topic confabs, NOT plausible added inferences. An injected llm judge
    is what closes this gap. This test PINS the limit so it is never silently
    claimed away — if a future model catches these, flip the assertion.
    """
    m = _mem()
    src = "We migrated the analytics store to Postgres last quarter."
    # the source says nothing about latency — this is an unsupported inference:
    r = m.add("The migration to Postgres reduced query latency.", source=src)
    assert r["status"] != "quarantined", (
        "CE now catches plausible added inferences — good, update this HONEST_LIMIT "
        f"test and the README scope note. status={r['status']!r}")
