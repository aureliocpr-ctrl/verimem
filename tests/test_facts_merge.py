"""FORGIA pezzo #241 — Wave 40: merge two duplicate facts.

After find_duplicate_facts (#237) flags a pair, this combines them
into one. Configurable: which one to keep as "primary"; the merged
fact inherits the union of source_episodes and a confidence
combination (default: average).
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


def test_keeper_a_default():
    from engram.facts_merge import merge_facts

    a = _FakeFact("a", "alpha", confidence=0.8)
    b = _FakeFact("b", "beta", confidence=0.6)
    out = merge_facts(a, b)
    # By default keeper is "a" — primary id is a.
    assert out["primary_id"] == "a"
    assert out["secondary_id"] == "b"


def test_keeper_b_explicit():
    from engram.facts_merge import merge_facts

    a = _FakeFact("a")
    b = _FakeFact("b")
    out = merge_facts(a, b, keeper="b")
    assert out["primary_id"] == "b"
    assert out["secondary_id"] == "a"


def test_source_episodes_union():
    from engram.facts_merge import merge_facts

    a = _FakeFact("a", source_episodes=["e1", "e2"])
    b = _FakeFact("b", source_episodes=["e2", "e3"])
    out = merge_facts(a, b)
    assert set(out["source_episodes"]) == {"e1", "e2", "e3"}


def test_confidence_average_by_default():
    from engram.facts_merge import merge_facts

    a = _FakeFact("a", confidence=0.8)
    b = _FakeFact("b", confidence=0.6)
    out = merge_facts(a, b)
    assert abs(out["confidence"] - 0.7) < 1e-9


def test_confidence_max_strategy():
    from engram.facts_merge import merge_facts

    a = _FakeFact("a", confidence=0.8)
    b = _FakeFact("b", confidence=0.6)
    out = merge_facts(a, b, confidence_strategy="max")
    assert out["confidence"] == 0.8


def test_proposition_uses_keeper():
    from engram.facts_merge import merge_facts

    a = _FakeFact("a", proposition="version A")
    b = _FakeFact("b", proposition="version B")
    out_a = merge_facts(a, b, keeper="a")
    out_b = merge_facts(a, b, keeper="b")
    assert out_a["proposition"] == "version A"
    assert out_b["proposition"] == "version B"


def test_topic_preferred_from_keeper():
    from engram.facts_merge import merge_facts

    a = _FakeFact("a", topic="user_facts")
    b = _FakeFact("b", topic="")
    out = merge_facts(a, b)
    assert out["topic"] == "user_facts"


def test_payload_shape_complete():
    from engram.facts_merge import merge_facts

    a = _FakeFact("a")
    b = _FakeFact("b")
    out = merge_facts(a, b)
    for k in ("primary_id", "secondary_id", "proposition",
                "topic", "confidence", "source_episodes"):
        assert k in out
