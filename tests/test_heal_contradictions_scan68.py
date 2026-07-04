"""TDD — heal_contradictions: self-healing del corpus (P0a/3, 2026-06-02).

Processa le contraddizioni GIA rilevate (ContradictionStore) e, per ogni coppia
con trust DIVERSO (_STATUS_RANK), invalida (supersede) il fatto piu debole verso
il piu forte e marca la contraddizione risolta. Trust pari -> lasciata
unresolved (serve giudizio umano: non sappiamo quale lato sia giusto).
Reversibile (supersede), zero-delete. NON rileva nuove contraddizioni (quello e
scan_corpus) — agisce solo su cio che il detector ha gia trovato. HERMETIC.
"""
from __future__ import annotations

from engram.contradiction import (
    Contradiction,
    ContradictionStore,
    heal_contradictions,
)
from engram.semantic import Fact, SemanticMemory


def _setup(tmp_path):
    db = tmp_path / "sm.db"
    return SemanticMemory(db_path=db), ContradictionStore(db)


def test_heal_supersedes_lower_trust_and_resolves(tmp_path):
    mem, store = _setup(tmp_path)
    mem.store(Fact(id="weak", proposition="NEXUS has 17280 tests",
                   topic="project/nexus/tests", status="legacy_unverified"))
    mem.store(Fact(id="strong", proposition="NEXUS has 9999 tests",
                   topic="project/nexus/tests", status="model_claim"))
    store.add(Contradiction(fact_a_id="weak", fact_b_id="strong",
                            kind="numeric_clash", similarity=0.95))

    out = heal_contradictions(mem, store)

    assert "weak" in out["healed_superseded"]        # debole invalidato
    assert mem.get("weak").superseded_by == "strong"
    assert mem.get("strong").superseded_by is None   # forte intatto
    assert store.count_unresolved() == 0             # contraddizione risolta


def test_heal_skips_equal_trust(tmp_path):
    mem, store = _setup(tmp_path)
    mem.store(Fact(id="x", proposition="metric 5", topic="t", status="model_claim"))
    mem.store(Fact(id="y", proposition="metric 9", topic="t", status="model_claim"))
    store.add(Contradiction(fact_a_id="x", fact_b_id="y",
                            kind="numeric_clash", similarity=0.9))

    out = heal_contradictions(mem, store)

    assert out["healed_superseded"] == []
    assert mem.get("x").superseded_by is None
    assert mem.get("y").superseded_by is None
    assert store.count_unresolved() == 1             # lasciata a giudizio umano


def test_heal_resolves_when_a_fact_missing(tmp_path):
    mem, store = _setup(tmp_path)
    mem.store(Fact(id="alone", proposition="solo", topic="t", status="model_claim"))
    store.add(Contradiction(fact_a_id="alone", fact_b_id="ghost",
                            kind="numeric_clash", similarity=0.9))

    out = heal_contradictions(mem, store)

    assert store.count_unresolved() == 0             # coppia non piu valida -> risolta
    assert mem.get("alone").superseded_by is None    # il fatto presente resta intatto
