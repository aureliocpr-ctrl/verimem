"""G5 #3 (RELEASE_GATE): gate-admission monotonicity + per-judge threshold
consistency, property-based.

The 2026-07-02 critic finding was exactly here: a LOCAL-scale score compared
against the claude-scale cut. These properties lock the contract:
(a) admission is MONOTONE in the grounding score — if score s passes, every
    s' > s passes (same config);
(b) the decision flips EXACTLY at resolve_write_threshold_for(judge_used) —
    the threshold of the judge that actually scored, never another scale's;
(c) an env threshold override wins for every backend.

The grounding call is mocked (score injected); no models load.
"""
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

import engram.grounding_gate as gg
from engram.anti_confab_gate import run_validation_gate


def _gate_with_score(monkeypatch, score: float, judge: str):
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.setattr(gg, "fact_grounding_score_ex",
                        lambda *a, **k: (score, judge))
    return run_validation_gate(
        proposition="Paris is the capital of France", verified_by=None,
        topic="geo", agent=None, validate="fast",
        source="France's capital is Paris.", grounding_llm=object())


@settings(max_examples=40, deadline=None)
@given(st.floats(min_value=0.0, max_value=100.0,
                 allow_nan=False, allow_infinity=False),
       st.sampled_from(["claude", "interactive"]))
def test_decision_flips_exactly_at_the_resolved_threshold(score, judge):
    """For any score: action == persist  <=>  score >= resolved threshold."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    try:
        res = _gate_with_score(mp, score, judge)
        thr = gg.resolve_write_threshold_for(judge)
        if score < thr:
            assert res.action == "downgrade", (score, thr, res.action)
        else:
            assert res.action == "persist", (score, thr, res.action)
        assert res.grounding_score == score  # surfaced either way
    finally:
        mp.undo()


@settings(max_examples=25, deadline=None)
@given(st.floats(min_value=0.0, max_value=99.0,
                 allow_nan=False, allow_infinity=False),
       st.floats(min_value=0.01, max_value=1.0,
                 allow_nan=False, allow_infinity=False))
def test_admission_is_monotone_in_score(s, delta):
    """If s admits, s+delta admits (same judge, same config)."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    try:
        lo = _gate_with_score(mp, s, "claude")
        hi = _gate_with_score(mp, min(100.0, s + delta), "claude")
        if lo.action == "persist":
            assert hi.action == "persist", (s, delta)
    finally:
        mp.undo()


@settings(max_examples=20, deadline=None)
@given(st.floats(min_value=1.0, max_value=99.0,
                 allow_nan=False, allow_infinity=False),
       st.sampled_from(["claude", "interactive", "local"]))
def test_env_threshold_override_wins_for_every_backend(thr, judge):
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    try:
        mp.setenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", str(thr))
        assert gg.resolve_write_threshold_for(judge) == thr
    finally:
        mp.undo()


# NOTE: hypothesis forbids function-scoped fixtures inside @given — each
# property builds its own MonkeyPatch() and undoes it in finally.
