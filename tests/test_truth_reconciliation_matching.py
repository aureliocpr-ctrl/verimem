"""P1 candidate-matching — the piece the critic's caller-verification exposed as
missing. reconcile_against_corpus must FIND the conflicting older fact (via shared
entities) instead of being handed it, then run P1's decision. This is the
end-to-end test the earlier 20/20 measure lacked (it used hand-fed candidates).
"""
from __future__ import annotations

from engram.contradiction import ContradictionStore
from engram.entity_kg import Entity, EntityStore
from engram.entity_populate import entity_kg_path_for
from engram.semantic import Fact, SemanticMemory
from engram.truth_reconciliation import (
    find_related_candidates,
    reconcile_against_corpus,
)

_NOW = 1_000_000_000.0
_DAY = 86400.0


def _setup(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    es = EntityStore(db_path=entity_kg_path_for(sm.db_path))
    cs = ContradictionStore(sm.db_path)
    return sm, es, cs


def test_entities_for_fact_roundtrip(tmp_path) -> None:
    _, es, _ = _setup(tmp_path)
    eid = es.store(Entity(canonical_name="config_x", type="config"))
    es.link_fact("f1", eid)
    assert eid in es.entities_for_fact("f1")
    assert es.entities_for_fact("nope") == []


def test_finds_related_via_shared_entity(tmp_path) -> None:
    sm, es, _ = _setup(tmp_path)
    old = Fact(id="old", proposition="config X is 30s", topic="t",
               status="verified", confidence=0.9, created_at=_NOW - 30 * _DAY)
    new = Fact(id="new", proposition="config X is 5s", topic="t",
               status="verified", confidence=0.9, created_at=_NOW)
    sm.store(old)
    sm.store(new)
    eid = es.store(Entity(canonical_name="config_x", type="config"))
    es.link_fact("old", eid)
    es.link_fact("new", eid)
    cands = find_related_candidates(sm, new, es)
    ids = {c.id for c in cands}
    assert "old" in ids, "must find the conflicting fact via the shared entity"
    assert "new" not in ids, "must exclude self"


def test_reconcile_against_corpus_supersedes_found_update(tmp_path) -> None:
    sm, es, cs = _setup(tmp_path)
    old = Fact(id="old", proposition="config X is 30s", topic="t",
               status="verified", confidence=0.9, created_at=_NOW - 30 * _DAY)
    new = Fact(id="new", proposition="config X is 5s", topic="t",
               status="verified", confidence=0.9, created_at=_NOW)
    sm.store(old)
    sm.store(new)
    eid = es.store(Entity(canonical_name="config_x", type="config"))
    es.link_fact("old", eid)
    es.link_fact("new", eid)
    res = reconcile_against_corpus(sm, new, es, contradiction_store=cs, now=_NOW,
                                   auto_supersede=True)
    assert "old" in res["superseded"], "end-to-end: found + superseded (opt-in)"
    assert sm.get("old").superseded_by == "new"


def test_default_is_conservative_contest_not_supersede(tmp_path) -> None:
    """Fail-safe default: candidates matched by correlation are CONTESTED, not
    superseded — no truth deleted from the live set on correlation alone."""
    sm, es, cs = _setup(tmp_path)
    old = Fact(id="old", proposition="config X is 30s", topic="t",
               status="verified", confidence=0.9, created_at=_NOW - 30 * _DAY)
    new = Fact(id="new", proposition="config X is 5s", topic="t",
               status="verified", confidence=0.9, created_at=_NOW)
    sm.store(old)
    sm.store(new)
    eid = es.store(Entity(canonical_name="config_x", type="config"))
    es.link_fact("old", eid)
    es.link_fact("new", eid)
    res = reconcile_against_corpus(sm, new, es, contradiction_store=cs, now=_NOW)
    assert res["superseded"] == [], "default must not supersede on correlation"
    assert "old" in res["contested"]
    assert sm.get("old").superseded_by is None
    assert cs.list_unresolved_for_fact("old"), "the doubt is recorded + visible"


def test_excludes_duplicate_and_superseded(tmp_path) -> None:
    sm, es, _ = _setup(tmp_path)
    dup = Fact(id="dup", proposition="config X is 5s", topic="t",
               status="verified", confidence=0.9, created_at=_NOW - 10 * _DAY)
    done = Fact(id="done", proposition="config X is 9s", topic="t",
                status="verified", confidence=0.9, created_at=_NOW - 5 * _DAY)
    succ = Fact(id="succ", proposition="config X is 7s", topic="t",
                status="verified", confidence=0.9, created_at=_NOW - 4 * _DAY)
    new = Fact(id="new", proposition="config X is 5s", topic="t",
               status="verified", confidence=0.9, created_at=_NOW)
    for f in (dup, done, succ, new):
        sm.store(f)
    sm.supersede("done", "succ", reason="test setup")  # really supersede 'done'
    eid = es.store(Entity(canonical_name="config_x", type="config"))
    for fid in ("dup", "done", "succ", "new"):
        es.link_fact(fid, eid)
    cands = find_related_candidates(sm, new, es)
    ids = {c.id for c in cands}
    assert "dup" not in ids, "same-proposition duplicate is not an update candidate"
    assert "done" not in ids, "already-superseded fact is not a candidate"
