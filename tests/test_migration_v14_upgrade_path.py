"""L'UPGRADE di uno store esistente non deve rompere la memoria.

Bug P0 trovato sullo store reale di Aurelio (2026-07-15) — 6120 fatti,
ogni write in errore:

    sqlite3.OperationalError: table facts has no column named epistemic

Root cause: la v14 (colonna ``epistemic``) è stata aggiunta allo _SCHEMA
(quindi ogni DB NUOVO ce l'ha) e la migrazione ``_migrate_v13_to_v14`` è
stata scritta e registrata — ma ``_SEMANTIC_TARGET_VERSION`` è rimasto 13,
quindi il runner non l'ha MAI eseguita. I 6905 test non l'hanno visto
perché creano ogni store da zero: nessuno percorreva l'upgrade path.

Questa suite testa quello che i test verdi non testavano: un DB alla
versione precedente che viene aperto dal codice nuovo.
"""
from __future__ import annotations

import re
import sqlite3

import pytest

from verimem.semantic import (
    _SCHEMA,
    _SEMANTIC_TARGET_VERSION,
    Fact,
    SemanticMemory,
)
from verimem.store_migrate import migra_lo_store


def _make_v13_db(path):
    """Uno store REALISTICO alla v13: lo schema ODIERNO meno la colonna v14,
    versione dichiarata 13 — lo stato esatto dello store di Aurelio.

    Costruito dallo _SCHEMA vero (non da una copia a mano che invecchia) e
    non via ``ALTER TABLE ... DROP COLUMN``: SQLite rifiuta il drop quando la
    definizione porta commenti ("error in table facts after drop column:
    incomplete input") — ed è pieno di commenti.
    """
    schema13 = re.sub(r",\s*\n\s*--\s*v14 \(2026-07-13\).*?epistemic TEXT",
                      "", _SCHEMA, flags=re.S)
    assert "epistemic" not in schema13, "il fixture deve partire DAVVERO da v13"
    conn = sqlite3.connect(path)
    conn.executescript(schema13)
    # la tabella di versioning VERA (dal modulo migrations, non una copia
    # a mano: aveva già una colonna sbagliata)
    from verimem.migrations import _VERSION_TABLE_DDL
    conn.executescript(_VERSION_TABLE_DDL)
    conn.execute("INSERT OR REPLACE INTO _schema_version "
                 "(db_id, version, upgraded_at) VALUES ('semantic', 13, ?)",
                 ("2026-07-05 18:01:51",))
    # seed reale: riempi OGNI colonna NOT NULL senza default, letta dallo
    # schema stesso (indovinarle a mano invecchia al primo ALTER)
    row = {"id": "seed01", "proposition": "the office is in Milan",
           "topic": "hq", "created_at": 1.0}
    for r in conn.execute("PRAGMA table_info(facts)"):
        name, typ, notnull, dflt = r[1], (r[2] or "").upper(), r[3], r[4]
        if not notnull or dflt is not None or name in row:
            continue
        row[name] = 0.0 if ("REAL" in typ or "INT" in typ) else ""
    cols = ", ".join(row)
    conn.execute(f"INSERT INTO facts ({cols}) VALUES "
                 f"({', '.join('?' for _ in row)})", tuple(row.values()))
    conn.commit()
    conn.close()


def test_target_version_covers_every_registered_migration():
    """Il guard che avrebbe evitato il bug: se registri la migrazione N,
    il target DEVE arrivare a N — altrimenti non gira mai."""
    assert _SEMANTIC_TARGET_VERSION >= 14


def test_un_v13_non_si_migra_piu_aprendolo(tmp_path):
    """D-0012: il percorso di aggiornamento passa da un comando, non dall'apertura.

    ⚠️ È il contratto CAMBIATO, e va letto insieme al bug che apre questo file.
    Prima, aprire uno store v13 lo riparava: comodo, e per questo pericoloso —
    lo stesso meccanismo aggiornava in silenzio un backup aperto per leggerlo,
    che così smetteva di essere un backup (misurato su copie: v7 → v17, +21
    colonne, senza avviso e senza ritorno).

    La riparazione non è sparita, si è spostata dove si vede: `verimem store
    migrate`, dopo un backup verificato contando le righe. Tutto ciò che questo
    file proteggeva — la colonna arriva, i fatti sopravvivono, scrivere
    funziona — è tenuto fermo dalle celle qui sotto, che ora passano di lì.
    """
    from verimem.schema import StoreDaMigrare

    db = tmp_path / "old.db"
    _make_v13_db(db)
    prima = db.read_bytes()

    with pytest.raises(StoreDaMigrare):
        SemanticMemory(db_path=db)

    assert db.read_bytes() == prima, (
        "il rifiuto è arrivato dopo aver toccato il file")


def test_v13_store_gets_the_epistemic_column_on_migrate(tmp_path):
    db = tmp_path / "old.db"
    _make_v13_db(db)
    cols = [r[1] for r in sqlite3.connect(db).execute(
        "PRAGMA table_info(facts)")]
    assert "epistemic" not in cols, "il fixture deve partire DAVVERO da v13"

    ricevuta = migra_lo_store(db)       # migrare = chiederlo

    cols = [r[1] for r in sqlite3.connect(db).execute(
        "PRAGMA table_info(facts)")]
    assert "epistemic" in cols
    ver = sqlite3.connect(db).execute(
        "SELECT version FROM _schema_version WHERE db_id='semantic'"
    ).fetchone()[0]
    assert ver >= 14
    assert "epistemic" in ricevuta.colonne_aggiunte.get("facts", ()), (
        f"la ricevuta non dice di averla aggiunta: {ricevuta}")


def test_write_works_after_upgrade(tmp_path):
    """Il sintomo esatto di Aurelio: scrivere su uno store aggiornato."""
    db = tmp_path / "old.db"
    _make_v13_db(db)
    migra_lo_store(db)
    mem = SemanticMemory(db_path=db)
    fact = Fact(proposition="Zephyrus signed with Kraken", topic="news")
    mem.store(fact, embed="sync")       # store() → None by design; id sul Fact
    got = mem.get(fact.id)
    assert got is not None and got.proposition == "Zephyrus signed with Kraken"


def test_existing_facts_survive_the_upgrade(tmp_path):
    """Migrare non perde memoria. E ora il backup lo dimostra contando."""
    db = tmp_path / "old.db"
    _make_v13_db(db)
    ricevuta = migra_lo_store(db)
    mem = SemanticMemory(db_path=db)
    props = [f.proposition for f in mem.all()]
    assert "the office is in Milan" in props
    assert ricevuta.righe_verificate >= 1, (
        "il backup dichiara zero righe verificate: non ha contato niente")


def test_upgrade_is_idempotent(tmp_path):
    """Migrare due volte non esplode (la migrazione non ri-gira)."""
    db = tmp_path / "old.db"
    _make_v13_db(db)
    migra_lo_store(db)
    seconda = migra_lo_store(db)
    cols = [r[1] for r in sqlite3.connect(db).execute(
        "PRAGMA table_info(facts)")]
    assert cols.count("epistemic") == 1
    assert not seconda.colonne_aggiunte, (
        f"la seconda migrazione dice di aver aggiunto qualcosa: {seconda}")
