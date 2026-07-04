"""FORGIA pezzo #263 — Wave 62: facts filtered by confidence.

Filter facts by confidence range. Useful: 'show me only the
high-confidence ones' or 'show low-confidence ones to verify'.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _FakeFact:
    id: str
    proposition: str = ""
    confidence: float = 0.9


def test_empty_returns_empty():
    from engram.facts_by_confidence import facts_by_confidence

    out = facts_by_confidence([])
    assert out["facts"] == []


def test_min_filter():
    from engram.facts_by_confidence import facts_by_confidence

    facts = [
        _FakeFact("low", confidence=0.3),
        _FakeFact("high", confidence=0.95),
    ]
    out = facts_by_confidence(facts, min_conf=0.5)
    ids = [f["id"] for f in out["facts"]]
    assert "high" in ids
    assert "low" not in ids


def test_max_filter():
    from engram.facts_by_confidence import facts_by_confidence

    facts = [
        _FakeFact("a", confidence=0.4),
        _FakeFact("b", confidence=0.9),
    ]
    out = facts_by_confidence(facts, max_conf=0.5)
    ids = [f["id"] for f in out["facts"]]
    assert "a" in ids
    assert "b" not in ids


def test_combined_range():
    from engram.facts_by_confidence import facts_by_confidence

    facts = [
        _FakeFact("low", confidence=0.1),
        _FakeFact("mid", confidence=0.5),
        _FakeFact("high", confidence=0.95),
    ]
    out = facts_by_confidence(facts, min_conf=0.4, max_conf=0.7)
    ids = [f["id"] for f in out["facts"]]
    assert ids == ["mid"]


def test_sorted_by_confidence_desc():
    from engram.facts_by_confidence import facts_by_confidence

    facts = [
        _FakeFact("a", confidence=0.3),
        _FakeFact("b", confidence=0.9),
        _FakeFact("c", confidence=0.6),
    ]
    out = facts_by_confidence(facts)
    confs = [f["confidence"] for f in out["facts"]]
    assert confs == sorted(confs, reverse=True)


def test_top_k_respected():
    from engram.facts_by_confidence import facts_by_confidence

    facts = [_FakeFact(f"f{i}", confidence=0.5) for i in range(10)]
    out = facts_by_confidence(facts, top_k=3)
    assert len(out["facts"]) == 3


def test_payload_shape_complete():
    from engram.facts_by_confidence import facts_by_confidence

    out = facts_by_confidence([])
    for k in ("facts", "n_total", "min_conf", "max_conf"):
        assert k in out
