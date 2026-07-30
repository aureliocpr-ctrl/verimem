"""Chi scrive un episodio deve sapere che fine hanno fatto i suoi fatti.

F2 dal dogfooding in parallelo, e sono DUE difetti nello stesso punto
(``mcp_server.py``, il ramo ``key_facts`` di ``hippo_record_episode``):

1. LA SOURCE VIENE BUTTATA IN SILENZIO. Il gate riceve
   ``proposition/topic/verified_by`` e nient'altro: il campo ``source`` non e'
   nello schema e non e' letto dall'handler. Quindi su questo canale il moat
   dell'entailment — la promessa d'esordio del server, «WITH a source: the
   entailment moat, the strong check» — NON PUO' girare, per costruzione. Non
   e' spento per configurazione: non c'e' proprio il modo di accenderlo.

2. L'ESITO DEL GATE NON ESCE. Un ``reject`` fa ``continue`` con un log
   server-side; un ``downgrade`` scrive il fatto ``quarantined``, cioe' fuori
   dal recall di default. In entrambi i casi il chiamante riceve ``fact_ids``
   nudi: l'id di un fatto sano e quello di un fatto quarantinato sono
   indistinguibili, e il fatto rifiutato semplicemente non c'e' senza che
   nessuno lo dica. ``hippo_remember`` la ricevuta ce l'ha (moat, warnings,
   knobs); questo canale no.

Il secondo difetto e' il piu' insidioso: un agente che registra un episodio con
i suoi key_facts crede di aver salvato, e meta' di quei fatti puo' essere in
quarantena. Il prodotto esiste per rendere visibile esattamente questo.
"""
from __future__ import annotations

import json

import pytest


@pytest.fixture()
def store(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    return tmp_path


async def _registra(**kw):
    from verimem import mcp_server as s
    base = {"task_text": "un lavoro qualsiasi", "outcome": "success",
            "final_answer": "fatto"}
    base.update(kw)
    out = await s.call_tool("hippo_record_episode", base)
    return json.loads(out[0].text)


@pytest.mark.asyncio
async def test_lo_schema_dichiara_la_source(store):
    """Se il campo non e' nello schema, nessun chiamante sa di poterlo passare
    — ed e' il campo che fa girare il moat."""
    from verimem import mcp_server as s
    tool = next(t for t in await s.list_tools()
                if t.name == "hippo_record_episode")
    testo = json.dumps(tool.inputSchema)
    assert "source" in testo, (
        "lo schema di key_facts non nomina `source`: su questo canale il moat "
        "non puo' girare e nessuno puo' saperlo")


@pytest.mark.asyncio
async def test_ogni_key_fact_dice_che_fine_ha_fatto(store):
    """Non `fact_ids` nudi: un esito per fatto, con la proposizione."""
    r = await _registra(key_facts=[
        {"proposition": "Il server di produzione sta a Francoforte.",
         "topic": "infra"},
    ])
    esiti = r.get("key_facts_outcome")
    assert isinstance(esiti, list) and len(esiti) == 1, r
    e = esiti[0]
    assert e.get("status") in {"model_claim", "quarantined", "rejected",
                               "failed"}, e
    assert e.get("proposition"), e


@pytest.mark.asyncio
async def test_un_fatto_quarantinato_NON_sembra_uguale_a_uno_sano(store):
    """Il difetto centrale: oggi i due id sono indistinguibili."""
    r = await _registra(key_facts=[
        {"proposition": "Il backup gira ogni notte alle 3.", "topic": "infra"},
        # auto-elogio senza evidenza: il gate lessicale lo declassa
        {"proposition": "This works perfectly and is fully verified.",
         "topic": "infra"},
    ])
    esiti = {e["proposition"][:20]: e for e in r["key_facts_outcome"]}
    assert len(esiti) == 2, r
    stati = {e["status"] for e in r["key_facts_outcome"]}
    assert stati != {"model_claim"}, (
        f"tutti e due dichiarati sani: il declassamento non viene riportato "
        f"({r['key_facts_outcome']})")


@pytest.mark.asyncio
async def test_la_source_arriva_al_gate_e_il_verdetto_esce(store):
    """Con una fonte che implica il fatto, l'esito deve poterlo dire."""
    r = await _registra(key_facts=[
        {"proposition": "La suite ha riportato 2 test passati.",
         "topic": "ci",
         "source": "tests/test_x.py::test_uno PASSED\n"
                   "tests/test_x.py::test_due PASSED\n"
                   "==== 2 passed in 1.20s ===="},
    ])
    e = r["key_facts_outcome"][0]
    assert "moat" in e, f"l'esito non dice se il moat ha giudicato: {e}"


@pytest.mark.asyncio
async def test_fact_ids_resta_per_chi_gia_lo_usa(store):
    """La ricevuta si aggiunge, non sostituisce: rompere i chiamanti esistenti
    per migliorare la diagnostica sarebbe un pessimo scambio."""
    r = await _registra(key_facts=[
        {"proposition": "Il server di produzione sta a Francoforte.",
         "topic": "infra"}])
    assert "fact_ids" in r and isinstance(r["fact_ids"], list), r
