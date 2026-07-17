"""R45: Composite fact priority score combining trust + recency + corroboration."""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = ""
    confidence: float = 0.9
    created_at: float = 0.0


def test_empty_returns_empty():
    from verimem.fact_priority import rank_facts_by_priority
    out = rank_facts_by_priority([])
    assert out["ranked"] == []


def test_fresh_high_conf_top():
    from verimem.fact_priority import rank_facts_by_priority
    now = time.time()
    facts = [
        _Fact("recent_high", "X", confidence=0.95, created_at=now),
        _Fact("old_low", "Y", confidence=0.3, created_at=now - 86400 * 365),
    ]
    out = rank_facts_by_priority(facts, now=now)
    assert out["ranked"][0]["id"] == "recent_high"


def test_payload_shape():
    from verimem.fact_priority import rank_facts_by_priority
    out = rank_facts_by_priority([])
    for k in ("ranked", "n_facts_scanned"):
        assert k in out


def test_entry_keys():
    from verimem.fact_priority import rank_facts_by_priority
    now = time.time()
    facts = [_Fact("f1", "X", confidence=0.9, created_at=now)]
    out = rank_facts_by_priority(facts, now=now)
    if out["ranked"]:
        for k in ("id", "priority", "components"):
            assert k in out["ranked"][0]


def test_priority_in_unit_range():
    from verimem.fact_priority import rank_facts_by_priority
    now = time.time()
    facts = [_Fact("f1", "X", confidence=0.5, created_at=now)]
    out = rank_facts_by_priority(facts, now=now)
    if out["ranked"]:
        assert 0.0 <= out["ranked"][0]["priority"] <= 1.0


def test_top_k_limit():
    from verimem.fact_priority import rank_facts_by_priority
    now = time.time()
    facts = [_Fact(f"f{i}", "X", confidence=0.5, created_at=now)
             for i in range(10)]
    out = rank_facts_by_priority(facts, now=now, top_k=3)
    assert len(out["ranked"]) == 3
