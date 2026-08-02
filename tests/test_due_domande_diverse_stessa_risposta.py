"""Il fallback OR matcha gli ARTICOLI, e due domande diverse tornano uguali.

`search_facts` prova prima l'AND su tutti i token; se non trova nulla ricade
sull'OR di qualsiasi token — con l'intenzione, scritta nel commento del
chiamante, di dare «relevant hits instead of []». Ma i token includono gli
articoli, quindi «relevant» diventa «tutto ciò che contiene *il*».

Misurato sul corpus VERO, 7079 fatti, limit 20::

    'quale database usa il cluster di produzione a Singapore' -> 20 hit
    'qual e il numero di targa della mia automobile'          -> 20 hit
       ...e i primi TRE risultati sono gli stessi identici delle due query,
       che non hanno in comune nient'altro che le parole funzionali.
    'which airline did the ambassador of Peru fly with'       -> 20 hit

Un database a Singapore e la targa di un'automobile ricevono la stessa
risposta: l'ordine non dipende dalla domanda, perché a matchare sono le parole
che stanno in ogni frase. Su tre fatti in inglese si vede in purezza — tutti
cominciano con «The», quindi qualunque domanda inglese rende il corpus intero.

LA CURA C'ERA GIÀ. `bm25_rank._tokens` toglie le funzionali en+it prima di
costruire la OR, e il suo commento descrive esattamente questo danno:
«l'OR-di-tutti-i-token lo faceva comunque matchare, riempiendo il ranklist di
rumore». Misurata il 2026-07-07. Ma vive nel percorso BM25/FTS, e questa è una
SQL LIKE che non ci passa: la cura era al SITO e non alla CLASSE — la terza
volta oggi.

LIMITE DICHIARATO: `_QUERY_STOPWORDS` è en+it. Una domanda in tedesco o in
spagnolo resta scoperta, ed è la classe «liste monolingue in un prodotto
mondiale» già pagata sulle lingue il 02/08. Il criterio senza lista esiste —
la document frequency, che non dipende dalla lingua — ma vive su `facts_fts`
con MATCH indicizzato, e questa superficie fa LIKE: portarcelo è una misura da
fare, non un'assunzione da scrivere qui.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory

IT = ["Il piano annuale costa 100 euro.",
      "La prova gratuita dura 14 giorni.",
      "Il supporto risponde in 24 ore."]
EN = ["The annual plan costs 100 euros.",
      "The free trial lasts 14 days.",
      "The support answers within 24 hours."]


def _store(frasi):
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    for t in frasi:
        m.add(t, topic="listino")
    return m.semantic


def _cerca(sm, query, limit=20):
    hits = sm.search_facts(query, limit=limit, require_all_tokens=True)
    if not hits and len(query.split()) > 1:
        hits = sm.search_facts(query, limit=limit, tokenize=True)
    return hits


@pytest.fixture()
def it():
    return _store(IT)


@pytest.fixture()
def en():
    return _store(EN)


def test_un_articolo_condiviso_non_e_una_risposta(it):
    got = _cerca(it, "quale database usa il cluster di produzione")
    assert got == [], (
        "due fatti di listino serviti a una domanda su un database, perché "
        f"contengono «il»: {[f.proposition for f in got]}")


def test_in_inglese_rendeva_il_corpus_intero(en):
    got = _cerca(en, "which database does the cluster use")
    assert got == [], (
        "ogni frase comincia con «The», quindi qualunque domanda inglese "
        f"rendeva tutto: {[f.proposition for f in got]}")


def test_una_query_di_soli_articoli_non_rende_tutto(it):
    assert _cerca(it, "il la") == []


def test_due_domande_diverse_non_danno_LA_STESSA_risposta(it):
    """Il difetto nella sua forma più netta: sul corpus vero un database a
    Singapore e la targa di un'automobile avevano gli stessi primi tre."""
    a = [f.id for f in _cerca(it, "quale database usa il cluster")]
    b = [f.id for f in _cerca(it, "qual e il numero di targa della mia auto")]
    assert not (a and a == b), (
        "due domande senza nulla in comune se non le parole funzionali "
        "ricevono la stessa identica lista")


def test_ma_una_domanda_VERA_continua_a_rispondere(it):
    """La controprova che conta: il fallback OR esiste perché una query
    multi-parola non deve tornare vuota quando il corpus sa rispondere."""
    got = _cerca(it, "quanto costa il piano annuale")
    assert any("100 euro" in f.proposition for f in got), (
        f"la cura ha mangiato una risposta vera: {[f.proposition for f in got]}")


def test_e_una_parola_di_contenuto_sola_basta(it):
    assert any("prova gratuita" in f.proposition
               for f in _cerca(it, "quanto dura la prova"))


def test_il_ramo_AND_non_si_muove(it):
    """`require_all_tokens=True` è il percorso di precisione e non tocca le
    funzionali: chi cerca una frase esatta la trova ancora."""
    got = it.search_facts("il piano annuale", limit=20,
                          require_all_tokens=True)
    assert any("piano annuale" in f.proposition for f in got)


def test_il_criterio_e_QUELLO_di_bm25_non_una_copia(it):
    """Due copie divergono: questa superficie deve chiedere i token allo
    stesso posto da cui li chiede il percorso BM25."""
    from verimem.bm25_rank import _tokens
    assert _tokens("quale database usa il cluster di produzione") == [
        "database", "usa", "cluster", "produzione"]
