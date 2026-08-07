"""Anche su MCP il pavimento tagliava un ranking che non aveva misurato nulla.

QUARTA GENERAZIONE DELLA STESSA CURA, e la terza è documentata nel codice::

    «Questo handler chiama `a.semantic` direttamente e non passa da
     `Memory.search`, quindi la cura di un'ora prima non lo raggiungeva: la
     stessa forma per cui quella del 29/07 si era fermata a `explain`.»
                                             — mcp_server.py, sopra il pavimento

Due ore fa ho curato su `Memory.search` il caso in cui l'encoder non risponde
entro il budget: `SemanticMemory.recall` cade sul ramo keyword e assegna
``score 0.0`` a TUTTI i risultati — che non è «nessuna somiglianza» ma
«somiglianza NON MISURATA» — e il pavimento, confrontandolo con una soglia di
somiglianza, taglia tutto. Misurato allora::

    a caldo      [0.8995] la risposta giusta · min_relevance=0.5 -> 1 risultato
    degradato    [0.0]    LA STESSA risposta · min_relevance=0.5 -> 0 risultati

⚠️ E LA MIA CURA NON RAGGIUNGEVA MCP, per il motivo scritto nel commento sopra.
Questo è **il canale degli AGENTI**, cioè il primo posto in cui il prodotto
scrive «abstention over hallucination»: qui un'astensione falsa costa più che
altrove, perché chi la riceve è un modello che non ha modo di sospettarla.

La cura è la stessa: il pavimento non si applica quando il ranking è degradato,
e il degrado si dichiara (``ranking: "keyword"``).
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import tempfile

import pytest

import verimem.semantic as sem
from verimem import Memory

MAGAZZINI = [f"Il magazzino K-{70 + i} di Rovigo ha {4000 + i * 100} "
             f"metri quadrati." for i in range(1, 6)]
DOMANDA = "Quanti metri quadrati ha il magazzino K-77?"


@pytest.fixture()
def mcp(monkeypatch):
    from verimem import mcp_server as srv

    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    for t in MAGAZZINI:
        m.add(t, topic="az/mag")

    class _Ag:
        semantic = m.semantic
        memory = m
    monkeypatch.setattr(srv, "_ag", lambda: _Ag())

    def _call(tool: str, args: dict) -> dict:
        return json.loads(asyncio.run(srv.call_tool(tool, args))[0].text)
    return _call


@pytest.fixture()
def degradato(monkeypatch):
    """Forza il ramo keyword: la stessa strada che il codice prende da solo
    quando il daemon di encode è freddo o contenduto."""
    monkeypatch.setattr(sem, "_encode_prepared_within_budget",
                        lambda *a, **k: None)


def test_il_pavimento_non_svuota_un_ranking_degradato(mcp, degradato):
    """IL CUORE: la risposta giusta c'è, il fallback la trova, e il pavimento
    la buttava via per uno zero che non era una misura."""
    out = mcp("hippo_facts_recall", {"query": DOMANDA, "k": 3,
                                     "min_relevance": 0.5})
    fatti = out.get("items") or []
    assert fatti, f"il pavimento ha svuotato un recall degradato: {out}"


def test_il_degrado_si_dichiara_anche_agli_agenti(mcp, degradato):
    """Chi legge deve sapere che quello `0.0` non è una somiglianza bassa: è
    una somiglianza non misurata. Su questo canale il lettore è un modello."""
    out = mcp("hippo_facts_recall", {"query": DOMANDA, "k": 3})
    fatti = out.get("items") or []
    assert fatti
    assert any(f.get("ranking") == "keyword" for f in fatti), fatti[0]


def test_a_caldo_il_pavimento_taglia_ancora(mcp):
    """IL PRESIDIO. La cura toglie il taglio SOLO sul ramo degradato: dove la
    somiglianza è stata misurata davvero, il pavimento fa il suo mestiere — ed
    è la garanzia che questo file esisteva per difendere."""
    out = mcp("hippo_facts_recall", {"query": "quale database usa il cluster",
                                     "k": 3, "min_relevance": 0.99})
    fatti = out.get("items") or []
    assert not fatti, f"a caldo un pavimento a 0.99 deve svuotare: {out}"


def test_il_ranking_top_level_PERDE_una_voce_invece_di_dichiararla(mcp, degradato):
    """DIFETTO SEPARATO, dichiarato e non curato qui.

    Il payload porta un campo `ranking` che descrive le fasi, col vocabolario
    giusto gia' pronto::

        a caldo    {"rerank": "applied", "fusion": "skipped_small_corpus"}
        degradato  {"fusion": "skipped_small_corpus"}          <- «rerank» SPARISCE

    Un'ASSENZA al posto di una dichiarazione: chi legge non sa che il ranking
    e' degradato, vede solo che una voce manca. E' la stessa classe che questo
    file cura a livello di item — il vocabolario per dirlo esiste gia'
    (`applied`, `skipped_small_corpus`), manca la parola.

    Il test lo FOTOGRAFA cosi' com'e': quando qualcuno lo curera', cadra' da
    solo e chi lo legge trovera' qui il perche'."""
    out = mcp("hippo_facts_recall", {"query": DOMANDA, "k": 3})
    assert "rerank" not in (out.get("ranking") or {}), (
        "curato? allora aggiorna questo test e la nota che lo accompagna")


def test_a_caldo_non_si_dichiara_nessun_degrado(mcp):
    out = mcp("hippo_facts_recall", {"query": DOMANDA, "k": 3})
    fatti = out.get("items") or []
    assert fatti
    assert all("ranking" not in f for f in fatti), fatti[0]
