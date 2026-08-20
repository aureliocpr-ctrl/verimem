"""`ensure_schema_version` chiude la transazione che ha trovato aperta.

La funzione apre `BEGIN IMMEDIATE`; se il chiamante ne aveva gia' una in corso
il BEGIN fallisce, il ramo `except sqlite3.OperationalError` prosegue senza
transazione propria, e il `conn.commit()` finale committa TUTTO — comprese le
scritture che il chiamante non aveva ancora deciso di rendere definitive.

Misurato il 2026-08-20 sulla funzione com'era:

    il chiamante inserisce la riga 99 e NON committa
    ensure_schema_version(...)
    dopo, in_transaction = False
    il chiamante NON PUO' fare rollback: cannot rollback - no transaction is active
    la riga 99 e' nel db vista da un'altra connessione? SI

⚠️ IL PERIMETRO, dichiarato perche' non sembri piu' grave di quanto e': nessuno
dei quattro chiamanti del prodotto ci arriva oggi — `entity_kg.py:483`,
`memory.py:384`, `semantic.py:2649`, `skill.py:237` chiamano tutti senza una
transazione aperta, e l'unico `BEGIN IMMEDIATE` del gruppo sta a
`entity_kg.py:587`, in un'altra funzione e dopo. E' una trappola per il prossimo
che chiamera' la funzione dentro una transazione, non un danno in corso.

I casi gia' coperti stanno qui sotto insieme al nuovo: se cadono quelli, il rotto
non e' la funzione ma questo banco.
"""
from __future__ import annotations

import sqlite3

from verimem import migrations as M


def _v1(conn):
    pass


def _v2(conn):
    conn.execute("ALTER TABLE t ADD COLUMN salience REAL DEFAULT 0.0")


LADDER = [(1, _v1), (2, _v2)]


def _conn(tmp_path, nome):
    c = sqlite3.connect(str(tmp_path / nome), isolation_level=None)
    c.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
    M.ensure_schema_version(c, db_id="t", target_version=1, migrations=LADDER[:1])
    return c


def test_non_committa_la_transazione_aperta_dal_chiamante(tmp_path):
    """Il caso nuovo: la scrittura del chiamante resta sua, e revocabile."""
    conn = _conn(tmp_path, "altrui.db")
    conn.execute("BEGIN")
    conn.execute("INSERT INTO t (id, v) VALUES (99, 'lavoro del chiamante')")

    M.ensure_schema_version(conn, db_id="t", target_version=2, migrations=LADDER)

    conn.execute("ROLLBACK")          # deve essere ancora possibile
    altra = sqlite3.connect(str(tmp_path / "altrui.db"))
    try:
        vive = altra.execute("SELECT COUNT(*) FROM t WHERE id = 99").fetchone()[0]
    finally:
        altra.close()
    assert vive == 0, "la riga del chiamante e' stata committata dalla migrazione"
    conn.close()


def test_la_migrazione_gira_lo_stesso_dentro_la_transazione_altrui(tmp_path):
    """Controllo che puo' fallire: non basta non committare, la colonna va aggiunta."""
    conn = _conn(tmp_path, "gira.db")
    conn.execute("BEGIN")
    M.ensure_schema_version(conn, db_id="t", target_version=2, migrations=LADDER)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(t)")}
    assert "salience" in cols
    conn.close()


def test_senza_transazione_del_chiamante_committa_come_sempre(tmp_path):
    """CASO GIA' COPERTO: se la transazione e' sua, la funzione committa lei."""
    conn = _conn(tmp_path, "solo.db")
    assert M.ensure_schema_version(conn, db_id="t", target_version=2,
                                   migrations=LADDER) == 2
    altra = sqlite3.connect(str(tmp_path / "solo.db"))
    try:
        cols = {r[1] for r in altra.execute("PRAGMA table_info(t)")}
    finally:
        altra.close()
    assert "salience" in cols, "la migrazione non e' arrivata su disco"
    conn.close()


def test_il_rollback_su_errore_resta_quello_di_prima(tmp_path):
    """CASO GIA' COPERTO: una migrazione che alza lascia il db alla versione di prima."""
    def _boom(conn):
        raise RuntimeError("la migrazione fallisce")

    conn = _conn(tmp_path, "boom.db")
    try:
        M.ensure_schema_version(conn, db_id="t", target_version=2,
                                migrations=[(1, _v1), (2, _boom)])
    except RuntimeError:
        pass
    assert M.schema_version(conn, "t") == 1
    conn.close()
