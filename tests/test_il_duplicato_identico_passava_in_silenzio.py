"""Scrivo tre volte lo stesso fatto, e il prodotto non me lo dice mai.

MISURATO DA UTENTE, tre `add` dello stesso identico testo::

    nel DB: 3 righe · 3 servibili
    recall -> la stessa frase 3 volte
    il prodotto dichiara che è un duplicato?  NO, mai

ws4 aveva misurato l'effetto sul corpus (4 gruppi di duplicati, 7 copie in
eccesso su 5311, e `slot=35 sprecati_da_duplicati=7` in un recall reale). Il
pezzo che mancava è **dal lato di chi scrive**: un utente che ri-salva per
distrazione dovrebbe saperlo alla seconda, non scoprirlo dopo con una ricerca
che rende tre copie identiche.

⚠️ IL MECCANISMO C'ERA GIÀ: `find_duplicate_facts` è esposto come
`hippo_find_duplicate_facts`. Ma è BATCH e fa Jaccard — si usa DOPO, per
ripulire. Al momento della scrittura non lo chiama nessuno.

⚠️ E IL COSTO DECIDE LA FORMA. Il controllo esatto è una scansione, misurata::

    corpus reale (7950 righe)       0.08 ms
    sintetico  50 000 righe         9.89 ms
    sintetico 200 000 righe        21.36 ms      <- per OGNI scrittura
    con un indice su proposition    0.127 ms     (schema: non è mio)

A 200k costerebbe 21 ms a scrittura. Ma saltarlo in silenzio sui corpus grandi
sarebbe **esattamente la classe che questo prodotto passa la giornata a
curare**: una garanzia che sparisce senza dirlo. Quindi il controllo si fa
finché è economico, e quando NON si fa **si dichiara** (`layer:
duplicate_check_skipped`).

📌 Chi volesse il controllo sempre attivo ha la strada: un indice su
`proposition` lo rende O(1) — 286 ms per costruirlo su 200k righe.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory, soglia_controllo_duplicati

FATTO = "Il magazzino K-77 di Rovigo ha 4200 metri quadrati."


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


def _avvisi(ricevuta, layer):
    return [w for w in (ricevuta.get("warnings") or [])
            if str(w.get("layer", "")) == layer]


def test_la_seconda_scrittura_identica_lo_dice(mem):
    """IL CUORE: alla seconda, non dopo con una ricerca che rende due copie."""
    mem.add(FATTO, topic="az/mag")
    ric = mem.add(FATTO, topic="az/mag")
    avvisi = _avvisi(ric, "duplicate")
    assert avvisi, f"nessun avviso di duplicato: {ric.get('warnings')}"
    assert "identic" in str(avvisi[0]).lower()


def test_il_duplicato_ENTRA_lo_stesso(mem):
    """IL PRESIDIO CHE VALE PIÙ DI TUTTI: l'avviso AVVISA, non blocca.

    Ri-scrivere un fatto è legittimo — può essere una conferma, o due fonti che
    concordano. Se questo cade, abbiamo trasformato un avviso in un divieto, ed
    è il modo in cui una cura buona diventa un danno."""
    mem.add(FATTO, topic="az/mag")
    ric = mem.add(FATTO, topic="az/mag")
    assert ric.get("stored") is True
    assert ric.get("status") != "quarantined", ric.get("status")


def test_un_fatto_nuovo_non_porta_avvisi(mem):
    """L'ALTRO PRESIDIO: sulla scrittura ordinaria non compare nulla."""
    mem.add(FATTO, topic="az/mag")
    ric = mem.add("Il magazzino Z-08 di Ancona ha 2600 metri quadrati.",
                  topic="az/mag")
    assert not _avvisi(ric, "duplicate")


def test_lo_stesso_testo_in_un_altro_topic_non_e_un_duplicato(mem):
    """Due topic diversi sono due contesti diversi: la stessa frase archiviata
    sotto «magazzini» e sotto «verbale-riunione» non è una svista."""
    mem.add(FATTO, topic="az/mag")
    ric = mem.add(FATTO, topic="az/verbali")
    assert not _avvisi(ric, "duplicate")


def test_quando_il_controllo_NON_si_fa_lo_dichiara(mem, monkeypatch):
    """⚠️ IL PEZZO CHE RENDE LA CURA ONESTA. Sopra la soglia il controllo
    costa troppo per pagarlo a ogni scrittura — e una garanzia che sparisce in
    silenzio è il difetto che stiamo curando da due giorni. Quindi si dichiara
    che non è stato fatto."""
    monkeypatch.setenv("ENGRAM_DUP_CHECK_MAX_FACTS", "1")
    mem.add(FATTO, topic="az/mag")
    ric = mem.add(FATTO, topic="az/mag")
    assert not _avvisi(ric, "duplicate")
    saltato = _avvisi(ric, "duplicate_check_skipped")
    assert saltato, f"il controllo salta e non lo dice: {ric.get('warnings')}"
    assert "indic" in str(saltato[0]).lower(), "deve dire come riattivarlo"


def test_zero_disattiva_del_tutto_e_in_silenzio(mem, monkeypatch):
    """Chi lo spegne di proposito non vuole nemmeno l'avviso del salto: `0` è
    una scelta esplicita, non un limite incontrato."""
    monkeypatch.setenv("ENGRAM_DUP_CHECK_MAX_FACTS", "0")
    mem.add(FATTO, topic="az/mag")
    ric = mem.add(FATTO, topic="az/mag")
    assert not _avvisi(ric, "duplicate")
    assert not _avvisi(ric, "duplicate_check_skipped")


def test_la_soglia_si_legge_da_UNA_funzione(monkeypatch):
    monkeypatch.setenv("ENGRAM_DUP_CHECK_MAX_FACTS", "1234")
    assert soglia_controllo_duplicati() == 1234
    monkeypatch.setenv("ENGRAM_DUP_CHECK_MAX_FACTS", "non-un-numero")
    assert soglia_controllo_duplicati() == 50_000
