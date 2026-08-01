"""Un documento indicizzato dalla porta normale non sa quando è arrivato.

`DocumentStore.ingest` e `ingest_file` dichiarano ``fetched_at: float = 0.0``
e NESSUNO lo calcola: tocca al chiamante passarlo, e in tutto il repo lo passa
un solo script (`scripts/ingest_md.py:39`, `fetched_at=now`). La CLI e il tool
MCP non lo passano, quindi i documenti che un utente indicizza restano a zero.

Misurato sullo store di Aurelio il 2026-08-01:

    documenti: 42 · con fetched_at = 0: 12
    di quelli, quanti hanno meta.indexed_at valorizzato: 0
      contract.txt            fetched_at=0.0  indexed_at=None
      docs\\ROADMAP-v0.7.md    fetched_at=0.0  indexed_at=None

Nessun altro campo recupera il dato: `meta.indexed_at` viene scritto solo
quando l'ingest riceve un `principal`, e su quei dodici non c'era.

E LA LISTA ORDINA PROPRIO PER QUEL CAMPO — ``ORDER BY d.fetched_at DESC,
d.source_id ASC`` (documents.py:224). Zero non e' un'assenza: e' il 1° gennaio
1970, cioe' una data FALSA, e mette in fondo alla lista, in ordine alfabetico,
esattamente i documenti che l'utente ha appena indicizzato. Chi ne indicizza
uno oggi lo cerca in cima e lo trova sotto quelli di maggio.

Il momento in cui un contenuto viene acquisito NON e' un'informazione che il
chiamante debba possedere: e' adesso, per costruzione. Il default lo dice; chi
sta ricostruendo un archivio con date vere continua a passarle esplicitamente.
"""
from __future__ import annotations

import time

import pytest

from verimem.documents import DocumentStore


@pytest.fixture()
def store(tmp_path):
    return DocumentStore(tmp_path / "documents.db")


def test_un_ingest_senza_data_si_timbra_da_solo(store):
    prima = time.time()
    store.ingest("nota.md", "Il contenuto della nota.")
    doc = store.get_latest("nota.md")
    assert doc is not None
    assert doc.fetched_at >= prima, (
        f"fetched_at={doc.fetched_at} — zero e' il 1970, non un'assenza, e "
        f"la lista ordina per questo campo")


def test_anche_un_file_si_timbra_da_solo(store, tmp_path):
    p = tmp_path / "roadmap.md"
    p.write_text("# Roadmap\nprima riga.", encoding="utf-8")
    prima = time.time()
    store.ingest_file(p)
    doc = store.get_latest(str(p))
    assert doc is not None and doc.fetched_at >= prima, doc.fetched_at


def test_una_data_esplicita_resta_quella_che_e(store):
    """Chi ricostruisce un archivio passa le date vere e non deve trovarsele
    riscritte a oggi: il default riempie un vuoto, non sovrascrive."""
    quando = 1_500_000_000.0
    store.ingest("vecchio.md", "Un documento del 2017.", fetched_at=quando)
    assert store.get_latest("vecchio.md").fetched_at == quando


def test_la_lista_mette_davvero_il_piu_recente_in_cima(store):
    """Il difetto visto dall'utente: l'ordinamento e' su questo campo."""
    store.ingest("antico.md", "Il primo.", fetched_at=1_500_000_000.0)
    store.ingest("appena.md", "Il secondo, indicizzato adesso.")
    elenco = store.list_sources(limit=10)
    assert elenco, elenco
    assert elenco[0]["source_id"] == "appena.md", (
        f"il piu' recente non e' in cima: {[d['source_id'] for d in elenco]}")
