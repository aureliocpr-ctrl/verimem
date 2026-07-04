"""FORGIA pezzo #260 — Wave 59: merge facts by topic.

Combine all facts under the same topic into one summary record.
Useful per knowledge consolidation: if 5 facts mention 'NEXUS
architecture', merge into one comprehensive entry.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _FakeFact:
    id: str
    proposition: str = ""
    topic: str = ""
    confidence: float = 0.9
    source_episodes: list[str] = field(default_factory=list)
    created_at: float = 0.0


def test_empty_facts_returns_none():
    from engram.facts_topic_merge import merge_facts_by_topic

    out = merge_facts_by_topic([], topic="anything")
    assert out is None


def test_topic_not_present_returns_none():
    from engram.facts_topic_merge import merge_facts_by_topic

    facts = [_FakeFact("f1", "x", topic="other")]
    out = merge_facts_by_topic(facts, topic="nonexistent")
    assert out is None


def test_single_fact_returns_unchanged_clone():
    from engram.facts_topic_merge import merge_facts_by_topic

    facts = [_FakeFact("f1", "only fact", topic="x")]
    out = merge_facts_by_topic(facts, topic="x")
    assert out is not None
    assert "only fact" in out["proposition"]
    assert out["topic"] == "x"


def test_multi_fact_merge():
    from engram.facts_topic_merge import merge_facts_by_topic

    facts = [
        _FakeFact("f1", "fact one", topic="x", confidence=0.9),
        _FakeFact("f2", "fact two", topic="x", confidence=0.7),
        _FakeFact("f3", "fact three", topic="x", confidence=0.8),
        _FakeFact("f4", "ignored", topic="other"),
    ]
    out = merge_facts_by_topic(facts, topic="x")
    assert "fact one" in out["proposition"]
    assert "fact two" in out["proposition"]
    assert "fact three" in out["proposition"]
    assert "ignored" not in out["proposition"]


def test_source_episodes_union():
    from engram.facts_topic_merge import merge_facts_by_topic

    facts = [
        _FakeFact("f1", "a", topic="x", source_episodes=["e1", "e2"]),
        _FakeFact("f2", "b", topic="x", source_episodes=["e2", "e3"]),
    ]
    out = merge_facts_by_topic(facts, topic="x")
    assert set(out["source_episodes"]) == {"e1", "e2", "e3"}


def test_confidence_strategy_average():
    from engram.facts_topic_merge import merge_facts_by_topic

    facts = [
        _FakeFact("f1", "a", topic="x", confidence=0.8),
        _FakeFact("f2", "b", topic="x", confidence=0.6),
    ]
    out = merge_facts_by_topic(facts, topic="x")
    assert abs(out["confidence"] - 0.7) < 1e-9


def test_custom_separator():
    from engram.facts_topic_merge import merge_facts_by_topic

    facts = [
        _FakeFact("f1", "alpha", topic="x"),
        _FakeFact("f2", "beta", topic="x"),
    ]
    out = merge_facts_by_topic(facts, topic="x", separator=" || ")
    assert " || " in out["proposition"]


def test_payload_shape_complete():
    from engram.facts_topic_merge import merge_facts_by_topic

    facts = [_FakeFact("f1", "a", topic="x")]
    out = merge_facts_by_topic(facts, topic="x")
    for k in ("topic", "proposition", "confidence",
                "source_episodes", "n_merged", "merged_ids"):
        assert k in out
