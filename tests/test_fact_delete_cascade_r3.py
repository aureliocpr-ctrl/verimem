"""Audit 3-round R2 #16 + #10 (correctness): a hard fact-delete must cascade to
its references — episodes already cascade, but a deleted fact left dangling rows.

Two real consequences (both confirmed by the audit):
 * a surviving partner of a contradiction stays 'contested' FOREVER, citing a
   now-deleted fact id (forget() never resolved them — R2 #10);
 * entity_facts links point at a dead id, so PPR/anchor recall surfaces ghosts.

Fix: delete()/delete_with_undo() call _cascade_delete_refs, which resolves the
contradictions involving the id and removes its entity_facts links.
"""
from __future__ import annotations

import sqlite3

from verimem.contradiction import Contradiction, ContradictionStore
from verimem.entity_kg import Entity, EntityStore
from verimem.entity_populate import entity_kg_path_for
from verimem.semantic import Fact, SemanticMemory


def test_delete_resolves_contradictions_and_purges_entity_links(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    a = Fact(proposition="the api timeout is 30s", topic="t")
    b = Fact(proposition="the api timeout is 5s", topic="t")
    sm.store(a)
    sm.store(b)

    cs = ContradictionStore(sm.db_path)
    cs.add(Contradiction(fact_a_id=a.id, fact_b_id=b.id, kind="negation",
                         similarity=0.95))
    assert cs.list_unresolved_for_fact(b.id), "precondition: b is contested by a"

    es = EntityStore(db_path=entity_kg_path_for(sm.db_path))
    eid = es.store(Entity(canonical_name="api_timeout", type="config"))
    es.link_fact(a.id, eid)

    # delete a -> its references must not dangle.
    assert sm.delete(a.id) is True

    # contradiction citing the deleted a is resolved (b no longer 'contested').
    assert cs.list_unresolved_for_fact(b.id) == [], \
        "deleting a fact must resolve contradictions that cite it"

    # entity_facts link to the deleted fact is gone.
    kg = entity_kg_path_for(sm.db_path)
    with sqlite3.connect(str(kg)) as c:
        n = c.execute(
            "SELECT COUNT(*) FROM entity_facts WHERE fact_id = ?", (a.id,),
        ).fetchone()[0]
    assert n == 0, "deleting a fact must purge its entity_facts links"


def test_delete_with_undo_also_cascades(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    a = Fact(proposition="cache ttl is 60s", topic="t")
    b = Fact(proposition="cache ttl is 600s", topic="t")
    sm.store(a)
    sm.store(b)
    cs = ContradictionStore(sm.db_path)
    cs.add(Contradiction(fact_a_id=a.id, fact_b_id=b.id, kind="negation",
                         similarity=0.95))

    res = sm.delete_with_undo(a.id)
    assert res["removed"] is True
    assert cs.list_unresolved_for_fact(b.id) == [], \
        "delete_with_undo must also cascade the contradiction cleanup"
