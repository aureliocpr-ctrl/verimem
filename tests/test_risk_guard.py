"""Predictive error-guarding — atomic idea #4 (2026-06-13).

The flip: idea #2 (correction-velocity) fires only when a task signature has a
failure-THEN-success history — it hands you the fix. But the most dangerous case
is the one with NO fix yet: a task that *keeps* failing. predict_outcome already
estimates p(failure) from similar past episodes (Jaccard on task_text + outcome,
fully grounded — no traces), but it's only reachable on PULL (the
hippo_outcome_predict MCP tool). This wires it as a PROACTIVE guard: at briefing
time, if the incoming task looks like one that historically FAILS (high
p_failure with enough confidence), surface the warning + the similar failures so
you guard against re-committing the error before you act.

assess_task_risk is a thin, deterministic wrapper over predict_outcome with the
guard thresholds. RED marker: the function does not exist yet.
"""
from __future__ import annotations

import types

from engram.risk_guard import assess_task_risk

_TASK = "deploy the auth service to production"
_SIM = "deploy auth service production"  # Jaccard 4/6 = 0.67 >= 0.3 threshold
_OTHER = "write the quarterly finance report"


def _ep(task_text: str, outcome: str):
    return types.SimpleNamespace(task_text=task_text, outcome=outcome)


def test_repeated_failures_make_a_task_risky():
    eps = [_ep(_SIM, "failure") for _ in range(4)] + [_ep(_OTHER, "success")]
    out = assess_task_risk(_TASK, eps)
    assert out["is_risky"] is True, "a task that historically fails must be flagged"
    assert out["p_failure"] > 0.55
    assert out["confidence"] >= 0.4
    assert out["n_similar"] == 4
    # the similar failures are surfaced (so you see WHAT failed), no other-task leak
    assert len(out["similar_failures"]) >= 1
    assert all("finance" not in f["task_text"] for f in out["similar_failures"])


def test_mostly_successful_task_is_not_risky():
    eps = [_ep(_SIM, "success") for _ in range(4)]
    out = assess_task_risk(_TASK, eps)
    assert out["is_risky"] is False
    assert out["similar_failures"] == []


def test_single_failure_is_too_little_confidence():
    # one similar failure => confidence 0.2 < 0.4 => not enough evidence to guard.
    eps = [_ep(_SIM, "failure")]
    out = assess_task_risk(_TASK, eps)
    assert out["is_risky"] is False, "one data point must not trigger a guard"
    assert out["n_similar"] == 1


def test_unrelated_task_has_no_signal():
    eps = [_ep(_SIM, "failure") for _ in range(4)]
    out = assess_task_risk("bake a chocolate cake recipe", eps)
    assert out["is_risky"] is False
    assert out["n_similar"] == 0


def test_empty_is_safe():
    out = assess_task_risk(_TASK, [])
    assert out["is_risky"] is False
    assert out["similar_failures"] == []


def test_blank_task_is_safe():
    out = assess_task_risk("", [_ep(_SIM, "failure") for _ in range(4)])
    assert out["is_risky"] is False


# --- wiring into get_briefing (the caller_verification gap) ------------------

class _FakeMem:
    def __init__(self, eps):
        self._eps = eps

    def all(self, limit=None):
        return self._eps if limit is None else self._eps[:limit]

    def count(self):
        return len(self._eps)


class _FakeAgent:
    def __init__(self, eps):
        self.memory = _FakeMem(eps)
        self.skills = None
        self.semantic = None


def test_get_briefing_wires_risk_guard_and_marks_summary():
    from engram.briefing import get_briefing
    eps = [_ep(_SIM, "failure") for _ in range(4)]
    out = get_briefing(agent=_FakeAgent(eps), task_text=_TASK)
    assert "risk_guard" in out, "briefing must expose the risk_guard field (wiring)"
    assert out["risk_guard"]["is_risky"] is True
    assert "[RISK]" in out["summary_text"], "the risk guard must be VISIBLE in the summary"


def test_get_briefing_risk_guard_absent_is_safe():
    from engram.briefing import get_briefing
    out = get_briefing(agent=_FakeAgent([]), task_text=None)
    assert "risk_guard" in out
    assert out["risk_guard"]["is_risky"] is False
    assert "[RISK]" not in out["summary_text"]
