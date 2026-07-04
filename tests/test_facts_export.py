"""FORGIA pezzo #230 — Wave 29: facts batch export.

Existing `hippo_remember`/`hippo_facts_*` cover write/search. This
exports the entire semantic memory as portable JSON for
backup/migration.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _FakeFact:
    id: str
    proposition: str = ""
    topic: str = ""
    confidence: float = 0.9
    created_at: float = 0.0


def test_empty_returns_empty_payload():
    from engram.facts_export import export_all_facts

    out = export_all_facts([])
    assert out["facts"] == []
    assert out["n_total"] == 0


def test_exports_all_facts():
    from engram.facts_export import export_all_facts

    facts = [
        _FakeFact("f1", "alpha", topic="t1", created_at=1.0),
        _FakeFact("f2", "beta", topic="t2", created_at=2.0),
    ]
    out = export_all_facts(facts)
    assert out["n_total"] == 2
    ids = {f["id"] for f in out["facts"]}
    assert ids == {"f1", "f2"}


def test_topic_filter():
    from engram.facts_export import export_all_facts

    facts = [
        _FakeFact("f1", "x", topic="user"),
        _FakeFact("f2", "y", topic="api"),
    ]
    out = export_all_facts(facts, topic="user")
    assert len(out["facts"]) == 1
    assert out["facts"][0]["id"] == "f1"


def test_includes_required_fields():
    from engram.facts_export import export_all_facts

    facts = [_FakeFact("f1", "test prop", topic="x", confidence=0.7)]
    out = export_all_facts(facts)
    record = out["facts"][0]
    assert record["id"] == "f1"
    assert record["proposition"] == "test prop"
    assert record["topic"] == "x"
    assert record["confidence"] == 0.7


def test_payload_shape_complete():
    from engram.facts_export import export_all_facts

    out = export_all_facts([])
    for k in ("facts", "n_total", "schema_version"):
        assert k in out
