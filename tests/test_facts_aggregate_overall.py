"""FORGIA pezzo #277 — Wave 76: facts overall aggregate."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _FakeFact:
    id: str
    proposition: str = ""
    topic: str = ""
    confidence: float = 0.9


def test_empty():
    from verimem.facts_aggregate_overall import aggregate_facts_overall

    out = aggregate_facts_overall([])
    assert out["n_total"] == 0
    assert out["avg_confidence"] == 0.0


def test_counts_topics():
    from verimem.facts_aggregate_overall import aggregate_facts_overall

    facts = [
        _FakeFact("a", topic="x"),
        _FakeFact("b", topic="x"),
        _FakeFact("c", topic="y"),
    ]
    out = aggregate_facts_overall(facts)
    assert out["n_total"] == 3
    assert out["n_topics"] == 2


def test_avg_confidence():
    from verimem.facts_aggregate_overall import aggregate_facts_overall

    facts = [
        _FakeFact("a", confidence=0.8),
        _FakeFact("b", confidence=0.6),
    ]
    out = aggregate_facts_overall(facts)
    assert abs(out["avg_confidence"] - 0.7) < 1e-9


def test_top_topics():
    from verimem.facts_aggregate_overall import aggregate_facts_overall

    facts = [
        _FakeFact("a", topic="hot"),
        _FakeFact("b", topic="hot"),
        _FakeFact("c", topic="hot"),
        _FakeFact("d", topic="cold"),
    ]
    out = aggregate_facts_overall(facts)
    top = out["top_topics"]
    assert top[0]["topic"] == "hot"
    assert top[0]["count"] == 3


def test_payload_shape():
    from verimem.facts_aggregate_overall import aggregate_facts_overall

    out = aggregate_facts_overall([])
    for k in ("n_total", "n_topics", "avg_confidence",
                "top_topics", "conf_distribution"):
        assert k in out
