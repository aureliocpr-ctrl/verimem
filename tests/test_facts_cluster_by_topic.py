"""FORGIA pezzo #279 — Wave 78: cluster facts by topic with full members.

Differenza da aggregate_facts_overall: questo restituisce per ogni
topic la LISTA delle propositions, non solo il count.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _FakeFact:
    id: str
    proposition: str
    topic: str
    confidence: float = 0.9
    created_at: float = 0.0
    source_episodes: list[str] = field(default_factory=list)


def test_empty():
    from engram.facts_cluster_by_topic import facts_cluster_by_topic

    out = facts_cluster_by_topic([])
    assert out["n_topics"] == 0
    assert out["clusters"] == []


def test_single_topic():
    from engram.facts_cluster_by_topic import facts_cluster_by_topic

    facts = [
        _FakeFact("f1", "A", "math", 0.9),
        _FakeFact("f2", "B", "math", 0.5),
    ]
    out = facts_cluster_by_topic(facts)
    assert out["n_topics"] == 1
    c = out["clusters"][0]
    assert c["topic"] == "math"
    assert c["count"] == 2
    assert set(c["fact_ids"]) == {"f1", "f2"}
    # avg_confidence = (0.9 + 0.5) / 2 = 0.7
    assert abs(c["avg_confidence"] - 0.7) < 1e-6


def test_multiple_topics_sorted_by_count_desc():
    from engram.facts_cluster_by_topic import facts_cluster_by_topic

    facts = [
        _FakeFact("f1", "A", "math"),
        _FakeFact("f2", "B", "math"),
        _FakeFact("f3", "C", "math"),
        _FakeFact("f4", "D", "lang"),
    ]
    out = facts_cluster_by_topic(facts)
    assert out["n_topics"] == 2
    # First cluster = topic with most facts
    assert out["clusters"][0]["topic"] == "math"
    assert out["clusters"][0]["count"] == 3
    assert out["clusters"][1]["topic"] == "lang"


def test_top_k_limit():
    from engram.facts_cluster_by_topic import facts_cluster_by_topic

    facts = [
        _FakeFact(f"f{i}", "p", f"t{i}") for i in range(10)
    ]
    out = facts_cluster_by_topic(facts, top_k=3)
    assert len(out["clusters"]) == 3


def test_max_props_per_cluster():
    """When a cluster has many facts, propositions list is truncated."""
    from engram.facts_cluster_by_topic import facts_cluster_by_topic

    facts = [_FakeFact(f"f{i}", f"prop {i}", "math") for i in range(20)]
    out = facts_cluster_by_topic(facts, max_props_per_cluster=5)
    c = out["clusters"][0]
    assert c["count"] == 20
    assert len(c["sample_propositions"]) == 5


def test_missing_topic_groups_as_no_topic():
    from engram.facts_cluster_by_topic import facts_cluster_by_topic

    facts = [
        _FakeFact("f1", "A", ""),
        _FakeFact("f2", "B", None),  # type: ignore
    ]
    out = facts_cluster_by_topic(facts)
    assert out["n_topics"] == 1
    assert out["clusters"][0]["topic"] == "(no topic)"
    assert out["clusters"][0]["count"] == 2


def test_payload_shape():
    from engram.facts_cluster_by_topic import facts_cluster_by_topic

    out = facts_cluster_by_topic([])
    for k in ("clusters", "n_topics", "n_total_facts"):
        assert k in out
