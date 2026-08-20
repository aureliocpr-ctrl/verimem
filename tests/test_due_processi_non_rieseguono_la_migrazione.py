"""La versione dello schema e' letta FUORI dalla transazione.

`ensure_schema_version` legge `current` alla prima riga, calcola l'elenco delle
migrazioni da quel valore, e solo DOPO apre `BEGIN IMMEDIATE`. Fra le due cose
c'e' una finestra: un altro processo puo' migrare e committare, e chi era gia'
entrato riesegue una migrazione gia' applicata.

In CI questo si vede come:

    File "verimem/memory.py", line 209, in _migration_v2_salience_columns
        conn.execute(ddl)
    sqlite3.OperationalError: duplicate column name: last_accessed_at

Il DDL delle migrazioni e' `ALTER TABLE ... ADD COLUMN` nudo, che non e'
idempotente: rieseguirlo NON e' innocuo, esplode. La protezione quindi non puo'
stare nel DDL, deve stare nella rilettura della versione dentro la transazione.

I test qui sotto misurano quella proprieta' e basta: che la versione sia riletta
DOPO aver preso il lock. Il primo e' quello che cade oggi; gli altri due sono i
controlli che possono fallire se la cura, invece di chiudere la finestra,
spegnesse le migrazioni.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem import migrations as M


def _conn(tmp_path, nome="db.sqlite"):
    return sqlite3.connect(str(tmp_path / nome))


def _colonne(conn, tabella="t"):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({tabella})")}


def _base(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY)")


def _aggiunge_colonna(conn):
    """Come le migrazioni vere: ALTER TABLE nudo, non idempotente."""
    conn.execute("ALTER TABLE t ADD COLUMN salience REAL DEFAULT 0.0")


LADDER = [(1, lambda c: None), (2, _aggiunge_colonna)]


def test_il_ddl_di_una_migrazione_non_e_idempotente(tmp_path):
    """Il presupposto: rieseguire una migrazione NON e' innocuo.

    Se un giorno tutte le migrazioni diventassero idempotenti questo test
    diventerebbe rosso, e vorrebbe dire che la finestra non fa piu' danno.
    """
    conn = _conn(tmp_path)
    _base(conn)
    _aggiunge_colonna(conn)
    with pytest.raises(sqlite3.OperationalError, match="duplicate column"):
        _aggiunge_colonna(conn)
    conn.close()


def test_la_versione_e_riletta_dentro_la_transazione(tmp_path, monkeypatch):
    """Un altro processo migra nella finestra fra la lettura e il BEGIN.

    Riproduco la finestra al punto esatto: la PRIMA lettura (quella fuori
    transazione) restituisce il valore stantio, tutte le successive leggono il
    db per davvero. Se la funzione rilegge dopo aver preso il lock, vede 2 e si
    ferma. Se si fida della lettura di prima, riesegue e sqlite esplode.
    """
    db = tmp_path / "corsa.sqlite"
    a = sqlite3.connect(str(db))
    b = sqlite3.connect(str(db))
    _base(a)
    M.ensure_schema_version(a, db_id="t", target_version=1, migrations=LADDER[:1])

    vero = M._read_version
    chiamate = {"n": 0}

    def _stantio(conn, db_id):
        chiamate["n"] += 1
        if chiamate["n"] == 1:
            v = vero(conn, db_id)
            # nella finestra: l'altro processo migra e committa
            M.ensure_schema_version(a, db_id="t", target_version=2,
                                    migrations=LADDER)
            return v
        return vero(conn, db_id)

    monkeypatch.setattr(M, "_read_version", _stantio)
    M.ensure_schema_version(b, db_id="t", target_version=2, migrations=LADDER)

    assert "salience" in _colonne(b)
    assert vero(b, "t") == 2
    a.close()
    b.close()


def test_senza_concorrenza_la_migrazione_gira_lo_stesso(tmp_path):
    """Controllo che puo' fallire: la cura non deve spegnere le migrazioni.

    Se chiudessi la finestra facendo uscire la funzione troppo presto, qui la
    colonna non comparirebbe e il test cadrebbe.
    """
    conn = _conn(tmp_path, "solo.sqlite")
    _base(conn)
    finale = M.ensure_schema_version(conn, db_id="t", target_version=2,
                                     migrations=LADDER)
    assert finale == 2
    assert "salience" in _colonne(conn)
    conn.close()


def test_richiamarla_due_volte_resta_un_no_op(tmp_path):
    """L'idempotenza promessa dal docstring, misurata."""
    conn = _conn(tmp_path, "due.sqlite")
    _base(conn)
    M.ensure_schema_version(conn, db_id="t", target_version=2, migrations=LADDER)
    assert M.ensure_schema_version(conn, db_id="t", target_version=2,
                                   migrations=LADDER) == 2
    conn.close()
