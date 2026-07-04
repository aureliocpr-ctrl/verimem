"""Correction-velocity detector — atomic idea #2 (2026-06-13).

The flip: idea #1 (emerging) tells you what you're doing a LOT lately. This
tells you what you GET WRONG THEN FIX. When the incoming task's signature has a
history of FAILURE-then-SUCCESS for the *same* signature, the briefing surfaces
the approach that eventually worked (and the failed attempts to avoid) — so you
skip the failed first attempt this time instead of re-deriving the correction.

``detect_correction_pattern`` is a PURE, deterministic, no-LLM function. It is
grounded in what real episodes actually carry (task_text + outcome + created_at)
— NOT step-level traces, which the live corpus rarely populates (a trajectory
diff there would look sophisticated and return nothing). It reuses the SAME
``emerging_patterns._signature`` primitive as idea #1 for consistency.

RED marker: the function does not exist yet.
"""
from __future__ import annotations

import time
import types

from engram.correction_velocity import detect_correction_pattern

_DAY = 86400.0

# Reuse idea #1's exact strings: task signature overlaps episode signature by 3
# tokens {embedding,fix,recall} >= the default min_token_overlap.
_TASK = "fix the embedding recall bug in the model"
_SIG = "fix embedding recall bug model"
_OTHER = "write the quarterly finance report"


def _ep(task_text: str, age_days: float, *, outcome: str, now: float):
    return types.SimpleNamespace(
        task_text=task_text,
        created_at=now - age_days * _DAY,
        outcome=outcome,
        id=f"ep-{outcome[:4]}-{int(age_days)}",
    )


def test_failure_then_success_is_detected_with_latency():
    now = time.time()
    eps = [
        _ep(_SIG, 5, outcome="failure", now=now),
        _ep(_SIG, 4, outcome="failure", now=now),
        _ep(_SIG, 3, outcome="success", now=now),  # the correction
        _ep(_OTHER, 2, outcome="failure", now=now),  # noise, other signature
    ]
    out = detect_correction_pattern(_TASK, eps, now=now)
    assert out["has_correction"] is True, "failure-then-success must be a correction"
    assert out["failures_before_success"] == 2
    # success surfaced = the correcting success (the proven fix)
    assert out["success"] is not None
    assert out["success"]["id"] == "ep-succ-3"
    assert out["success"]["age_days"] == 3.0
    # latency = last failure before the fix (4d) -> the fix (3d) = 1 day
    assert out["correction_latency_days"] == 1.0
    # the failed attempts to avoid, most-recent-first, no other-signature leak
    fail_ids = [f["id"] for f in out["recent_failures"]]
    assert fail_ids == ["ep-fail-4", "ep-fail-5"]
    assert all("finance" not in f["task_text"] for f in out["recent_failures"])


def test_only_successes_is_not_a_correction():
    now = time.time()
    eps = [
        _ep(_SIG, 3, outcome="success", now=now),
        _ep(_SIG, 1, outcome="success", now=now),
    ]
    out = detect_correction_pattern(_TASK, eps, now=now)
    assert out["has_correction"] is False
    assert out["success"] is None
    assert out["recent_failures"] == []


def test_regression_success_then_failure_is_not_a_correction():
    """Success FIRST, then a later failure = a regression, not a recovery.
    has_correction requires a success that comes AFTER a failure."""
    now = time.time()
    eps = [
        _ep(_SIG, 5, outcome="success", now=now),  # worked 5 days ago
        _ep(_SIG, 1, outcome="failure", now=now),  # then broke 1 day ago
    ]
    out = detect_correction_pattern(_TASK, eps, now=now)
    assert out["has_correction"] is False, "no success AFTER the failure = no correction"


def test_unrelated_signature_is_ignored():
    now = time.time()
    eps = [
        _ep(_OTHER, 4, outcome="failure", now=now),
        _ep(_OTHER, 2, outcome="success", now=now),
    ]
    out = detect_correction_pattern(_TASK, eps, now=now)
    assert out["has_correction"] is False, "correction of a different task must not match"


def test_partial_outcome_is_not_a_clean_success():
    now = time.time()
    eps = [
        _ep(_SIG, 4, outcome="failure", now=now),
        _ep(_SIG, 2, outcome="partial", now=now),  # not a clean fix
    ]
    out = detect_correction_pattern(_TASK, eps, now=now)
    assert out["has_correction"] is False, "'partial' must not count as the correcting success"


def test_empty_episodes_is_safe():
    out = detect_correction_pattern(_TASK, [], now=time.time())
    assert out["has_correction"] is False
    assert out["recent_failures"] == []
    assert out["success"] is None


def test_blank_task_is_safe():
    now = time.time()
    eps = [_ep(_SIG, 4, outcome="failure", now=now), _ep(_SIG, 2, outcome="success", now=now)]
    out = detect_correction_pattern("", eps, now=now)
    assert out["has_correction"] is False


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


def test_get_briefing_wires_correction_and_marks_summary():
    from engram.briefing import get_briefing
    now = time.time()
    eps = [
        _ep(_SIG, 5, outcome="failure", now=now),
        _ep(_SIG, 4, outcome="failure", now=now),
        _ep(_SIG, 3, outcome="success", now=now),
    ]
    out = get_briefing(agent=_FakeAgent(eps), task_text=_TASK)
    assert "correction" in out, "briefing must expose the correction field (wiring)"
    assert out["correction"]["has_correction"] is True
    assert out["correction"]["failures_before_success"] == 2
    assert "[CORRECTION]" in out["summary_text"], (
        "the correction signal must be VISIBLE in the human summary"
    )


def test_get_briefing_correction_absent_is_safe():
    from engram.briefing import get_briefing
    out = get_briefing(agent=_FakeAgent([]), task_text=None)
    assert "correction" in out
    assert out["correction"]["has_correction"] is False
    assert "[CORRECTION]" not in out["summary_text"]
