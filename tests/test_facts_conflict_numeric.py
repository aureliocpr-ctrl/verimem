"""Batch numeric-conflict scan over the facts pool.

Sibling of the polarity scanner (test_facts_conflict.py). Detects facts
already in the corpus that assert a DIFFERENT value for the same unit about
the same subject — the inconsistency the polarity scanner is blind to
(both facts are positive). Shares the quantity_match core with the
write-time gate, so the two views agree by construction.
"""
from __future__ import annotations

from engram.facts_conflict import (
    NumericConflictPair,
    find_numeric_conflicts,
)
from engram.semantic import Fact


def _f(prop: str, topic: str = "eng/component", confidence: float = 1.0) -> Fact:
    return Fact(proposition=prop, topic=topic, confidence=confidence)


def test_empty_and_single_pool_return_empty() -> None:
    assert find_numeric_conflicts([]) == []
    assert find_numeric_conflicts([_f("Cache holds 1024 entries.")]) == []


def test_numeric_conflict_detected() -> None:
    facts = [
        _f("Sessions are stored with a TTL of 30 minutes.", topic="eng/session"),
        _f("Sessions expire after 45 minutes of inactivity.", topic="eng/session"),
    ]
    pairs = find_numeric_conflicts(facts)
    assert len(pairs) == 1
    p = pairs[0]
    assert isinstance(p, NumericConflictPair)
    assert p.unit == "min"
    assert {p.value_a, p.value_b} == {30.0, 45.0}


def test_same_value_no_conflict() -> None:
    facts = [
        _f("Cache is bounded at 1024 entries.", topic="eng/cache"),
        _f("The cache holds 1024 entries max.", topic="eng/cache"),
    ]
    assert find_numeric_conflicts(facts) == []


def test_unrelated_subject_same_unit_no_conflict() -> None:
    facts = [
        _f("The ring buffer holds 256 entries.", topic="eng/buffer"),
        _f("The cache is bounded at 1024 entries.", topic="eng/cache"),
    ]
    assert find_numeric_conflicts(facts) == []


def test_contrasting_qualifier_no_conflict() -> None:
    facts = [
        _f("The read timeout is 30 seconds.", topic="eng/net"),
        _f("The write timeout is 10 seconds.", topic="eng/net"),
    ]
    assert find_numeric_conflicts(facts) == []


def test_noise_topics_excluded_by_default() -> None:
    # Two genuinely-conflicting facts but under excluded noise prefixes.
    facts = [
        _f("Cache holds 1024 entries.", topic="test/scratch"),
        _f("Cache holds 4096 entries.", topic="lab/stress"),
    ]
    assert find_numeric_conflicts(facts) == []
    # …but discoverable when the caller opts out of the exclusion.
    pairs = find_numeric_conflicts(facts, exclude_topic_prefixes=())
    assert len(pairs) == 1


def test_topic_filter_narrows_scan() -> None:
    facts = [
        _f("Cache holds 1024 entries.", topic="eng/cache"),
        _f("Cache holds 4096 entries.", topic="eng/cache"),
        _f("Queue holds 50 jobs.", topic="eng/queue"),
        _f("Queue holds 99 jobs.", topic="eng/queue"),
    ]
    pairs = find_numeric_conflicts(facts, topic="eng/cache")
    assert len(pairs) == 1
    assert pairs[0].unit == "entry"
