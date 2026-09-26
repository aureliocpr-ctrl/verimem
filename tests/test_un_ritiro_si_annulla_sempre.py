"""Un ritiro si annulla sempre: la finestra di undo di un ritiro e' uno STATO.

Un ritiro (``supersede``) non cancella la riga: la marca. Fino a oggi il suo
handle di undo scadeva dopo 7 giorni e ``prune_expired_undo_log``, che gira a
ogni scrittura distruttiva, lo cancellava: dopo una settimana un ritiro
sbagliato non si poteva piu' annullare con ``verimem facts undo``, anche se il
fatto era ancora li'. Il 23-24/09 un passaggio automatico ha ritirato 41 fatti
veri di uno store vero; senza questa cura i loro handle sparivano il 30/09.
La scadenza resta per i ``forget``, dove la riga non c'e' piu'.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem import event_jsonl_log, flow_events
from verimem.client import Memory
from verimem.undo_log import prune_expired_undo_log

_MILAN = "the office headquarters are in Milan"
_TURIN = "the logistics warehouse operates in Turin"


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    flow_events.reset_flow_context()
    return Memory(tmp_path / "memory.db")


def _ritiro_vecchio_di_otto_giorni(m):
    a = m.add(_MILAN, topic="hq/milan", verified_by=["hr-doc"])["id"]
    b = m.add(_TURIN, topic="wh/turin", verified_by=["ops-doc"])["id"]
    m.semantic.supersede(a, b, principal="test:undo", reason="retired by mistake")
    op_id = next(o["op_id"] for o in m.semantic.list_undoable_ops(limit=50)
                 if o["op_type"] == "supersede" and o["fact_id"] == a)
    with sqlite3.connect(m.semantic.db_path) as c:
        c.execute("UPDATE facts_undo_log SET ttl_expires_at = 1 WHERE op_id = ?",
                  (op_id,))
        prune_expired_undo_log(c)
    return a, b, op_id


def test_l_handle_di_un_ritiro_sopravvive_alla_potatura(mem):
    _a, _b, op_id = _ritiro_vecchio_di_otto_giorni(mem)
    elencati = [o["op_id"] for o in mem.semantic.list_undoable_ops(limit=50)]
    assert op_id in elencati, (
        "l'handle di un ritiro vecchio di otto giorni e' sparito: "
        "un ritiro sbagliato non si puo' piu' annullare")


def test_un_ritiro_vecchio_di_otto_giorni_si_annulla_ancora(mem):
    a, b, op_id = _ritiro_vecchio_di_otto_giorni(mem)
    esito = mem.semantic.undo_destructive_op(op_id)
    assert esito.get("ok") is True and esito.get("action") == "restored", esito
    assert mem.semantic.get(a).superseded_by is None
    assert mem.semantic.get(b).superseded_by is None, "il vincitore resta vivo"
