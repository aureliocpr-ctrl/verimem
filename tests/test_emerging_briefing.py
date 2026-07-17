"""Emerging-task early-warning (atomic idea #1, 2026-06-13).

When the incoming task matches a SIGNATURE that is rising in frequency (done
several times in the recent window vs almost never before), the briefing should
flag it [EMERGING] and surface ONLY the recent episodes that share that
signature — so you accelerate what you're getting good at instead of
re-deriving it from the whole corpus.

curate_emerging_briefing is a PURE, deterministic, no-LLM function composing
two real capabilities: emerging_patterns._signature (the 4-token task
signature) and emerging_patterns.find_emerging_patterns (which signatures are
emerging). RED marker: the function does not exist yet.
"""
from __future__ import annotations

import time
import types

from verimem.emerging_briefing import curate_emerging_briefing

_DAY = 86400.0


def _ep(task_text: str, age_days: float, *, outcome: str = "success", now: float):
    return types.SimpleNamespace(
        task_text=task_text,
        created_at=now - age_days * _DAY,
        outcome=outcome,
        id=f"ep-{task_text[:6]}-{int(age_days)}",
    )


def test_emerging_task_is_flagged_and_recent_episodes_surfaced():
    now = time.time()
    # An "embedding recall bug fix" task done 3x in the last week, once 40 days ago.
    eps = [
        _ep("fix embedding recall bug model", 1, now=now),
        _ep("fix embedding recall bug model", 2, now=now),
        _ep("fix embedding recall bug model", 3, now=now),
        _ep("fix embedding recall bug model", 40, now=now),  # historical
        _ep("write the quarterly finance report", 2, now=now),  # noise, not emerging
    ]
    out = curate_emerging_briefing("fix the embedding recall bug in the model", eps, now=now)
    assert out["is_emerging"] is True, "a rising task signature must be flagged emerging"
    assert out["matched_pattern"] is not None
    rec_ids = {e["id"] for e in out["episodes_recent"]}
    # the 3 recent same-signature episodes surface; the 40-day-old one does NOT
    assert len([e for e in out["episodes_recent"]]) == 3
    assert "ep-fix em-40" not in rec_ids, "historical episode must not be surfaced as recent"
    assert all("finance" not in e["task_text"] for e in out["episodes_recent"]), (
        "unrelated-signature episodes must not leak in"
    )


def test_non_emerging_task_not_flagged():
    now = time.time()
    eps = [
        _ep("fix embedding recall bug model", 1, now=now),
        _ep("write the quarterly finance report", 2, now=now),
    ]
    # a one-off task with no rising signature
    out = curate_emerging_briefing("design a brand new unrelated feature xyz", eps, now=now)
    assert out["is_emerging"] is False
    assert out["episodes_recent"] == []


def test_recent_episodes_ordered_most_recent_first():
    now = time.time()
    eps = [
        _ep("tune the recall encode budget timeout", 5, now=now),
        _ep("tune the recall encode budget timeout", 1, now=now),
        _ep("tune the recall encode budget timeout", 3, now=now),
    ]
    out = curate_emerging_briefing("tune recall encode budget timeout", eps, now=now)
    assert out["is_emerging"] is True
    ages = [e["age_days"] for e in out["episodes_recent"]]
    assert ages == sorted(ages), "recent episodes must be ordered most-recent-first"


def test_empty_episodes_is_safe():
    out = curate_emerging_briefing("anything", [], now=time.time())
    assert out["is_emerging"] is False
    assert out["episodes_recent"] == []


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


def test_get_briefing_wires_emerging_and_surfaces_recent():
    from verimem.briefing import get_briefing
    now = time.time()
    eps = [
        _ep("fix embedding recall bug model", 1, now=now),
        _ep("fix embedding recall bug model", 2, now=now),
        _ep("fix embedding recall bug model", 3, now=now),
        _ep("fix embedding recall bug model", 40, now=now),
        _ep("write the quarterly finance report", 2, now=now),
    ]
    out = get_briefing(agent=_FakeAgent(eps),
                       task_text="fix the embedding recall bug in the model")
    assert "emerging" in out, "briefing must expose the emerging field (wiring)"
    assert out["emerging"]["is_emerging"] is True
    assert len(out["emerging"]["episodes_recent"]) == 3


def test_get_briefing_emerging_field_present_without_task_text():
    from verimem.briefing import get_briefing
    out = get_briefing(agent=_FakeAgent([]), task_text=None)
    assert "emerging" in out
    assert out["emerging"]["is_emerging"] is False


def test_get_briefing_summary_shows_emerging_marker_when_rising():
    from verimem.briefing import get_briefing
    now = time.time()
    eps = [
        _ep("fix embedding recall bug model", 1, now=now),
        _ep("fix embedding recall bug model", 2, now=now),
        _ep("fix embedding recall bug model", 3, now=now),
        _ep("fix embedding recall bug model", 40, now=now),
    ]
    out = get_briefing(agent=_FakeAgent(eps),
                       task_text="fix the embedding recall bug in the model")
    assert "[EMERGING]" in out["summary_text"], (
        "the emerging signal must be VISIBLE in the human summary, not just the payload"
    )


def test_get_briefing_summary_no_marker_when_not_emerging():
    from verimem.briefing import get_briefing
    out = get_briefing(agent=_FakeAgent([]), task_text="a one-off unrelated task")
    assert "[EMERGING]" not in out["summary_text"]
