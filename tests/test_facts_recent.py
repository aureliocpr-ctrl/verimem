"""FORGIA pezzo #269 — Wave 68: facts_recent (last N by created_at)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _FakeFact:
    id: str
    proposition: str = ""
    topic: str = ""
    confidence: float = 0.9
    created_at: float = 0.0


def test_empty():
    from engram.facts_recent import facts_recent

    out = facts_recent([])
    assert out["facts"] == []


def test_sorted_newest_first():
    from engram.facts_recent import facts_recent

    facts = [
        _FakeFact("old", created_at=100.0),
        _FakeFact("new", created_at=300.0),
        _FakeFact("mid", created_at=200.0),
    ]
    out = facts_recent(facts)
    ids = [f["id"] for f in out["facts"]]
    assert ids == ["new", "mid", "old"]


def test_top_k():
    from engram.facts_recent import facts_recent

    facts = [_FakeFact(f"f{i}", created_at=float(i)) for i in range(10)]
    out = facts_recent(facts, top_k=3)
    assert len(out["facts"]) == 3


def test_payload_shape():
    from engram.facts_recent import facts_recent

    out = facts_recent([])
    for k in ("facts", "n_total"):
        assert k in out
