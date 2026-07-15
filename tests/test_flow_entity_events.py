"""La VITA del grafo in diretta: nodi che nascono, nodi che si accendono.

Mandato Aurelio 2026-07-15: "voglio vedere l'attivazione dei nodi live e
quando se ne crea uno nuovo... se guardo il grafo voglio vedere il grafo
live". Il write path popola già il knowledge graph per ogni fatto
(``populate_entities_for_fact``: extract → store → link → co-occur edges);
qui quel lavoro diventa OSSERVABILE con lo stesso canale dei flow events
(observability.emit → events.jsonl → SSE ``/v1/events/flow``):

* ``flow.entity`` — payload ``created`` (i nodi NUOVI, con nome e tipo:
  la UI li fa comparire) + ``touched`` (gli id toccati da questo fatto: la
  UI li fa pulsare) + ``edges`` + ``fact_id``.

Metadati di flusso soltanto: nomi di entità e id, mai il testo del fatto.
Nessun evento se il fatto non tocca il grafo (silenzio = niente rumore).
"""
from __future__ import annotations

import json

import pytest

from engram import event_jsonl_log, flow_events
from engram.entity_kg import EntityStore
from engram.entity_populate import populate_entities_for_fact


@pytest.fixture()
def kg(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("VERIMEM_ACTOR", raising=False)
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    flow_events.reset_flow_context()
    return EntityStore(db_path=tmp_path / "kg.db"), tmp_path


def _events(tmp_path, name="flow.entity"):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        rec = json.loads(ln)
        if rec.get("name") == name:
            out.append(rec)
    return out


_ENTS = [{"name": "Milan", "type": "place"}, {"name": "Acme", "type": "org"}]


def test_new_entities_are_announced_as_created(kg):
    store, tmp = kg
    populate_entities_for_fact("f1", "irrelevant", store, entities=_ENTS)
    evts = _events(tmp)
    assert len(evts) == 1
    p = evts[0]["payload"]
    assert p["fact_id"] == "f1"
    assert {c["name"] for c in p["created"]} == {"Milan", "Acme"}
    assert {c["type"] for c in p["created"]} == {"place", "org"}
    assert len(p["touched"]) == 2
    assert p["edges"] == 2          # clique co_occurs bidirezionale


def test_existing_entities_are_touched_not_created(kg):
    """Il secondo fatto sulle stesse entità: nessuna nascita, solo pulse."""
    store, tmp = kg
    populate_entities_for_fact("f1", "x", store, entities=_ENTS)
    populate_entities_for_fact("f2", "y", store, entities=_ENTS)
    evts = _events(tmp)
    assert len(evts) == 2
    p = evts[1]["payload"]
    assert p["created"] == [], "esistevano già — nessun nodo nuovo"
    assert len(p["touched"]) == 2, "ma si accendono lo stesso"
    assert p["fact_id"] == "f2"


def test_touched_ids_match_the_graph(kg):
    """Gli id nell'evento sono quelli VERI del grafo — la UI li usa per
    accendere i nodi giusti."""
    store, tmp = kg
    populate_entities_for_fact("f1", "x", store, entities=_ENTS)
    p = _events(tmp)[0]["payload"]
    ids_in_graph = {n["id"] for n in store.snapshot()["nodes"]}
    assert set(p["touched"]) <= ids_in_graph
    assert {c["id"] for c in p["created"]} <= ids_in_graph


def test_no_entities_no_event(kg):
    """Un fatto che non tocca il grafo non genera rumore."""
    store, tmp = kg
    populate_entities_for_fact("f1", "", store, entities=[])
    assert _events(tmp) == []


def test_entity_event_carries_surface_and_actor(kg, monkeypatch):
    """Stesso tagging dei flow events: chi ha fatto crescere il grafo."""
    store, tmp = kg
    monkeypatch.setenv("VERIMEM_ACTOR", "claude-code")
    monkeypatch.setenv("ENGRAM_FLOW_SURFACE", "mcp")
    populate_entities_for_fact("f1", "x", store, entities=_ENTS)
    p = _events(tmp)[0]["payload"]
    assert p["actor"] == "claude-code"
    assert p["surface"] == "mcp"


def test_event_carries_no_fact_text(kg):
    """Privacy: metadati di flusso, MAI il contenuto del fatto."""
    store, tmp = kg
    secret = "the CEO said something confidential in the 1:1"
    populate_entities_for_fact("f1", secret, store, entities=_ENTS)
    raw = (tmp / "events.jsonl").read_text(encoding="utf-8")
    assert "confidential" not in raw
