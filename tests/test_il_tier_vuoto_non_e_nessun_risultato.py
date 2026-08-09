"""«Non ho trovato niente» e «non c'è niente da cercare» sono due risposte.

ws2«Vega», sonda del 2026-08-07 su store isolato, zero ingestione:

    TranscriptIndex().count()  ->  0
    recall('qual è il piano per il rilascio?')  ->  []  in 0.03s

Nessun campo distingue «tier vuoto» da «nessun match». E il tier C non si
riempie da solo: l'ingester è delegato a un hook che il prodotto **non
installa**, quindi un utente di fabbrica ha `hippo_transcript_recall` nel
listino, riceve `[]` per sempre, e quel `[]` è identico a «ho cercato e
non c'era».

È la quinta istanza della stessa forma — non-trovato contro
trovato-ma-nascosto — dopo i documenti nascosti e la quarantena
invisibile: **il prodotto sa una cosa (`count()==0`) e non la dice dove
serve.**

La cura è un CAMPO, non un filtro: `n_indexed_turns` e `tier_empty`
viaggiano col risultato. Additiva nel contenuto; cambia però la FORMA
della risposta MCP da lista nuda a oggetto, e questo va dichiarato — in
repo nessuno dipendeva dalla lista (verificato: una sola menzione, in un
docstring).
"""
from __future__ import annotations

import pytest

from verimem.transcript_index import TranscriptIndex, Turn


@pytest.fixture()
def indice(tmp_path):
    # `TranscriptIndex(db_path=...)` e' la via che il prodotto offre: niente
    # monkeypatch su un risolutore privato che non esiste (la mia prima
    # stesura ne inventava uno — terza volta oggi che scrivo il banco
    # contro l'API che immagino invece di quella che c'e').
    return TranscriptIndex(db_path=tmp_path / "transcript.db")


def test_un_tier_mai_popolato_lo_DICHIARA(indice):
    """Il caso dell'utente di fabbrica: il tool esiste, il tier è vuoto per
    sempre, e la risposta non lo diceva."""
    out = indice.recall_report("qual è il piano per il rilascio?")

    assert out["turns"] == []
    assert out["tier_empty"] is True, out
    assert out["n_indexed_turns"] == 0


def test_un_tier_PIENO_senza_match_non_si_dichiara_vuoto(indice):
    """L'altra popolazione, che è quella che rende la dichiarazione utile:
    qui `[]` significa davvero «ho cercato e non c'era»."""
    indice.store(Turn(text="the depot holds 10 crates", session_id="s1",
                      role="user", ts=1.0))
    out = indice.recall_report("qualcosa di completamente diverso")

    assert out["tier_empty"] is False, out
    assert out["n_indexed_turns"] == 1


def test_il_conteggio_e_quello_della_SESSIONE_quando_si_filtra(indice):
    """Chiedere di una sessione che non esiste non è «il tier è vuoto»:
    sono due assenze diverse, e confonderle rifà il difetto un piano più
    in basso."""
    indice.store(Turn(text="the depot holds 10 crates", session_id="s1",
                      role="user", ts=1.0))
    out = indice.recall_report("piano", session_id="s2")

    assert out["turns"] == []
    assert out["n_indexed_turns"] == 0
    assert out["tier_empty"] is False, "il TIER non è vuoto: lo è la sessione"
    assert out["scope"] == "session:s2", out


def test_la_lista_resta_disponibile_per_chi_la_usava(indice):
    """`recall()` non cambia: chi vuole solo le righe continua a chiamarla.
    La dichiarazione è un metodo IN PIÙ, non una rottura del vecchio."""
    indice.store(Turn(text="the depot holds 10 crates", session_id="s1",
                      role="user", ts=1.0))
    righe = indice.recall("depot")
    assert isinstance(righe, list)


def test_dichiara_anche_PERCHE_il_tier_puo_essere_vuoto(indice):
    """Un `tier_empty: true` senza spiegazione manda a cercare un guasto:
    qui non c'è nessun guasto, c'è un ingester che il prodotto non
    installa — e chi legge deve saperlo per non perdere un'ora."""
    nota = indice.recall_report("x")["tier_empty_means"]
    assert "ingest" in nota.lower(), nota
