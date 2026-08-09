"""La cancellazione si vede quanto un ritiro.

Censimento delle camere dark (ws6, 2026-08-05): un ritiro emette
`flow.supersession`, una quarantena `flow.quarantine`, il rilascio
`flow.restore` — e la CANCELLAZIONE, che è l'azione più distruttiva del
prodotto, spariva in silenzio. È anche l'unica che non si annulla quando
non c'era snapshot, e che sopravvive solo nelle copie del worker
(`forget_with_report`).

`undoable` viaggia con l'evento perché è la differenza che conta sul
momento: la stessa riga di feed racconta una cancellazione reversibile e
una definitiva, e chi guarda deve poterle distinguere senza andare a
cercare altrove.
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


def _flow(tmp_path, name="flow.forget"):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()
            if json.loads(ln).get("name") == name]


def test_una_cancellazione_esce_sul_canale(mem):
    m, tmp = mem
    fid = m.add(_FATTO, topic="hq", verified_by=["doc"])["id"]
    assert m.semantic.delete(fid, principal="test:forget", action="forget")

    evts = _flow(tmp)
    assert len(evts) == 1, "l'azione piu' distruttiva non puo' essere muta"
    p = evts[0]["payload"]
    assert p["fact_id"] == fid and p["action"] == "forget"
    assert p["undoable"] is False, p
    assert _FATTO not in json.dumps(p), "metadati, mai il testo"


def test_una_cancellazione_annullabile_lo_dichiara(mem):
    """La stessa riga di feed deve distinguere il definitivo dal reversibile."""
    m, tmp = mem
    fid = m.add(_FATTO, topic="hq", verified_by=["doc"])["id"]
    res = m.semantic.delete_with_undo(fid, principal="test:forget")
    assert res["removed"] is True and res["op_id"]

    p = _flow(tmp)[-1]["payload"]
    assert p["undoable"] is True, p


def test_una_cancellazione_a_vuoto_non_emette(mem):
    """Un id inesistente non cancella niente: un evento per un
    non-cambiamento è rumore (stessa regola del ramo idempotente)."""
    m, tmp = mem
    assert m.semantic.delete("00000000dead", principal="test:forget") is False
    assert _flow(tmp) == []
