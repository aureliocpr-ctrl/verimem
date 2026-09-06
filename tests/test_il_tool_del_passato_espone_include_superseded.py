"""Il tool DEDICATO al passato deve esporre `include_superseded`.

T18 ha chiuso il difetto su SDK e CLI e sulle due porte MCP ordinarie
(`hippo_facts_recall`, `hippo_facts_search`). Restava fuori proprio
`hippo_recall_as_of` — il tool che esiste APPOSTA per leggere il passato:

    schema   properties: query, when, k          -> nessun include_superseded
    gestore  recall_as_of(a.semantic, query,
                          when=…, k=…)           -> non lo passa

mentre `recall_as_of` lo accetta dal 06/09. È la stessa forma di tutto T18 —
la capacità c'è nella funzione e la porta non la espone — sul tool dove pesa di
più: chi chiede «cosa valeva allora, più la storia» a uno strumento chiamato
`recall_as_of` non ha nessun altro posto dove chiederlo.

Il caso è quello della QA, TRE fatti in catena, perché con due sole scritture
le due richieste chiedono la stessa cosa e non separano «i filtri COMPONGONO»
da «uno dei due è IGNORATO»:

    A (asserito _BASE) --ritirato da--> B  … T …  --> C

a **T** il corrente era B, A era già ritirato, C non esisteva.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from verimem import mcp_server
from verimem.semantic import Fact, SemanticMemory

_BASE = 1_700_000_000.0
_DAY = 86400.0
_T = _BASE + 300 * _DAY


@pytest.fixture()
def porta(tmp_path, monkeypatch):
    """Lo store con la catena, agganciato al server MCP."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    for fid, quando, testo in (("A", _BASE, "Il canone e' 2400 euro."),
                               ("B", _BASE + 100 * _DAY, "Il canone e' 2900 euro."),
                               ("C", _BASE + 500 * _DAY, "Il canone e' 3400 euro.")):
        sm.store(Fact(id=fid, proposition=testo, topic="t", asserted_at=quando),
                 embed="sync")
    sm.supersede("A", "B", principal="test:suite", reason="same-source evolution")
    sm.supersede("B", "C", principal="test:suite", reason="same-source evolution")

    class _Agente:
        def __init__(self) -> None:
            self.semantic = sm

    monkeypatch.setattr(mcp_server, "_ag", lambda: _Agente())
    return sm


def _chiama(nome: str, argomenti: dict) -> dict:
    from mcp.types import CallToolRequest, CallToolRequestParams

    async def _vai() -> dict:
        res = await mcp_server.server.request_handlers[CallToolRequest](
            CallToolRequest(method="tools/call",
                            params=CallToolRequestParams(name=nome,
                                                         arguments=argomenti)))
        p = res.root if hasattr(res, "root") else res
        testo = next(c.text for c in p.content if hasattr(c, "text"))
        return json.loads(testo)

    return asyncio.run(_vai())


def _ids(risposta: dict) -> list[str]:
    for chiave in ("items", "results", "facts", "hits"):
        righe = risposta.get(chiave)
        if isinstance(righe, list):
            return sorted(r.get("id") for r in righe if isinstance(r, dict))
    return []


def test_controllo_positivo_il_tool_risponde_il_corrente_di_allora(porta) -> None:
    """Se cade, il resto del file non misura niente."""
    assert _ids(_chiama("hippo_recall_as_of",
                        {"query": "quanto e' il canone", "when": _T,
                         "k": 5})) == ["B"], (
        "a quell'istante il corrente era B: il tool non risponde nemmeno "
        "quello e la cella sotto non separerebbe niente")


def test_lo_schema_dichiara_include_superseded(porta) -> None:
    """⚠️ RED: un client MCP legge lo SCHEMA, non il nostro codice.

    Un parametro che il gestore accettasse senza dichiararlo sarebbe invisibile
    a chi usa il tool: gli strumenti si scoprono dallo schema, ed è l'unica
    documentazione che un agente legge davvero.
    """
    async def _elenco():
        from mcp.types import ListToolsRequest
        res = await mcp_server.server.request_handlers[ListToolsRequest](
            ListToolsRequest(method="tools/list"))
        p = res.root if hasattr(res, "root") else res
        return p.tools

    strumenti = asyncio.run(_elenco())
    quello = next((s for s in strumenti if s.name == "hippo_recall_as_of"), None)
    assert quello is not None, "hippo_recall_as_of non è più esposto"
    proprieta = (quello.inputSchema or {}).get("properties", {})
    assert "include_superseded" in proprieta, (
        f"lo schema del tool DEDICATO al passato non dichiara "
        f"`include_superseded`: espone {sorted(proprieta)}. Le due porte "
        "ordinarie e l'SDK lo hanno da T18; qui no, e un client non può "
        "sapere che la capacità esiste")


def test_il_gestore_lo_INOLTRA_e_non_lo_ingoia(porta) -> None:
    """⚠️ RED: lo schema senza l'inoltro sarebbe una promessa vuota.

    È la coppia che conta: dichiararlo e non usarlo è il difetto che T18 ha
    chiuso ovunque — un parametro accettato e ingoiato in silenzio.
    """
    solo_tempo = _ids(_chiama("hippo_recall_as_of",
                              {"query": "quanto e' il canone", "when": _T,
                               "k": 5}))
    con_storia = _ids(_chiama("hippo_recall_as_of",
                              {"query": "quanto e' il canone", "when": _T,
                               "k": 5, "include_superseded": True}))
    assert solo_tempo == ["B"], "il controllo è cambiato sotto i piedi"
    assert con_storia == ["A", "B"], (
        f"chiedendo i ritirati il tool rende {con_storia}: il parametro "
        "arriva alla porta e non al filtro. A era già ritirato a quell'istante "
        "e deve comparire SOLO quando lo si chiede")


def test_con_poco_spazio_vince_il_corrente(porta) -> None:
    """`k=1`: prima quello che valeva allora, poi la storia se avanza spazio.

    Il difetto era nella cura stessa, trovato il 06/09 sull'SDK e curato con
    due passate; questa cella verifica che la porta MCP erediti la stessa
    priorità invece di reintrodurre il difetto per conto suo.
    """
    assert _ids(_chiama("hippo_recall_as_of",
                        {"query": "quanto e' il canone", "when": _T, "k": 1,
                         "include_superseded": True})) == ["B"], (
        "con posto per un fatto solo ha vinto il RITIRATO: chiedere la storia "
        "non deve far perdere il valore che a quell'istante era vero")
