"""L'interruttore saltava proprio il canale per cui il prodotto esiste.

Curato l'SDK (`4e8ca319`), il censimento è stato rifatto sul canale MCP —
quello che un AGENTE usa, e il primo posto dove il prodotto scrive «abstention
over hallucination». Stesso store di tre fatti di listino, stessa domanda fuori
tema, `ENGRAM_MIN_RELEVANCE=0.99`, cioè un pavimento che nulla può superare::

    SDK   Memory.search      -> 0 hit
    MCP   hippo_facts_recall -> 3
    MCP   hippo_facts_search -> 2

Quinta e sesta superficie. `hippo_facts_recall` e `hippo_facts_search` chiamano
`a.semantic` direttamente e non passano da `Memory.search`, quindi la cura di
un'ora fa non li raggiunge — la stessa forma per cui la cura del 29/07 si era
fermata a `explain`.

Il pavimento arriva qui riusando `env_floor_if_set`, non ricopiandone il
criterio: due copie divergono, e in questo file ne stiamo curando la terza
generazione.

E il criterio sta in un cricchetto sullo SCHEMA, così la settima superficie
cade da sola invece di aspettare un altro censimento.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import tempfile

import pytest

from verimem import Memory

LISTINO = ["Il piano annuale costa 100 euro.",
           "La prova gratuita dura 14 giorni.",
           "Il supporto risponde in 24 ore."]
FUORI_TEMA = "quale database usa il cluster di produzione"

#: Le superfici MCP che rispondono a una QUERY con dei FATTI ordinati per
#: RILEVANZA SEMANTICA — quelle per cui «non ho niente di abbastanza vicino» è
#: una risposta possibile perché esiste un punteggio da confrontare.
#:
#: `hippo_facts_search` NON sta qui e non è una dimenticanza: è una SQL LIKE
#: sul testo, senza punteggio, e un pavimento di similarità su un match
#: lessicale confronterebbe due cose diverse. Nel censimento rendeva 2 fatti
#: alla stessa domanda fuori tema, ma per un'altra ragione — il fallback OR
#: che fa matchare le parole funzionali — curata separatamente perché la
#: diagnosi è diversa e le due cure non si sostituiscono.
SUPERFICI = [("hippo_facts_recall", {"k": 3})]


@pytest.fixture()
def mcp(monkeypatch):
    from verimem import mcp_server as srv

    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    for t in LISTINO:
        m.add(t, topic="listino")

    class _Ag:
        semantic = m.semantic
        memory = m
    monkeypatch.setattr(srv, "_ag", lambda: _Ag())

    def _call(tool: str, args: dict) -> dict:
        res = asyncio.run(srv.call_tool(tool, args))
        return json.loads(res[0].text)
    _call.store = m
    return _call


def _quanti(payload: dict) -> int:
    if isinstance(payload.get("count"), int):
        return payload["count"]
    for key in ("items", "results", "facts", "hits"):
        if isinstance(payload.get(key), list):
            return len(payload[key])
    raise AssertionError(f"payload senza una lista di fatti: {list(payload)}")


@pytest.mark.parametrize("tool,extra", SUPERFICI)
def test_l_interruttore_arriva_anche_qui(mcp, monkeypatch, tool, extra):
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "0.99")
    got = _quanti(mcp(tool, {"query": FUORI_TEMA, **extra}))
    assert got == 0, (
        f"{tool} ha servito {got} fatti del listino a una domanda fuori tema "
        f"con il pavimento a 0.99: è il canale degli agenti, quello dove il "
        f"prodotto promette l'astensione")


@pytest.mark.parametrize("tool,extra", SUPERFICI)
def test_senza_la_variabile_niente_cambia(mcp, monkeypatch, tool, extra):
    """La parte deliberatamente non fatta: il default `auto` resta su
    `explain`, dove è stato misurato."""
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    assert _quanti(mcp(tool, {"query": FUORI_TEMA, **extra})) > 0


@pytest.mark.parametrize("tool,extra", SUPERFICI)
def test_un_pavimento_esplicito_batte_l_ambiente(mcp, monkeypatch, tool, extra):
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "off")
    got = _quanti(mcp(tool, {"query": FUORI_TEMA, "min_relevance": 0.99,
                             **extra}))
    assert got == 0


@pytest.mark.parametrize("tool,extra", SUPERFICI)
def test_una_domanda_che_il_corpus_sa_passa(mcp, monkeypatch, tool, extra):
    """Controprova: un pavimento vero non mangia le risposte vere."""
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "0.5")
    assert _quanti(mcp(tool, {"query": "quanto costa il piano annuale",
                              **extra})) > 0


def test_ogni_superficie_a_query_dichiara_il_pavimento():
    """IL CRICCHETTO. Non l'elenco: il criterio. Un tool che prende una
    `query` e rende fatti ordinati deve poter dire «niente di abbastanza
    vicino» — se ne nasce un settimo senza `min_relevance`, questo cade da
    solo invece di aspettare il prossimo censimento a mano."""
    from verimem import mcp_server as srv

    strumenti = asyncio.run(srv.list_tools())
    senza = []
    for t in strumenti:
        nome = getattr(t, "name", "")
        if nome not in {n for n, _ in SUPERFICI}:
            continue
        props = (getattr(t, "inputSchema", None) or {}).get("properties") or {}
        if "min_relevance" not in props:
            senza.append(nome)
    assert not senza, (
        f"superfici di recupero senza un pavimento dichiarato: {senza}\n"
        f"l'SDK e la CLI lo espongono; un agente che legge lo schema conclude "
        f"che su questo canale il prodotto non sappia astenersi")
