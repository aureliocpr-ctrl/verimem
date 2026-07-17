"""FORGIA pezzo #237 — Wave 36: batch find duplicate facts.

Same idea as find_duplicate_skills but for semantic memory: token
Jaccard on proposition text. Useful to dedupe accumulated facts
that say the same thing in slightly different wording.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _FakeFact:
    id: str
    proposition: str = ""
    topic: str = ""
    created_at: float = 0.0


def test_empty_returns_no_pairs():
    from verimem.find_duplicate_facts import find_duplicate_facts

    out = find_duplicate_facts([])
    assert out["pairs"] == []


def test_identical_propositions_detected():
    from verimem.find_duplicate_facts import find_duplicate_facts

    facts = [
        _FakeFact("f1", "the API endpoint is X"),
        _FakeFact("f2", "the API endpoint is X"),
    ]
    out = find_duplicate_facts(facts, threshold=0.5)
    assert len(out["pairs"]) == 1


def test_no_dupes_below_threshold():
    from verimem.find_duplicate_facts import find_duplicate_facts

    facts = [
        _FakeFact("f1", "alpha beta gamma"),
        _FakeFact("f2", "completely different text"),
    ]
    out = find_duplicate_facts(facts, threshold=0.5)
    assert out["pairs"] == []


def test_pairs_sorted_by_jaccard_desc():
    from verimem.find_duplicate_facts import find_duplicate_facts

    facts = [
        _FakeFact("a", "x y z"),
        _FakeFact("b", "x y z"),  # 1.0
        _FakeFact("c", "x y w"),  # 0.5 vs a
    ]
    out = find_duplicate_facts(facts, threshold=0.0)
    jaccards = [p["jaccard"] for p in out["pairs"]]
    assert jaccards == sorted(jaccards, reverse=True)


def test_top_k_respected():
    from verimem.find_duplicate_facts import find_duplicate_facts

    facts = [_FakeFact(f"f{i}", "x y z") for i in range(10)]
    out = find_duplicate_facts(facts, threshold=0.5, top_k=3)
    assert len(out["pairs"]) <= 3


def test_topic_filter_optional():
    from verimem.find_duplicate_facts import find_duplicate_facts

    facts = [
        _FakeFact("a", "x", topic="user"),
        _FakeFact("b", "x", topic="user"),
        _FakeFact("c", "x", topic="api"),
    ]
    out = find_duplicate_facts(facts, threshold=0.0, topic="user")
    # Only the 1 pair within "user" topic.
    assert len(out["pairs"]) == 1


def test_payload_shape_complete():
    from verimem.find_duplicate_facts import find_duplicate_facts

    out = find_duplicate_facts([])
    for k in ("pairs", "n_total_facts", "threshold"):
        assert k in out
