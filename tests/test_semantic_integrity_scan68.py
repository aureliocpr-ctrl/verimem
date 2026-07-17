"""TDD — 3 bug di INTEGRITA MEMORIA in engram/semantic.py trovati dallo scan 68-Opus (2026-06-02),
verificati a mano da NONNA leggendo il codice. Tutti i test sono HERMETIC (temp DB), zero
side-effect sul DB reale ~/.verimem.

BUG #1 (semantic.py:695-711) store() usa INSERT OR REPLACE con 16 colonne -> azzera
    superseded_by/at/reason (non listate) su re-store dello stesso id -> fatti soppressi resuscitano.
BUG #2 (semantic.py:1733) clear() fa solo DELETE, non bumpa _cache_version -> recall(topic=None)
    serve fatti fantasma dalla cache stantia.
BUG #3 (semantic.py:1779) _row() non rilegge writer_role/meta_narrative -> il Fact ricaricato
    perde la provenance v6 (il gate anti-confab che legge fact.writer_role vede il default).
"""
from __future__ import annotations

import sqlite3

from verimem.semantic import Fact, SemanticMemory


def test_store_does_not_wipe_supersession(tmp_path):
    db = tmp_path / "s.db"
    m = SemanticMemory(db_path=db)
    m.store(Fact(id="x1", proposition="proposition uno lunga abbastanza per embedding", topic="t/a", confidence=0.5))
    # simula una supersession precedente (impostata da supersede(), via UPDATE)
    con = sqlite3.connect(db)
    con.execute("UPDATE facts SET superseded_by='x2', superseded_reason='dup' WHERE id='x1'")
    con.commit()
    con.close()
    # re-store stesso id (es. re-embedding / update contenuto): il fact NON porta supersession
    m.store(Fact(id="x1", proposition="proposition uno EDITATA lunga abbastanza", topic="t/a", confidence=0.6))
    con = sqlite3.connect(db)
    row = con.execute("SELECT superseded_by, superseded_reason FROM facts WHERE id='x1'").fetchone()
    con.close()
    assert row == ("x2", "dup"), f"supersession AZZERATA dal re-store: {row}"


def test_clear_invalidates_recall_cache(tmp_path):
    m = SemanticMemory(db_path=tmp_path / "s.db")
    m.store(Fact(id="c1", proposition="alpha beta gamma delta memoria semantica", topic="t/c", confidence=0.5))
    v0 = m._cache_version
    m.clear()
    assert m._cache_version > v0, "clear() non bumpa _cache_version -> recall servirebbe fatti fantasma dalla cache"


def test_row_roundtrips_provenance_v6(tmp_path):
    db = tmp_path / "s.db"
    m = SemanticMemory(db_path=db)
    m.store(Fact(id="p1", proposition="provenance roundtrip fact abbastanza lunga", topic="t/p",
                 confidence=0.5, writer_role="system_hook", meta_narrative=True))
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM facts WHERE id='p1'").fetchone()
    con.close()
    got = SemanticMemory._row(row)
    assert got.writer_role == "system_hook", f"writer_role perso nel roundtrip: {got.writer_role}"
    assert got.meta_narrative is True, f"meta_narrative perso nel roundtrip: {got.meta_narrative}"
