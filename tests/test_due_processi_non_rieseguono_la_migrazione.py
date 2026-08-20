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


def test_una_migrazione_parziale_dell_altro_non_blocca_il_resto(tmp_path,
                                                                monkeypatch):
    """L'altro processo si ferma a META' scaletta: il resto va applicato lo stesso.

    Copre il ramo che il test sopra NON tocca. Li' l'altro arriva al mio stesso
    target e la funzione esce subito; qui arriva a v2 mentre io punto a v3, e la
    cura deve saltare SOLO la v2 e applicare la v3. Se saltasse tutto avrei
    chiuso la finestra rompendo la scaletta, che e' il modo peggiore di ottenere
    un verde.

    Il banco tiene traccia di CHI esegue ogni migrazione: la prima versione
    contava le esecuzioni in una lista sola e attribuiva a B anche quelle di A,
    dando un `CADE` che era del misuratore e non della cura.
    """
    eseguite: list[tuple[str, int]] = []
    nome: dict[int, str] = {}

    def _passo(v):
        def _fn(conn):
            eseguite.append((nome.get(id(conn), "?"), v))
            if v > 1:
                conn.execute(f"ALTER TABLE t ADD COLUMN c{v} REAL")
        return _fn

    ladder = [(1, _passo(1)), (2, _passo(2)), (3, _passo(3))]

    db = tmp_path / "parziale.sqlite"
    a = sqlite3.connect(str(db))
    b = sqlite3.connect(str(db))
    nome[id(a)] = "A"
    nome[id(b)] = "B"
    _base(a)
    M.ensure_schema_version(a, db_id="t", target_version=1, migrations=ladder[:1])

    vero = M._read_version
    aperta = {"gia": False}

    def _finestra(conn, db_id):
        if id(conn) == id(b) and not aperta["gia"]:
            aperta["gia"] = True
            v = vero(conn, db_id)
            # il patch e' globale: va spento mentre migra A, o A ci ricade dentro
            monkeypatch.setattr(M, "_read_version", vero)
            M.ensure_schema_version(a, db_id="t", target_version=2,
                                    migrations=ladder[:2])
            monkeypatch.setattr(M, "_read_version", _finestra)
            return v
        return vero(conn, db_id)

    monkeypatch.setattr(M, "_read_version", _finestra)
    eseguite.clear()
    finale = M.ensure_schema_version(b, db_id="t", target_version=3,
                                     migrations=ladder)

    assert [v for chi, v in eseguite if chi == "B"] == [3]
    assert ("A", 2) in eseguite
    assert finale == 3
    assert {"c2", "c3"} <= _colonne(b)
    a.close()
    b.close()
