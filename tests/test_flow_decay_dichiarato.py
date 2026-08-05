"""La passata di decadimento riscrive tutto il corpus, in silenzio.

Censimento delle camere dark (ws6, 2026-08-05): `run_decay_pass`
(`decay_job.py:124`) legge OGNI riga di `facts` e ne riscrive la
`confidence` con un solo `executemany`. È la scrittura di massa del
prodotto — e non emetteva un evento, quindi su una superficie viva
migliaia di righe cambiavano valore senza che nulla lo dicesse.

E c'è l'asimmetria che rende la camera un problema di governo e non solo
di telemetria: **la passata non guarda il verdetto**. Un fatto giudicato
99 dal moat e una pretesa mai giudicata decadono con la stessa formula,
e vengono decadute anche le righe RITIRATE e QUARANTINATE, che non
vengono servite a nessuno.

Qui non si decide niente: la passata continua a toccare esattamente le
stesse righe di prima. Si DICHIARA chi ha toccato — la stessa scelta di
`hidden_records`, che non decide ma dichiara.
"""
from __future__ import annotations

import json
import sqlite3
import time

import pytest

from verimem import event_jsonl_log, flow_events
from verimem.client import Memory
from verimem.decay_job import run_decay_pass

_GIORNO = 86400.0


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    flow_events.reset_flow_context()
    return Memory(tmp_path / "memory.db"), tmp_path


def _flow(tmp_path, name="flow.decay"):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()
            if json.loads(ln).get("name") == name]


def _invecchia(m: Memory, fid: str, giorni: float) -> None:
    """Sposta indietro created_at: la passata decade dal tempo trascorso."""
    with sqlite3.connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET created_at = ?, confidence = 0.9 "
                    "WHERE id = ?", (time.time() - giorni * _GIORNO, fid))


def _scrivi(m: Memory, testo: str, topic: str = "hq") -> str:
    return m.add(testo, topic=topic, verified_by=["doc"])["id"]


def test_una_passata_che_scrive_esce_sul_canale(mem):
    """La scrittura di massa non può essere l'unica muta."""
    m, tmp = mem
    _invecchia(m, _scrivi(m, "the head office is in Milan"), 120)

    out = run_decay_pass(m.semantic)
    assert out["facts_updated"] >= 1

    evts = _flow(tmp)
    assert len(evts) == 1, "una passata che riscrive il corpus deve dirlo"
    p = evts[0]["payload"]
    assert p["facts_seen"] == out["facts_seen"]
    assert p["facts_updated"] == out["facts_updated"]
    assert p["dry_run"] is False


def test_la_passata_in_prova_non_si_traveste_da_scrittura(mem):
    """Un `dry_run` che emette lo stesso evento di una passata vera è una
    bugia sul feed: chi guarda vede migliaia di righe cambiate e non è
    successo niente."""
    m, tmp = mem
    _invecchia(m, _scrivi(m, "the head office is in Milan"), 120)

    run_decay_pass(m.semantic, dry_run=True)
    evts = _flow(tmp)
    assert len(evts) == 1
    assert evts[0]["payload"]["dry_run"] is True


def test_il_sommario_separa_i_giudicati_dai_mai_giudicati(mem):
    """L'asimmetria che rende la camera un problema di GOVERNO: il
    verdetto del moat non entra nella formula. Il conteggio da solo non
    lo mostra — serve il rapporto fra le due popolazioni."""
    m, tmp = mem
    giudicato = _scrivi(m, "the head office is in Milan")
    mai = _scrivi(m, "the branch office is in Rome")
    for fid in (giudicato, mai):
        _invecchia(m, fid, 120)
    with sqlite3.connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET grounding_score = 99.4 WHERE id = ?",
                    (giudicato,))

    out = run_decay_pass(m.semantic)
    pop = out["updated_by_population"]
    assert pop["grounded"] == 1, out
    assert pop["never_judged"] == 1, out
    assert _flow(tmp)[0]["payload"]["updated_by_population"] == pop


def test_conta_a_parte_le_righe_che_non_servono_a_nessuno(mem):
    """Ritirati e quarantinati vengono decaduti come gli altri: sono
    righe che il prodotto non restituisce, e il lavoro speso su di loro
    non si vedeva da nessuna parte."""
    m, tmp = mem
    # tre topic distinti: nello stesso, il write path li ritira gia' fra
    # loro da solo e il supersede esplicito qui sotto chiuderebbe un ciclo
    vivo = _scrivi(m, "the head office is in Milan", topic="hq/a")
    ritirato = _scrivi(m, "the depot is in Turin", topic="hq/b")
    quarantinato = _scrivi(m, "the branch office is in Rome", topic="hq/c")
    for fid in (vivo, ritirato, quarantinato):
        _invecchia(m, fid, 120)
    m.semantic.supersede(ritirato, vivo, principal="test:decay",
                         reason="banco")
    m.semantic.quarantine_fact(quarantinato, reason="banco")

    pop = run_decay_pass(m.semantic)["updated_by_population"]
    assert pop["servable"] == 1, pop
    assert pop["retired"] == 1, pop
    assert pop["quarantined"] == 1, pop


def test_dichiara_a_cosa_e_cieca(mem):
    """Un numero senza la sua definizione è il difetto che questo ramo
    cura: la ripartizione va letta sapendo che la formula NON legge né il
    verdetto né lo stato."""
    m, _ = mem
    _invecchia(m, _scrivi(m, "the head office is in Milan"), 120)

    cieca = run_decay_pass(m.semantic)["decays_regardless_of"]
    assert "grounding_score" in cieca and "superseded" in cieca, cieca


@pytest.mark.asyncio
async def test_la_porta_mcp_consegna_la_ripartizione(tmp_path, monkeypatch):
    """`hippo_decay_run` è l'UNICA porta da cui la passata si comanda: se
    la ripartizione non esce di lì, non esiste per nessun chiamante.
    Stessa regola già consegnata su questo ramo — una funzione di governo
    esce su tutte le porte nello stesso commit, non nel prossimo."""
    import json as _json

    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server

    m = Memory(tmp_path / "m.db")
    _invecchia(m, _scrivi(m, "the head office is in Milan"), 120)

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = m.semantic

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    handler = mcp_server.server.request_handlers[CallToolRequest]
    res = await handler(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name="hippo_decay_run", arguments={})))
    payload = res.root if hasattr(res, "root") else res
    out = _json.loads(next(c.text for c in payload.content
                           if hasattr(c, "text")))

    assert out["facts_updated"] >= 1, out
    assert set(out["updated_by_population"]) == {
        "grounded", "never_judged", "servable", "retired", "quarantined"}
    assert "grounding_score" in out["decays_regardless_of"]


def test_una_passata_che_non_cambia_niente_non_emette(mem):
    """Stessa regola del ramo idempotente della cancellazione: un evento
    per un non-cambiamento è rumore, e su un corpus fermo la passata gira
    a vuoto ogni volta che il worker la chiama."""
    m, tmp = mem
    _scrivi(m, "the head office is in Milan")  # appena creato: non decade

    out = run_decay_pass(m.semantic)
    assert out["facts_updated"] == 0
    assert _flow(tmp) == []
