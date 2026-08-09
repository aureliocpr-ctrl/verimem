"""Una risposta di recall dichiara COME e' stata ordinata.

Misurato il 2026-07-30 sul corpus vero, tre chiamate identiche nello stesso
processo::

    1a (CE freddo, grafo freddo)  [c96a2aa2a2cc, d528b9fd9c9b, bfd30e41eb94,
                                   84932b087fa2, 17cefffe1bce]
    3a (tutto caldo)              [c96a2aa2a2cc, d528b9fd9c9b, 84932b087fa2,
                                   bfd30e41eb94, 93eec6da4302]

Stessa domanda, un fatto DENTRO e uno FUORI, ordine diverso. Nel log del
server c'era la spiegazione::

    rerank cold-load exceeded 0.25s cold budget -> keeping bi-encoder order
    PPR fusion exceeded 2.00s budget -> keeping reranked order

Nella risposta, no: le due avevano le STESSE sei chiavi e nessuno dei 14 campi
per item nominava il degrado. Il prodotto promette «provenance on every read»,
e la provenienza dell'ORDINE — quale dei tre segnali ha davvero concorso — non
usciva da nessuna superficie.

Non e' un difetto di lentezza: i budget FANNO il loro mestiere (2s encode, 3s
rerank / 0.25s a freddo, 2s fusione) ed e' giusto che degradino invece di
appendere il chiamante. E' un difetto di SILENZIO — la stessa classe curata
oggi tre volte: `judge_state` (assente vs sta-scaldando), `key_facts_outcome`
(sano vs quarantinato indistinguibili), l'anello `:removed` del lineage.

Le vie silenziose sono otto per il rerank (query lunga in AUTO, breaker,
documenti fuori finestra CE, slot occupato, thread non partito, overrun a
freddo, overrun a regime, errore dello scorer) e altrettante per la fusione.
Qui si inchiodano quelle DETERMINISTICHE: un segnale spento per configurazione
e un segnale saltato per la lunghezza della query. Il caso «budget sforato»
dipende da una gara di temporizzazione e NON viene inchiodato in un test: un
test che a volte salta e a volte fallisce non presidia niente (stessa ragione
per cui oggi ne ho cancellato uno sul primo tools/call).
"""
from __future__ import annotations

import pytest

from verimem import semantic
from verimem.semantic import Fact, SemanticMemory


@pytest.fixture()
def store(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    sm = SemanticMemory(db_path=tmp_path / "semantic.db")
    for i in range(6):
        sm.store(Fact(proposition=f"Il servizio numero {i} gira su un VPS "
                                  f"di Amsterdam.", topic="prove"))
    return sm


def _stadi(sm, query, k=3):
    semantic.ranking_reset()
    sm.recall(query, k=k)
    return semantic.ranking_stages()


def test_una_recall_dichiara_gli_stadi_che_hanno_girato(store):
    stadi = _stadi(store, "servizio VPS")
    assert stadi is not None, (
        "dopo una recall non c'e' nessuna dichiarazione di come sia stata "
        "ordinata: il chiamante non puo' sapere quali segnali hanno deciso")
    assert "rerank" in stadi and "fusion" in stadi, stadi


def test_un_segnale_SPENTO_si_dichiara_invece_di_tacere(store, monkeypatch):
    """`ENGRAM_RECALL_RERANK=0` e' una scelta legittima dell'operatore. Il
    chiamante che riceve i risultati deve poterla vedere: un ordine prodotto
    senza cross-encoder non e' lo stesso oggetto di uno prodotto con."""
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "0")
    stadi = _stadi(store, "servizio VPS")
    assert stadi["rerank"] == "off", stadi
    assert stadi["fusion"] == "off", stadi


def test_una_query_LUNGA_non_viene_reranked_e_lo_dice(store, monkeypatch):
    """In AUTO (default dal 26/07) il CE gira solo sotto le 10 parole, perche'
    sulle query lunghe MISURA peggio (-0.080 MRR, 12 meglio / 38 peggio). La
    scelta e' giusta e resta; quello che manca e' dirlo. Deterministico: le
    parole si contano, non si cronometrano."""
    monkeypatch.delenv("ENGRAM_RECALL_RERANK", raising=False)  # AUTO
    lunga = ("quale servizio gira sul VPS di Amsterdam e come mai proprio "
             "quello e non un altro fra tutti")
    assert len(lunga.split()) > 10
    stadi = _stadi(store, lunga)
    assert stadi["rerank"] == "skipped_long_query", stadi

    corta = "servizio VPS"
    assert len(corta.split()) <= 10
    assert _stadi(store, corta)["rerank"] != "skipped_long_query"


def test_due_ordinamenti_diversi_non_si_dichiarano_uguali(store, monkeypatch):
    """Il cuore del difetto misurato: due risposte alla STESSA domanda,
    ottenute con segnali diversi, devono differire anche nella dichiarazione.
    Se i due dizionari fossero identici, il campo non presidierebbe nulla."""
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    senza = _stadi(store, "servizio VPS")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    con = _stadi(store, "servizio VPS")
    assert senza != con, (
        f"due recall ordinate diversamente si dichiarano identiche: {senza}")


def test_la_dichiarazione_ESCE_dalla_superficie_MCP(tmp_path, monkeypatch):
    """Il registro deve arrivare a CHI CHIAMA, non restare una variabile di
    modulo: e' sulla risposta MCP che il difetto e' stato misurato, ed e' li'
    che va verificato. Un registro corretto e non collegato sarebbe il
    trentanovesimo modulo irraggiungibile, non una cura."""
    import asyncio
    import json

    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from verimem import mcp_server

    # Seminato NELLA semantic dell'agente, non in un db costruito a mano: su
    # uno store vuoto la recall esce prima di ordinare qualunque cosa e il
    # registro resterebbe vuoto per assenza di lavoro — vero, ma non
    # proverebbe il collegamento. E l'agente MCP e' gia' costruito quando la
    # suite arriva qui, quindi la sua data dir e' la sola che conta.
    sm = mcp_server._ag().semantic
    for i in range(4):
        sm.store(Fact(proposition=f"Il servizio numero {i} gira su un VPS "
                                  f"di Amsterdam.", topic="prove/ranking"))
    out = asyncio.run(mcp_server._call_tool_impl(
        "hippo_facts_recall", {"query": "servizio VPS", "k": 3}))
    risposta = json.loads(out[0].text)
    assert "ranking" in risposta, (
        f"la risposta non dice come e' stata ordinata: {sorted(risposta)}")
    assert risposta["ranking"] is not None, risposta["ranking"]
    assert risposta["ranking"].get("rerank") == "off", risposta["ranking"]


def test_fuori_da_una_recall_non_si_inventa_nulla():
    """Chi non ha aperto una registrazione non deve ricevere un dizionario
    vuoto che sembra «nessun degrado»: assente e vuoto sono due cose diverse
    (la lezione di `judge_state` di stamattina)."""
    semantic._RANKING.set(None)
    assert semantic.ranking_stages() is None
    semantic._ranking_note("rerank", "applied")  # non deve esplodere
    assert semantic.ranking_stages() is None


def test_la_dichiarazione_non_perde_i_valori_gia_scritti(store):
    semantic.ranking_reset()
    semantic._ranking_note("dense", "ok")
    semantic._ranking_note("rerank", "applied")
    stadi = semantic.ranking_stages()
    assert stadi["dense"] == "ok" and stadi["rerank"] == "applied"
    # copia difensiva: chi legge non deve poter riscrivere lo stato interno
    stadi["rerank"] = "manomesso"
    assert semantic.ranking_stages()["rerank"] == "applied"
