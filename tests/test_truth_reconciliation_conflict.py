"""P1 refinement — a lightweight conflict heuristic guarding auto_supersede.

Two facts sharing an entity may CONFLICT (same attribute, different value:
"config X is 30s" vs "config X is 5s") or be COMPLEMENTARY (different attributes:
"config X is 5s" vs "config X owner is Bob"). classify_conflict only checks
time+authority, so on its own it would supersede a complementary fact. The
heuristic adds a second guard for the (opt-in, dangerous) supersede path. It is
best-effort token-based, NOT semantic — the fail-safe default (contest, never
supersede) remains the real protection.
"""
from __future__ import annotations

from verimem.contradiction import ContradictionStore
from verimem.entity_kg import Entity, EntityStore
from verimem.entity_populate import entity_kg_path_for
from verimem.semantic import Fact, SemanticMemory
from verimem.truth_reconciliation import looks_like_conflict, reconcile_against_corpus

_NOW = 1_000_000_000.0
_DAY = 86400.0


def test_same_attribute_diff_value_is_conflict() -> None:
    assert looks_like_conflict("config X is 30s", "config X is 5s")


def test_complementary_attribute_is_not_conflict() -> None:
    assert not looks_like_conflict("config X is 5s", "config X owner is Bob")


def test_unrelated_is_not_conflict() -> None:
    assert not looks_like_conflict("the sky is blue today", "config X is 5s")


def test_identical_is_not_conflict() -> None:
    assert not looks_like_conflict("config X is 5s", "config X is 5s")


def test_auto_supersede_skips_complementary_fact(tmp_path) -> None:
    """End-to-end: even with auto_supersede=True, a COMPLEMENTARY older fact
    sharing the entity is contested, NOT superseded — the conflict guard saves it
    from being wrongly deleted from the live set."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    es = EntityStore(db_path=entity_kg_path_for(sm.db_path))
    cs = ContradictionStore(sm.db_path)
    # complementary older fact: different attribute (owner), same entity
    comp = Fact(id="comp", proposition="config X owner is Bob", topic="t",
                status="verified", confidence=0.9, created_at=_NOW - 30 * _DAY)
    new = Fact(id="new", proposition="config X is 5s", topic="t",
               status="verified", confidence=0.9, created_at=_NOW)
    sm.store(comp)
    sm.store(new)
    eid = es.store(Entity(canonical_name="config_x", type="config"))
    es.link_fact("comp", eid)
    es.link_fact("new", eid)
    res = reconcile_against_corpus(sm, new, es, contradiction_store=cs, now=_NOW,
                                   auto_supersede=True)
    assert sm.get("comp").superseded_by is None, "complementary fact must survive"
    # the conflict filter EXCLUDES the complementary fact entirely — neither
    # superseded nor (falsely) contested. This is the fix the real-corpus
    # dry-run forced: no contested-storm on shared-but-unrelated facts.
    assert "comp" not in res["superseded"]
    assert "comp" not in res["contested"]
