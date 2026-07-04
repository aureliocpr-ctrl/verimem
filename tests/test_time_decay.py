"""R7: Time-decay on facts confidence.

CVE patchato 6 mesi fa → confidence dovrebbe abbassarsi.
Memory invecchia, l'agente sa quando un fatto è "stale".

Exponential decay: half-life parametrizzabile (default 90 giorni).
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str
    confidence: float
    created_at: float


def test_fresh_fact_retains_confidence():
    from engram.time_decay import decay_confidence

    now = time.time()
    f = _Fact("f1", "X", "topic", 1.0, created_at=now - 86400)  # 1 day old
    out = decay_confidence(f, now=now, half_life_days=90)
    assert out >= 0.99  # almost no decay


def test_half_life_decay():
    """At half-life days, confidence should be ~50% of original."""
    from engram.time_decay import decay_confidence

    now = time.time()
    f = _Fact("f1", "X", "topic", 1.0,
              created_at=now - 86400 * 90)  # 90 days
    out = decay_confidence(f, now=now, half_life_days=90)
    assert 0.45 <= out <= 0.55


def test_double_half_life_quarter_confidence():
    from engram.time_decay import decay_confidence

    now = time.time()
    f = _Fact("f1", "X", "topic", 1.0,
              created_at=now - 86400 * 180)  # 2 half-lives
    out = decay_confidence(f, now=now, half_life_days=90)
    assert 0.20 <= out <= 0.30


def test_very_old_fact_near_zero():
    from engram.time_decay import decay_confidence

    now = time.time()
    f = _Fact("f1", "X", "topic", 1.0,
              created_at=now - 86400 * 720)  # 2 years
    out = decay_confidence(f, now=now, half_life_days=90)
    assert out < 0.05


def test_freshness_levels():
    from engram.time_decay import assess_freshness

    now = time.time()

    # 1 day old → fresh
    f1 = _Fact("f1", "X", "t", 0.9, created_at=now - 86400)
    out1 = assess_freshness(f1, now=now)
    assert out1["status"] == "fresh"

    # 100 days → stale
    f2 = _Fact("f2", "X", "t", 0.9, created_at=now - 86400 * 100)
    out2 = assess_freshness(f2, now=now)
    assert out2["status"] == "stale"

    # 365 days → expired
    f3 = _Fact("f3", "X", "t", 0.9, created_at=now - 86400 * 365)
    out3 = assess_freshness(f3, now=now)
    assert out3["status"] == "expired"


def test_freshness_includes_decayed_confidence():
    from engram.time_decay import assess_freshness

    now = time.time()
    f = _Fact("f1", "X", "t", 0.9, created_at=now - 86400 * 90)
    out = assess_freshness(f, now=now)
    assert "decayed_confidence" in out
    assert "age_days" in out
    assert 88 <= out["age_days"] <= 92


def test_find_stale_facts():
    from engram.time_decay import find_stale_facts

    now = time.time()
    facts = [
        _Fact("f1", "fresh", "t", 0.9, created_at=now - 86400 * 10),
        _Fact("f2", "stale", "t", 0.9, created_at=now - 86400 * 100),
        _Fact("f3", "old", "t", 0.9, created_at=now - 86400 * 200),
        _Fact("f4", "fresh2", "t", 0.9, created_at=now - 86400 * 5),
    ]
    out = find_stale_facts(facts, now=now, threshold_days=60)
    ids = [f["id"] for f in out["stale_facts"]]
    assert "f2" in ids
    assert "f3" in ids
    assert "f1" not in ids
    assert "f4" not in ids


def test_payload_shape():
    from engram.time_decay import assess_freshness, find_stale_facts

    out1 = find_stale_facts([])
    for k in ("stale_facts", "n_total_scanned", "n_stale"):
        assert k in out1

    now = time.time()
    f = _Fact("f1", "X", "t", 1.0, created_at=now - 86400)
    out2 = assess_freshness(f, now=now)
    for k in ("status", "decayed_confidence", "age_days", "original_confidence"):
        assert k in out2
