"""Deterministic corroboration — trust-restore complement to Tier-1.

Two facts in DIFFERENT topics asserting the SAME value for the same unit
about the same subject = independent corroboration (real evidence, no LLM).
Positive twin of the numeric conflict scanner.
"""
from __future__ import annotations

from verimem.corroboration import (
    Corroboration,
    corroboration_index,
    find_corroborations,
)
from verimem.semantic import Fact


def _f(prop: str, topic: str) -> Fact:
    return Fact(proposition=prop, topic=topic, confidence=0.9)


def test_same_value_distinct_topics_is_corroboration() -> None:
    facts = [
        _f("The cache is bounded at 1024 entries.", "eng/cache"),
        _f("Cache holds 1024 entries maximum.", "docs/cache"),
    ]
    out = find_corroborations(facts)
    assert len(out) == 1
    assert isinstance(out[0], Corroboration)
    assert out[0].unit == "entry" and out[0].value == 1024.0


def test_different_value_is_not_corroboration() -> None:
    facts = [
        _f("The cache is bounded at 1024 entries.", "eng/cache"),
        _f("Cache holds 4096 entries maximum.", "docs/cache"),
    ]
    assert find_corroborations(facts) == []


def test_same_topic_duplicate_is_not_independent() -> None:
    # Same value, same topic → a duplicate, NOT independent corroboration.
    facts = [
        _f("The cache is bounded at 1024 entries.", "eng/cache"),
        _f("Cache holds 1024 entries maximum.", "eng/cache"),
    ]
    assert find_corroborations(facts) == []
    # …but explicitly allowing same-topic surfaces it.
    assert len(find_corroborations(facts, require_distinct_topic=False)) == 1


def test_unrelated_subject_same_value_no_corroboration() -> None:
    facts = [
        _f("The cache is bounded at 1024 entries.", "eng/cache"),
        _f("The ring buffer holds 1024 entries.", "eng/buffer"),
    ]
    # share only the unit word 'entries' (no distinctive subject overlap)
    assert find_corroborations(facts) == []


def test_corroboration_index_counts_distinct_peers() -> None:
    facts = [
        _f("Sessions expire after 30 minutes of inactivity.", "eng/session"),
        _f("Session TTL is 30 minutes.", "docs/session"),
        _f("The session timeout is set to 30 minutes.", "ops/session"),
    ]
    idx = corroboration_index(facts)
    # each of the three should be corroborated by the other two
    assert idx and max(idx.values()) >= 2


def test_noise_topics_excluded() -> None:
    facts = [
        _f("Cache holds 1024 entries.", "test/scratch"),
        _f("Cache holds 1024 entries.", "lab/x"),
    ]
    assert find_corroborations(facts) == []
