"""FORGIA pezzo #222 — Wave 21: facts grouped by topic.

For each `topic`, returns the count of facts and a sample. Lets the
user see "quali argomenti ho memorizzato?" without paginating
through hundreds of facts.

Topic = `f.topic`; empty/missing topics grouped under a fallback
key.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _FakeFact:
    id: str
    proposition: str = ""
    topic: str = ""
    created_at: float = 0.0


def test_empty_returns_empty_topics():
    from verimem.facts_topics import facts_topics

    out = facts_topics([])
    assert out["n_total"] == 0
    assert out["topics"] == []


def test_groups_by_topic_with_counts():
    from verimem.facts_topics import facts_topics

    facts = [
        _FakeFact("f1", "fact 1", topic="user"),
        _FakeFact("f2", "fact 2", topic="user"),
        _FakeFact("f3", "fact 3", topic="api"),
    ]
    out = facts_topics(facts)
    by_name = {t["topic"]: t for t in out["topics"]}
    assert by_name["user"]["count"] == 2
    assert by_name["api"]["count"] == 1


def test_empty_topic_grouped_under_fallback():
    from verimem.facts_topics import facts_topics

    facts = [
        _FakeFact("f1", "no topic 1"),
        _FakeFact("f2", "no topic 2"),
    ]
    out = facts_topics(facts)
    assert len(out["topics"]) == 1
    fallback = out["topics"][0]
    # Fallback name is documented as "(no topic)" or similar.
    assert fallback["count"] == 2


def test_topics_sorted_by_count_desc():
    from verimem.facts_topics import facts_topics

    facts = [
        _FakeFact("f1", "x", topic="small"),
        _FakeFact("f2", "x", topic="medium"),
        _FakeFact("f3", "x", topic="medium"),
        _FakeFact("f4", "x", topic="big"),
        _FakeFact("f5", "x", topic="big"),
        _FakeFact("f6", "x", topic="big"),
    ]
    out = facts_topics(facts)
    counts = [t["count"] for t in out["topics"]]
    assert counts == sorted(counts, reverse=True)


def test_includes_sample_facts():
    from verimem.facts_topics import facts_topics

    facts = [
        _FakeFact(f"f{i}", f"prop {i}", topic="x")
        for i in range(10)
    ]
    out = facts_topics(facts, n_samples=3)
    assert out["topics"][0]["sample_facts"] is not None
    assert len(out["topics"][0]["sample_facts"]) <= 3


def test_top_k_topics_respected():
    from verimem.facts_topics import facts_topics

    facts = [
        _FakeFact(f"f{i}", "x", topic=f"topic{i}")
        for i in range(20)
    ]
    out = facts_topics(facts, top_k_topics=5)
    assert len(out["topics"]) == 5


def test_n_total_matches_input():
    from verimem.facts_topics import facts_topics

    facts = [_FakeFact(f"f{i}", "x", topic="t") for i in range(7)]
    out = facts_topics(facts)
    assert out["n_total"] == 7
