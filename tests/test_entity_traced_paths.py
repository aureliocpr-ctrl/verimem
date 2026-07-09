"""Traced multi-hop: il traversal che porta con sé la catena di custodia.

Il gap misurato del prodotto è il multi-hop (0.39-0.44). ``neighbors()`` sa
raggiungere un'entità a N salti ma SCARTA il percorso — ritorna il nodo e
l'ultimo predicato, non la catena di edge. Per una memoria che vende FIDUCIA
questo non basta: la risposta multi-hop deve arrivare con la sua derivazione
citabile ("Alice —sposa(conv#3)→ Bob —lavora(doc#7)→ Acme"), e deve poter
ASTENERSI quando un salto non è fondato (edge senza source_fact_id).

``traced_paths`` è quel traversal: ogni percorso porta gli edge con
predicate + source_fact_id + weight, un flag ``grounded`` (ogni salto ha una
fonte) e ``min_weight`` (il salto più debole = la fiducia del percorso). È il
differenziatore: nessun competitor dà un multi-hop verificabile.
"""
from __future__ import annotations

import pytest

from engram.entity_kg import Entity, EntityStore


@pytest.fixture()
def kg(tmp_path):
    s = EntityStore(db_path=tmp_path / "kg.db")
    # Alice --married_to(f_marry)--> Bob --works_at(f_job)--> Acme
    #                                Bob --lives_in(f_live)--> Berlin
    # Alice --friend_of(NO SOURCE)--> Carol   (edge non fondato)
    for name, typ, eid in [
            ("Alice", "person", "e_alice"), ("Bob", "person", "e_bob"),
            ("Acme", "org", "e_acme"), ("Berlin", "place", "e_berlin"),
            ("Carol", "person", "e_carol")]:
        s.store(Entity(canonical_name=name, type=typ, id=eid))
    s.add_edge("e_alice", "e_bob", "married_to", weight=0.9,
               source_fact_id="f_marry")
    s.add_edge("e_bob", "e_acme", "works_at", weight=0.7,
               source_fact_id="f_job")
    s.add_edge("e_bob", "e_berlin", "lives_in", weight=0.8,
               source_fact_id="f_live")
    s.add_edge("e_alice", "e_carol", "friend_of", weight=0.5,
               source_fact_id=None)  # non fondato
    return s


def test_two_hop_path_carries_the_full_chain(kg):
    paths = kg.traced_paths("e_alice", max_hops=2)
    to_acme = [p for p in paths if p["target"] == "e_acme"]
    assert len(to_acme) == 1, "un percorso Alice->Acme a 2 salti"
    hops = to_acme[0]["hops"]
    assert [h["predicate"] for h in hops] == ["married_to", "works_at"]
    assert [h["source_fact_id"] for h in hops] == ["f_marry", "f_job"], (
        "ogni salto porta la sua fonte — la catena di custodia")
    assert [h["dst_entity"] for h in hops] == ["e_bob", "e_acme"]


def test_min_weight_is_the_path_trust(kg):
    p = next(p for p in kg.traced_paths("e_alice", max_hops=2)
             if p["target"] == "e_acme")
    # min(0.9, 0.7) = il salto più debole governa la fiducia del percorso
    assert p["min_weight"] == pytest.approx(0.7)
    assert p["grounded"] is True, "entrambi i salti hanno una fonte"


def test_ungrounded_hop_is_flagged_not_hidden(kg):
    """L'edge Alice->Carol non ha source_fact_id: il percorso esiste ma è
    marcato NON fondato, così l'answerer può astenersi invece di affermare."""
    p = next(p for p in kg.traced_paths("e_alice", max_hops=1)
             if p["target"] == "e_carol")
    assert p["grounded"] is False
    assert p["hops"][0]["source_fact_id"] is None


def test_hop_bound_is_respected(kg):
    one_hop = kg.traced_paths("e_alice", max_hops=1)
    targets = {p["target"] for p in one_hop}
    assert targets == {"e_bob", "e_carol"}, "a 1 salto niente Acme/Berlin"
    two_hop = {p["target"] for p in kg.traced_paths("e_alice", max_hops=2)}
    assert {"e_acme", "e_berlin"} <= two_hop


def test_shortest_path_wins_on_ties(kg):
    """Se un target è raggiungibile a 1 e a 2 salti, vince il più corto
    (meno anelli nella catena = più fiducia)."""
    kg.add_edge("e_alice", "e_acme", "partner_of", weight=0.6,
                source_fact_id="f_direct")
    p = next(p for p in kg.traced_paths("e_alice", max_hops=2)
             if p["target"] == "e_acme")
    assert len(p["hops"]) == 1, "il percorso diretto a 1 salto batte i 2 salti"
    assert p["hops"][0]["source_fact_id"] == "f_direct"


def test_cycle_does_not_loop_forever(kg):
    kg.add_edge("e_acme", "e_alice", "employs", weight=0.5,
                source_fact_id="f_cycle")
    paths = kg.traced_paths("e_alice", max_hops=4)
    # nessun target ripetuto, nessun nodo visitato due volte in un percorso
    for p in paths:
        seen = [h["dst_entity"] for h in p["hops"]]
        assert len(seen) == len(set(seen)), "un percorso non rivisita un nodo"


def test_no_paths_from_isolated_entity(kg):
    kg.store(Entity(canonical_name="Lonely", type="person", id="e_lonely"))
    assert kg.traced_paths("e_lonely", max_hops=3) == []


def test_k_caps_the_result(kg):
    for i in range(20):
        kg.store(Entity(canonical_name=f"N{i}", type="thing", id=f"e_n{i}"))
        kg.add_edge("e_alice", f"e_n{i}", "rel", weight=0.5,
                    source_fact_id=f"f_{i}")
    assert len(kg.traced_paths("e_alice", max_hops=1, k=5)) == 5
