"""Il TIMONE — un ritiro si vede e si annulla (ws6, sala di controllo).

Misurato il 2026-08-04 sul canale verimem-coord (banchi ws5): quattro
scritture, tre ritiri, e nessuna azione dell'utente esce dal loop —
riscrivere il fatto perso ne uccide un altro e ``Memory.restore()``
rifiuta i superseded per contratto. La via di ritorno ESISTE dal 27/05
(``facts_undo_log`` prevede ``op_type='supersede'``, ``undo_op``
ripristina la riga con INSERT OR REPLACE) ma nessun chiamante la
alimentava: ``snapshot_pre_op`` aveva UN call site in produzione, per
``'forget'`` (semantic.py:5020).

Questi test pinnano il collegamento nel punto dove convergono TUTTI gli
otto call site di ``.supersede(`` — ``SemanticMemory.supersede`` — così
ogni percorso (same-source post-gate, correct(), reconcile, chain, MCP,
CLI) e ogni porta sono coperti in un colpo:

1. un supersede che muta davvero la riga scrive lo snapshot pre-op;
2. lo stesso supersede emette ``flow.supersession`` (metadati, mai i
   testi delle proposizioni — la Engine Room mostra flusso, non contenuto);
3. ``undo_op`` sull'op registrato riporta il fatto SERVIBILE — la metrica
   canonica della ritrattazione ws3 22:32: ``superseded_by IS NULL AND
   status NOT IN ('quarantined')`` — e il winner resta vivo (il ping-pong
   Rossi/Bianchi finisce con ENTRAMBI, non con un altro ritiro);
4. i rami no-op (idempotente stessa coppia) non snapshottano e non
   emettono: un evento per un non-cambiamento è rumore;
5. ``flow_extra`` arricchisce l'evento senza cambiare firma altrove — è
   il canale con cui il write path (ws3) aggiungerà token_di_ricerca /
   n_candidati_esaminati / limit_applicato senza toccare questo modulo.
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, flow_events
from verimem.client import Memory

_MILAN = "the office headquarters are in Milan"
_TURIN = "the logistics warehouse operates in Turin"


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("VERIMEM_ACTOR", raising=False)
    monkeypatch.delenv("ENGRAM_ACTOR", raising=False)
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    flow_events.reset_flow_context()
    m = Memory(tmp_path / "memory.db")
    return m, tmp_path


def _flow(tmp_path, name=None):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        rec = json.loads(ln)
        if str(rec.get("name", "")).startswith("flow.") and (
                name is None or rec["name"] == name):
            out.append(rec)
    return out


def _due_fatti(m):
    """Due fatti ammessi su topic DIVERSI (nessun auto-ritiro del gate:
    qui si prova il supersede ESPLICITO, il punto di convergenza)."""
    a = m.add(_MILAN, topic="hq/milan", verified_by=["hr-doc"])
    b = m.add(_TURIN, topic="wh/turin", verified_by=["ops-doc"])
    assert a["stored"] and b["stored"]
    return a["id"], b["id"]


def _undo_ops_supersede(m, fact_id):
    return [o for o in m.semantic.list_undoable_ops(limit=50)
            if o["op_type"] == "supersede" and o["fact_id"] == fact_id]


# ---- 1. lo snapshot esiste ---------------------------------------------------

def test_supersede_registra_snapshot_undo(mem):
    m, _ = mem
    a, b = _due_fatti(m)
    res = m.semantic.supersede(a, b, principal="test:timone",
                               reason="manual-test")
    assert res["ok"] is True and res["idempotent_noop"] is False
    ops = _undo_ops_supersede(m, a)
    assert len(ops) == 1, (
        "un supersede che muta la riga deve lasciare l'handle di undo "
        f"(trovati: {ops})")


# ---- 2. l'undo riporta il fatto servibile e il winner resta ------------------

def test_undo_riporta_il_fatto_servibile_e_il_winner_resta(mem):
    m, _ = mem
    a, b = _due_fatti(m)
    m.semantic.supersede(a, b, principal="test:timone", reason="manual-test")
    op_id = _undo_ops_supersede(m, a)[0]["op_id"]

    res = m.semantic.undo_destructive_op(op_id)
    assert res["ok"] is True and res["action"] == "restored"

    fa = m.semantic.get(a)
    assert fa is not None
    assert fa.superseded_by is None, "l'undo deve togliere il ritiro"
    assert fa.status != "quarantined", (
        "servibile = non-superseduto E non-quarantinato (metrica canonica)")
    fb = m.semantic.get(b)
    assert fb is not None and fb.superseded_by is None, (
        "il winner resta vivo: il ping-pong finisce con ENTRAMBI")


# ---- 3. l'evento esce, coi metadati e senza testi ----------------------------

def test_supersede_emette_flow_supersession_coi_metadati(mem):
    m, tmp = mem
    a, b = _due_fatti(m)
    m.semantic.supersede(a, b, principal="test:timone", reason="manual-test")

    evts = _flow(tmp, "flow.supersession")
    assert len(evts) == 1, f"atteso un flow.supersession, trovati {len(evts)}"
    p = evts[0]["payload"]
    assert p["loser_id"] == a and p["winner_id"] == b
    assert p["reason"] == "manual-test"
    assert p["loser_topic"] == "hq/milan" and p["winner_topic"] == "wh/turin"
    assert p["reversible"] is True, (
        "con lo snapshot scritto nello stesso giro, il ritiro nasce annullabile")
    blob = json.dumps(p)
    assert _MILAN not in blob and _TURIN not in blob, (
        "l'evento porta metadati, MAI il testo delle proposizioni")


# ---- 4. il no-op non snapshotta e non emette ---------------------------------

def test_idempotent_noop_niente_snapshot_niente_evento(mem):
    m, tmp = mem
    a, b = _due_fatti(m)
    m.semantic.supersede(a, b, principal="test:timone", reason="manual-test")
    n_ops = len(_undo_ops_supersede(m, a))
    n_evts = len(_flow(tmp, "flow.supersession"))

    res = m.semantic.supersede(a, b, principal="test:timone",
                               reason="manual-test")
    assert res["idempotent_noop"] is True
    assert len(_undo_ops_supersede(m, a)) == n_ops, (
        "il ramo idempotente non deve accumulare handle di undo")
    assert len(_flow(tmp, "flow.supersession")) == n_evts, (
        "il ramo idempotente non deve emettere un secondo evento")


# ---- 5. flow_extra: il canale per i campi ricchi del write path --------------

def test_flow_extra_arricchisce_l_evento(mem):
    m, tmp = mem
    a, b = _due_fatti(m)
    m.semantic.supersede(
        a, b, principal="test:timone", reason="manual-test",
        flow_extra={"branch": "_route_evolutions/evolution",
                    "n_candidati_esaminati": 10})

    p = _flow(tmp, "flow.supersession")[0]["payload"]
    assert p["branch"] == "_route_evolutions/evolution"
    assert p["n_candidati_esaminati"] == 10


# ---- 6. il wiring: la ricevuta SDK porta l'handle ----------------------------

def test_undo_emette_flow_undo(mem):
    """Un'azione di governo dev'essere visibile quanto la mutazione che
    annulla: un undo invisibile ricreerebbe il difetto che il timone cura."""
    m, tmp = mem
    a, b = _due_fatti(m)
    res = m.semantic.supersede(a, b, principal="test:timone",
                               reason="manual-test")
    m.semantic.undo_destructive_op(res["undo_op_id"])
    evts = _flow(tmp, "flow.undo")
    assert len(evts) == 1
    p = evts[0]["payload"]
    assert p["op_type"] == "supersede" and p["fact_id"] == a
    assert p["action"] == "restored"


def test_update_propaga_undo_op_id_nella_ricevuta(mem):
    """``Memory.update`` supersede il vecchio: la ricevuta deve portare
    l'handle — l'utente che corregge DEVE poter tornare indietro senza
    conoscere le tabelle interne (niente agganci scollegati)."""
    m, _ = mem
    a = m.add(_MILAN, topic="hq/milan", verified_by=["hr-doc"])["id"]
    res = m.update(a, "the office headquarters moved to Rome",
                   topic="hq/milan")
    assert res["updated"] is True and res["supersedes"] == a
    assert res.get("undo_op_id"), (
        "la ricevuta dell'update deve portare l'handle di undo")
    undo = m.semantic.undo_destructive_op(res["undo_op_id"])
    assert undo["ok"] is True and undo["action"] == "restored"
    assert m.semantic.get(a).superseded_by is None
