"""R14: Trust score per source — composite reliability rating.

Combines:
  - declared `confidence` of the fact (0..1)
  - age decay (older → less trust)
  - source agent reputation (success_rate over their past episodes)
  - corroboration count (how many other facts agree)

Output: trust score 0..1 per fact, plus rationale.
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str
    confidence: float = 0.9
    created_at: float = 0.0


def test_high_trust_fresh_high_confidence():
    from engram.trust_score import compute_trust_score

    now = time.time()
    f = _Fact("f1", "X", "t", confidence=0.95, created_at=now - 86400)
    out = compute_trust_score(f, now=now)
    assert out["trust"] >= 0.85


def test_low_trust_old_low_confidence():
    from engram.trust_score import compute_trust_score

    now = time.time()
    f = _Fact("f1", "X", "t", confidence=0.3,
              created_at=now - 86400 * 365)
    out = compute_trust_score(f, now=now)
    assert out["trust"] < 0.3


def test_corroboration_boost():
    from engram.trust_score import compute_trust_score

    now = time.time()
    target = _Fact("f1", "WordPress 5.8 vulnerable to CVE-X", "t",
                   confidence=0.7, created_at=now)
    corroborating = [
        _Fact("f2", "WordPress 5.8 vulnerable to CVE-X confirmed", "t",
              confidence=0.9, created_at=now),
        _Fact("f3", "WordPress 5.8 vulnerable to CVE-X", "t",
              confidence=0.85, created_at=now),
    ]
    out_solo = compute_trust_score(target, now=now)
    out_with_corr = compute_trust_score(
        target, now=now, corroborating_facts=corroborating,
    )
    # With corroboration, trust should be higher (or at worst equal)
    assert out_with_corr["trust"] >= out_solo["trust"]


def test_payload_keys():
    from engram.trust_score import compute_trust_score
    now = time.time()
    f = _Fact("f1", "X", "t", confidence=0.5, created_at=now)
    out = compute_trust_score(f, now=now)
    for k in ("trust", "components", "rationale"):
        assert k in out
    for k in ("base_confidence", "age_decay", "corroboration"):
        assert k in out["components"]


def test_components_in_unit_range():
    from engram.trust_score import compute_trust_score
    now = time.time()
    f = _Fact("f1", "X", "t", confidence=0.5, created_at=now)
    out = compute_trust_score(f, now=now)
    for v in out["components"].values():
        assert 0.0 <= v <= 1.0
    assert 0.0 <= out["trust"] <= 1.0


def test_rank_facts_by_trust():
    from engram.trust_score import rank_facts_by_trust

    now = time.time()
    facts = [
        _Fact("recent", "X", "t", 0.95, created_at=now - 86400),
        _Fact("old", "X", "t", 0.5, created_at=now - 86400 * 365),
        _Fact("mid", "X", "t", 0.7, created_at=now - 86400 * 30),
    ]
    out = rank_facts_by_trust(facts, now=now)
    # Recent + high confidence should be first
    assert out["ranked"][0]["id"] == "recent"


def test_empty_input():
    from engram.trust_score import rank_facts_by_trust
    out = rank_facts_by_trust([])
    assert out["ranked"] == []
