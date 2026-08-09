"""Il registro dei ritiri regge la scala — e l'ordine non cambia.

Misurato il 2026-08-05 su 200.000 righe sintetiche: la query ordinava su
``COALESCE(superseded_at, 0)``, e un'ESPRESSIONE non può usare un indice —
quindi SQLite scansionava tutta la tabella e ordinava in memoria per
restituire 50 righe:

    con COALESCE, senza indice : 63.6 ms   SCAN + TEMP B-TREE
    senza COALESCE, senza idx  : 55.4 ms   SCAN + TEMP B-TREE
    senza COALESCE, CON indice :  0.1 ms   SCAN facts USING INDEX

600 volte. E il ``COALESCE`` proteggeva da un caso che non esiste: sul
corpus reale i ritiri senza ``superseded_at`` sono **0 su 1794**. Anche se
esistessero, l'ordine non cambierebbe — in SQLite NULL è minore di tutto,
quindi in DESC finisce in fondo esattamente dove lo metteva lo zero.

Questi test pinnano le due cose insieme: l'ordine (compresi i NULL) e il
fatto che il piano usi l'indice invece del temp B-tree. Un test di ordine
senza il piano lascerebbe rientrare la lentezza al primo refactor.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.client import Memory
from verimem.retirement_log import retirement_log


@pytest.fixture()
def con_ritiri(tmp_path):
    m = Memory(tmp_path / "memory.db")
    ids = []
    for i, t in enumerate([
        "Il magazzino K-77 ha 4200 metri quadri.",
        "Il magazzino Z-08 ha 2600 metri quadri.",
        "Il magazzino R-31 ha 900 metri quadri.",
        "Il deposito centrale ha 12000 metri quadri.",
    ]):
        ids.append(m.add(t, topic=f"wh/{i}", verified_by=["doc"])["id"])
    # due ritiri in tempi diversi: il secondo deve uscire per primo
    m.semantic.supersede(ids[0], ids[1], principal="t", reason="primo")
    m.semantic.supersede(ids[2], ids[3], principal="t", reason="secondo")
    return m


def test_il_piu_recente_esce_per_primo(con_ritiri):
    righe = retirement_log(con_ritiri.semantic, limit=10)
    assert [r["reason"] for r in righe] == ["secondo", "primo"], righe


def test_un_ritiro_senza_data_finisce_in_fondo(con_ritiri):
    """Il caso che il COALESCE difendeva: zero occorrenze sul corpus reale,
    ma se capitasse l'ordine non deve cambiare — NULL in DESC va in fondo,
    dove lo metteva lo zero."""
    m = con_ritiri
    with sqlite3.connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET superseded_at = NULL "
                    "WHERE superseded_reason = 'primo'")
    righe = retirement_log(m.semantic, limit=10)
    assert [r["reason"] for r in righe] == ["secondo", "primo"], righe
    assert righe[-1]["superseded_at"] is None


def test_l_indice_arriva_anche_su_uno_store_GIA_migrato(tmp_path):
    """Il caso che conta, e che il test sullo store nuovo NON copre.

    L'indice era stato messo dentro una vecchia migrazione: i database nuovi
    lo avevano, quello di produzione no — la via veloce esisteva ovunque
    tranne dove stavano i dati (misurato su copia del corpus reale). La
    guardia meccanica dopo la scala lo crea a ogni apertura.
    """
    db = tmp_path / "gia_migrato.db"
    m = Memory(db)
    m.add("un fatto qualunque", topic="t", verified_by=["doc"])
    del m
    with sqlite3.connect(db) as con:      # simula lo store già passato oltre
        con.execute("DROP INDEX IF EXISTS idx_facts_superseded_at")
    with sqlite3.connect(db) as con:
        assert "idx_facts_superseded_at" not in {
            r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='index'")}

    Memory(db)                            # riapertura: deve auto-ripararsi
    with sqlite3.connect(db) as con:
        assert "idx_facts_superseded_at" in {
            r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='index'")}


def test_il_piano_usa_l_indice_e_non_il_temp_btree(con_ritiri):
    """La proprietà che rende la coda praticabile su un corpus grande:
    senza questa asserzione un refactor può reintrodurre 600x di lentezza
    senza rompere nessun altro test."""
    m = con_ritiri
    q = ("SELECT f.id FROM facts f WHERE f.superseded_by IS NOT NULL "
         "ORDER BY f.superseded_at DESC LIMIT 50")
    with sqlite3.connect(m.semantic.db_path) as con:
        piano = " ".join(str(r[-1]) for r in
                         con.execute("EXPLAIN QUERY PLAN " + q))
    assert "idx_facts_superseded_at" in piano, piano
    assert "TEMP B-TREE" not in piano.upper(), piano
