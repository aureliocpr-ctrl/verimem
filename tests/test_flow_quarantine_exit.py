"""L'uscita dalla quarantena si vede quanto l'ingresso.

Censimento delle camere dark (ws6): `quarantine_fact` e `restore_fact`
emettono da cicli gli eventi `fact_quarantined` / `fact_restored` — ma le
superfici live tengono SOLO i nomi che iniziano con ``flow.``
(gateway.py:511, engine.js), quindi:

  * un fatto declassato DOPO la scrittura spariva dal feed senza una riga
    (l'ingresso al write si vede come flow.write status=quarantined, il
    declass successivo del triage no);
  * il rilascio non si vedeva MAI ⇒ la Engine Room mostrava una coda che
    poteva solo crescere.

È la stessa classe dei ritiri silenziosi: il meccanismo c'è, l'evento pure,
e il consumatore non lo vede perché sta fuori dal namespace che ascolta.
Qui si pinna che entrambe le transizioni escono sul canale flow.
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, flow_events
from verimem.client import Memory

_FATTO = "the office headquarters are in Milan"


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    flow_events.reset_flow_context()
    return Memory(tmp_path / "memory.db"), tmp_path


def _flow(tmp_path, name):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        rec = json.loads(ln)
        if rec.get("name") == name:
            out.append(rec)
    return out


def test_il_declass_dopo_la_scrittura_esce_sul_canale_flow(mem):
    m, tmp = mem
    fid = m.add(_FATTO, topic="hq", verified_by=["doc"])["id"]
    assert m.semantic.quarantine_fact(fid, reason="triage tier-2") is True

    evts = _flow(tmp, "flow.quarantine")
    assert len(evts) == 1, "un declass invisibile e' una coda che cresce sola"
    p = evts[0]["payload"]
    assert p["fact_id"] == fid
    assert p["prior_status"] and p["prior_status"] != "quarantined"
    assert p["reason"] == "triage tier-2"


def test_il_rilascio_esce_sul_canale_flow(mem):
    m, tmp = mem
    fid = m.add(_FATTO, topic="hq", verified_by=["doc"])["id"]
    m.semantic.quarantine_fact(fid, reason="triage")
    assert m.semantic.restore_fact(fid, reason="falso positivo") is True

    evts = _flow(tmp, "flow.restore")
    assert len(evts) == 1, (
        "un'azione di governo dev'essere visibile quanto la decisione "
        "che annulla")
    p = evts[0]["payload"]
    assert p["fact_id"] == fid and p["to_status"] == "model_claim"


def test_i_no_op_non_emettono(mem):
    """Un evento per un non-cambiamento è rumore: la stessa regola del
    ramo idempotente del timone."""
    m, tmp = mem
    fid = m.add(_FATTO, topic="hq", verified_by=["doc"])["id"]
    m.semantic.quarantine_fact(fid, reason="triage")
    assert m.semantic.quarantine_fact(fid, reason="di nuovo") is False
    assert len(_flow(tmp, "flow.quarantine")) == 1

    m.semantic.restore_fact(fid)
    assert m.semantic.restore_fact(fid) is False   # non piu' quarantinato
    assert len(_flow(tmp, "flow.restore")) == 1
