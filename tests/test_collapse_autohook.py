"""Plan logic for the auto-hook snapshot collapse (pure, no DB)."""
from __future__ import annotations

from scripts.collapse_autohook_snapshots import plan_collapse

_DAY1 = 1780000000.0  # fixed epochs; exact day boundaries don't matter to the test


def _r(fid: str, ts: float) -> dict:
    return {"id": fid, "topic": "handoff/pre-compact-auto-hook-x", "created_at": ts}


def test_last_of_day_wins_and_earlier_lose():
    rows = [_r("a", _DAY1), _r("b", _DAY1 + 600), _r("c", _DAY1 + 1200)]
    plan = plan_collapse(rows)
    assert len(plan) == 1
    assert plan[0]["winner_id"] == "c"
    assert plan[0]["loser_ids"] == ["a", "b"]


def test_days_are_independent():
    rows = [_r("a", _DAY1), _r("b", _DAY1 + 600),
            _r("x", _DAY1 + 3 * 86400), _r("y", _DAY1 + 3 * 86400 + 60)]
    plan = plan_collapse(rows)
    assert [p["winner_id"] for p in plan] == ["b", "y"]
    assert sum(len(p["loser_ids"]) for p in plan) == 2


def test_single_snapshot_day_untouched():
    rows = [_r("only", _DAY1)]
    assert plan_collapse(rows) == []


def test_deterministic_tiebreak_on_equal_ts():
    rows = [_r("b", _DAY1), _r("a", _DAY1)]  # same ts: id order decides
    plan = plan_collapse(rows)
    assert plan[0]["winner_id"] == "b"
    assert plan[0]["loser_ids"] == ["a"]
