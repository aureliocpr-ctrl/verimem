"""Entity-live write path (2026-06-10) — closes the critic caveat on 2aa6769.

The backfill made the entity KG real (7 570 entities from the live corpus)
but extraction ran only as a one-shot script: facts stored AFTER the
backfill never entered the graph, so KG coverage decayed over time. These
tests pin the wiring of extract→store→link→co-occur edges into
``SemanticMemory.store()``:

  - sibling path derivation (tests never touch the live ~/.engram KG)
  - default ON, opt-out via ENGRAM_ENTITY_LIVE=0
  - quarantined facts never enter the graph
  - best-effort: a KG failure must never break store()
  - idempotent on re-store of the same fact

RED marker: ``entity_kg_path_for`` / ``populate_entities_for_fact`` must
exist in verimem.entity_populate and store() must populate the sibling KG.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.entity_kg import EntityStore
from verimem.entity_populate import (
    entity_kg_path_for,
    populate_entities_for_fact,
)
from verimem.semantic import Fact, SemanticMemory

# Deterministic extraction targets: module path + snake_case identifier.
PROP = "community_detector fix shipped in engram/semantic.py via strict TDD"


def _mem(tmp_path: Path) -> SemanticMemory:
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    return SemanticMemory(db_path=db)


def _kg_of(mem: SemanticMemory) -> EntityStore:
    return EntityStore(db_path=entity_kg_path_for(mem.db_path))


# ── path derivation ─────────────────────────────────────────────────────────

def test_kg_path_semantic_layout(tmp_path: Path) -> None:
    """<root>/semantic/semantic.db → <root>/entity_kg/entity_kg.db (live layout)."""
    p = entity_kg_path_for(tmp_path / "semantic" / "semantic.db")
    assert p == tmp_path / "entity_kg" / "entity_kg.db"


def test_kg_path_flat_layout(tmp_path: Path) -> None:
    """A bare tmp db must keep the KG inside the same tmp dir (test isolation)."""
    p = entity_kg_path_for(tmp_path / "x.db")
    assert p == tmp_path / "entity_kg" / "entity_kg.db"


# ── single-fact populate primitive ──────────────────────────────────────────

def test_populate_single_fact_links_and_edges(tmp_path: Path) -> None:
    kg = EntityStore(db_path=tmp_path / "kg" / "entity_kg.db")
    linked, edges = populate_entities_for_fact("f1", PROP, kg)
    assert linked >= 2, "module path + identifier must both extract"
    assert edges >= 2, "co-occurrence clique must be wired"
    e = kg.get_by_name("community_detector")
    assert e is not None
    assert "f1" in kg.facts_for_entity(e.id)


def test_populate_single_fact_no_entities(tmp_path: Path) -> None:
    kg = EntityStore(db_path=tmp_path / "kg" / "entity_kg.db")
    linked, edges = populate_entities_for_fact("f2", "nessuna entita qui", kg)
    assert (linked, edges) == (0, 0)


# ── store() wiring ──────────────────────────────────────────────────────────

def test_store_populates_sibling_kg(tmp_path: Path) -> None:
    mem = _mem(tmp_path)
    f = Fact(proposition=PROP, topic="project/engram")
    mem.store(f, embed="defer")
    kg = _kg_of(mem)
    e = kg.get_by_name("community_detector")
    assert e is not None, "stored fact's entities must land in the sibling KG"
    assert f.id in kg.facts_for_entity(e.id)
    assert kg.edges_from(e.id), "co-occurrence edges must be wired at write time"


def test_store_is_idempotent_on_restore(tmp_path: Path) -> None:
    mem = _mem(tmp_path)
    f = Fact(proposition=PROP, topic="project/engram")
    mem.store(f, embed="defer")
    mem.store(f, embed="defer")  # re-store same id (UPSERT path)
    kg = _kg_of(mem)
    e = kg.get_by_name("community_detector")
    assert e is not None
    assert kg.facts_for_entity(e.id).count(f.id) == 1, "no duplicate links"


def test_store_quarantined_skips_kg(tmp_path: Path) -> None:
    mem = _mem(tmp_path)
    f = Fact(proposition=PROP, topic="project/engram", status="quarantined")
    mem.store(f, embed="defer")
    kg = _kg_of(mem)
    assert kg.get_by_name("community_detector") is None, (
        "a quarantined fact must never seed the entity graph"
    )


def test_store_optout_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENGRAM_ENTITY_LIVE", "0")
    mem = _mem(tmp_path)
    f = Fact(proposition=PROP, topic="project/engram")
    mem.store(f, embed="defer")
    kg = _kg_of(mem)
    assert kg.count() == 0, "opt-out must skip entity-live entirely"


def test_kg_failure_never_breaks_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import verimem.semantic as sm_mod

    def _boom(*a: object, **k: object) -> tuple[int, int]:
        raise RuntimeError("synthetic KG failure")

    monkeypatch.setattr(
        "verimem.entity_populate.populate_entities_for_fact", _boom,
    )
    mem = _mem(tmp_path)
    f = Fact(proposition=PROP, topic="project/engram")
    mem.store(f, embed="defer")  # must NOT raise
    assert mem.get(f.id) is not None, "fact must persist despite KG failure"
    assert sm_mod is not None  # keep the import referenced
