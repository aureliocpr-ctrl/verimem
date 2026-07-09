"""Reasoning dossier: la risposta multi-hop CON la sua derivazione citata.

``traced_paths`` dà la catena di edge; questo layer la rende una risposta di
prodotto: recupera la PROPOSIZIONE reale dietro ogni salto (dal fatto che
l'ha generato) e compone una derivazione leggibile e citabile — oppure
un'ASTENSIONE onesta quando un salto non è fondato. È il TrustReport del
ragionamento: nessun competitor risponde a un multi-hop mostrando il perché.
"""
from __future__ import annotations

import pytest

from engram.entity_kg import Entity, EntityStore
from engram.graph_reasoning import reasoning_dossier


class _StubSemantic:
    """Recupera la proposition per fact_id (come SemanticMemory.get)."""

    def __init__(self, facts: dict[str, str]):
        self._f = facts

    def get(self, fact_id, *, live_only: bool = False):
        prop = self._f.get(fact_id)
        if prop is None:
            return None
        return type("F", (), {"proposition": prop, "id": fact_id})()


@pytest.fixture()
def kg(tmp_path):
    s = EntityStore(db_path=tmp_path / "kg.db")
    for name, eid in [("Alice", "e_alice"), ("Bob", "e_bob"),
                      ("Acme", "e_acme"), ("Carol", "e_carol")]:
        s.store(Entity(canonical_name=name, type="x", id=eid))
    s.add_edge("e_alice", "e_bob", "married_to", 0.9, "f_marry")
    s.add_edge("e_bob", "e_acme", "works_at", 0.7, "f_job")
    s.add_edge("e_alice", "e_carol", "friend_of", 0.5, None)  # non fondato
    return s


@pytest.fixture()
def sem():
    return _StubSemantic({
        "f_marry": "Alice is married to Bob.",
        "f_job": "Bob works at Acme Corporation.",
    })


def test_grounded_two_hop_dossier_cites_every_step(kg, sem):
    d = reasoning_dossier(kg, sem, "e_alice", target="e_acme", max_hops=2)
    assert d["grounded"] is True
    assert d["abstained"] is False
    assert d["answer"] == "Acme"
    # la derivazione porta le PROPOSIZIONI reali, non solo i predicati
    props = [step["proposition"] for step in d["derivation"]]
    assert props == ["Alice is married to Bob.", "Bob works at Acme Corporation."]
    assert [s["source_fact_id"] for s in d["derivation"]] == ["f_marry", "f_job"]
    # una riga leggibile "come lo so"
    assert "Alice is married to Bob." in d["chain"]
    assert "Bob works at Acme Corporation." in d["chain"]


def test_ungrounded_path_abstains_with_reason(kg, sem):
    d = reasoning_dossier(kg, sem, "e_alice", target="e_carol", max_hops=1)
    assert d["abstained"] is True
    assert d["grounded"] is False
    assert "friend_of" in d["reason"] or "not grounded" in d["reason"].lower()
    assert d.get("answer") is None, "non affermare una derivazione non fondata"
    assert d["target_name"] == "Carol", (
        "anche l'astensione porta il NOME del target (una UI non mostra id)")


def test_missing_source_fact_abstains_not_fabricates(kg):
    """Il salto CITA un fatto ma il fatto è sparito dallo store (supersede/
    delete): non si inventa il testo, si astiene onestamente."""
    empty = _StubSemantic({"f_marry": "Alice is married to Bob."})  # manca f_job
    d = reasoning_dossier(kg, empty, "e_alice", target="e_acme", max_hops=2)
    assert d["abstained"] is True
    assert "f_job" in d["reason"]


def test_no_target_returns_all_grounded_dossiers(kg, sem):
    ds = reasoning_dossier(kg, sem, "e_alice", max_hops=2)
    assert isinstance(ds, list)
    grounded = [d for d in ds if d["grounded"]]
    assert any(d["answer"] == "Acme" for d in grounded)
    # il path non fondato verso Carol c'è ma marcato abstained
    carol = next(d for d in ds if d["target"] == "e_carol")
    assert carol["abstained"] is True


def test_unreachable_target_abstains(kg, sem):
    d = reasoning_dossier(kg, sem, "e_alice", target="e_nowhere", max_hops=2)
    assert d["abstained"] is True
    assert "no path" in d["reason"].lower() or "unreachable" in d["reason"].lower()
