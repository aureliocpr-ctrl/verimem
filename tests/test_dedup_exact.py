"""Plan logic for exact-text fact dedup (pure, no DB)."""
from __future__ import annotations

from scripts.dedup_exact_facts import plan_dedup


def _r(fid, prop, ts, topic="project/x"):
    return {"id": fid, "proposition": prop, "created_at": ts, "topic": topic}


def test_keeps_earliest_supersedes_rest():
    rows = [_r("b", "same fact", 200), _r("a", "same fact", 100),
            _r("c", "same fact", 300)]
    plan = plan_dedup(rows)
    assert len(plan) == 1
    assert plan[0]["winner_id"] == "a"          # earliest created_at survives
    assert plan[0]["loser_ids"] == ["b", "c"]


def test_whitespace_normalized_but_not_semantics():
    rows = [_r("a", "hello  world", 100), _r("b", "hello world", 200),
            _r("c", "hello world!", 300)]
    plan = plan_dedup(rows)
    # a and b collapse (whitespace only); c differs (punctuation) -> its own group
    assert len(plan) == 1
    assert plan[0]["winner_id"] == "a"
    assert plan[0]["loser_ids"] == ["b"]


def test_unique_facts_produce_no_plan():
    rows = [_r("a", "one", 1), _r("b", "two", 2), _r("c", "three", 3)]
    assert plan_dedup(rows) == []


def test_cross_topic_exact_dup_is_collapsed():
    # identical text under different topics is still a duplicate (byte-identical)
    rows = [_r("a", "dup", 100, topic="project/x"),
            _r("b", "dup", 200, topic="lessons/y")]
    plan = plan_dedup(rows)
    assert plan and plan[0]["winner_id"] == "a" and plan[0]["loser_ids"] == ["b"]


def test_deterministic_tiebreak_on_equal_ts():
    rows = [_r("b", "same", 100), _r("a", "same", 100)]
    plan = plan_dedup(rows)
    assert plan[0]["winner_id"] == "a"  # id tiebreak
    assert plan[0]["loser_ids"] == ["b"]


def test_empty_propositions_ignored():
    rows = [_r("a", "   ", 1), _r("b", "   ", 2)]
    # whitespace-only normalizes to empty -> not a real fact, never collapsed
    assert plan_dedup(rows) == []
