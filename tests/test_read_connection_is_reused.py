"""Le letture del read path riusano una connessione invece di aprirne cento.

MISURATO IL 26/07, strumentando ``_connect`` per cronometrare solo apertura e
chiusura: su quattro recall reali il **45,2%** del tempo se ne va li' — 463 ms su
1025 — con circa 100-104 connessioni per query. Il conteggio combacia con una
misura indipendente della notte (102: 71 su semantic.db + 31 su entity_kg.db).

Il costo non sono i PRAGMA. Togliendoli si risparmiano 0,307 ms per connessione,
31 ms in tutto, il 3%: ``journal_mode`` e' persistente nel file e ``synchronous``
si divide con lui lo stesso costo di header, quindi levarne uno non serve. Il
costo e' il PRIMO ACCESSO su una connessione fresca — leggere lo schema,
preparare la statement, aprire il WAL: connect+close senza query costa 0,347 ms,
con una SELECT 2,224 ms. Non si ottimizza, si evita.

E non vengono da una funzione ingorda ma da cento CHIAMATE: ``get`` circa 35
volte per query dallo scorer della fusione, ``facts_for_entity`` 20,
``get_by_name`` 5, ``fact_counts`` 3 — tutte SELECT, verificato sull'AST.

DUE VINCOLI, e sono la ragione del disegno.

Uno: sqlite3 vieta di usare una connessione da un thread diverso da quello che
l'ha aperta, e il read path lavora in thread (rerank, fusione). Quindi una per
thread, non una condivisa con un lock — che oltre a essere piu' fragile
serializzerebbe letture che oggi vanno in parallelo.

Due, ed e' il piu' insidioso: un lettore persistente che lasci aperta una read
transaction AFFAMA I CHECKPOINT DEL WAL, e il file cresce senza mai potersi
consolidare. E' lo stesso vincolo che ``_db_data_version`` rispetta emettendo
solo PRAGMA e mai DML — il suo commento lo dice a chiare lettere. Qui le SELECT
servono, quindi il presidio e' un ``rollback`` all'uscita: chiude qualunque
transazione lasciata aperta da un cursore non esaurito, e su una connessione
pulita non costa niente.
"""
from __future__ import annotations

import sqlite3
import threading

import pytest

from verimem import semantic as sem
from verimem._sqlite_pragma import read_connection


@pytest.fixture()
def db(tmp_path):
    p = tmp_path / "letture.db"
    conn = sqlite3.connect(p)
    conn.execute("CREATE TABLE t (id TEXT PRIMARY KEY, v TEXT)")
    conn.execute("INSERT INTO t VALUES ('a', 'uno')")
    conn.commit()
    conn.close()
    return p


def test_the_same_thread_gets_the_same_connection(db):
    """Il cuore: cento chiamate, una connessione."""
    with read_connection(db) as c1:
        pass
    with read_connection(db) as c2:
        pass
    assert c1 is c2, (
        "due letture nello stesso thread hanno aperto due connessioni: il "
        "primo accesso si paga di nuovo, che e' il costo da evitare")


def test_two_threads_never_share_a_connection(db):
    """sqlite3 vieta l'uso cross-thread, e il read path lavora in thread:
    condividere una connessione la farebbe sollevare, o peggio corrompere."""
    viste: dict[str, object] = {}

    def leggi(nome):
        with read_connection(db) as c:
            c.execute("SELECT v FROM t WHERE id='a'").fetchone()
            viste[nome] = c

    t1 = threading.Thread(target=leggi, args=("uno",))
    t2 = threading.Thread(target=leggi, args=("due",))
    t1.start(); t2.start(); t1.join(5); t2.join(5)
    assert len(viste) == 2
    assert viste["uno"] is not viste["due"], (
        "due thread hanno ricevuto la STESSA connessione")


def test_a_different_database_gets_its_own_connection(db, tmp_path):
    """Il read path legge due file — semantic.db e entity_kg.db — e la cache
    e' per file, altrimenti il secondo store leggerebbe dal primo."""
    altro = tmp_path / "altro.db"
    conn = sqlite3.connect(altro)
    conn.execute("CREATE TABLE t (id TEXT PRIMARY KEY, v TEXT)")
    conn.commit(); conn.close()
    with read_connection(db) as c1:
        pass
    with read_connection(altro) as c2:
        pass
    assert c1 is not c2


def test_a_read_transaction_is_always_closed_on_the_way_out(db):
    """Il presidio contro l'unico modo in cui un lettore persistente fa danno.

    LIMITE DICHIARATO: questo test NON falsifica il rollback. Una mutazione
    che lo rimuove non lo fa fallire, perche' nel codice di oggi nessuna lettura
    tiene vivo un cursore — `conn.execute(...).fetchone()` lo scarta e la
    transazione si chiude da se'. Il rollback e' quindi una guardia difensiva,
    non la cura di un difetto attuale, e va letto per quello che e'.

    CHE IL CASO ESISTA E' PERO' DIMOSTRATO: su una connessione con un cursore
    lasciato a meta', ``PRAGMA journal_mode=WAL`` solleva "cannot change into
    wal mode from within a transaction" — cioe' SQLite la considera dentro una
    transazione. E ``conn.in_transaction`` di Python dice False: riflette solo
    le transazioni di scrittura che gestisce il driver e **non vede le read
    transaction**. La prima versione di questo test usava proprio
    ``in_transaction``, e per questo la mutazione "togli il rollback" NON
    veniva rilevata: misurava con uno strumento cieco a cio' che cercava.

    Un lettore che tiene aperta una read transaction impedisce ai checkpoint
    del WAL di consolidare, e il file cresce senza potersi ridurre — lo stesso
    vincolo che ``_db_data_version`` rispetta non emettendo mai DML.
    """
    conn = sqlite3.connect(db)
    conn.executemany("INSERT INTO t VALUES (?, ?)",
                     [(str(i), f"v{i}") for i in range(50)])
    conn.commit(); conn.close()

    with read_connection(db) as c:
        c.execute("SELECT v FROM t").fetchone()     # UNA riga su 51: a meta'

    # il rilevatore dimostrato: cambiare journal mode solleva se una
    # transazione e' aperta, mentre in_transaction resta cieco e direbbe False
    assert c.in_transaction is False                 # lo strumento sbagliato
    try:
        c.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.OperationalError as exc:
        pytest.fail(
            f"una read transaction e' rimasta aperta ({exc}): i checkpoint del "
            "WAL non possono consolidare e il file cresce senza ridursi")


def test_every_hot_read_of_the_read_path_is_wired(db):
    """Il buco che la mutazione ha trovato: nessun test verificava il
    CABLAGGIO. L'helper poteva essere perfetto e non essere usato da nessuno —
    e infatti riportando entity_kg a ``self._connect()`` tutti i test
    passavano. Verificato sul sorgente, che e' l'unico posto dove la domanda
    "questa lettura riusa la connessione?" ha una risposta stabile."""
    import ast
    import pathlib as _pl

    attesi = {
        "verimem/semantic.py": {"get"},
        "verimem/entity_kg.py": {"get", "get_by_name", "facts_for_entity",
                                 "fact_counts"},
    }
    for modulo, funzioni in attesi.items():
        albero = ast.parse(_pl.Path(modulo).read_text(encoding="utf-8"))
        for nodo in ast.walk(albero):
            if not isinstance(nodo, ast.FunctionDef) or nodo.name not in funzioni:
                continue
            usa = False
            for sub in ast.walk(nodo):
                if (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Name)
                        and sub.func.id == "read_connection"):
                    usa = True
            assert usa, (
                f"{modulo}:{nodo.name} apre ancora una connessione per ogni "
                "lettura: l'helper esiste ma quella chiamata non lo usa")


def test_a_broken_connection_is_replaced_not_kept(db):
    """Se la connessione riusata si guasta, va buttata: tenerla in cache
    significherebbe che ogni lettura successiva di quel thread fallisce per
    sempre — un guasto transitorio diventerebbe permanente."""
    with read_connection(db) as c1:
        pass
    c1.close()                              # la rompe di proposito
    with read_connection(db) as c2:
        c2.execute("SELECT v FROM t WHERE id='a'").fetchone()
    assert c2 is not c1, "la connessione chiusa e' stata riusata"


def test_the_reused_connection_sees_writes_from_elsewhere(db):
    """Una connessione che vive a lungo non deve servire uno snapshot vecchio:
    e' l'errore che renderebbe il read path piu' veloce e SBAGLIATO."""
    with read_connection(db) as c:
        assert c.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1

    fuori = sqlite3.connect(db)
    fuori.execute("INSERT INTO t VALUES ('z', 'tre')")
    fuori.commit(); fuori.close()

    with read_connection(db) as c2:
        n = c2.execute("SELECT COUNT(*) FROM t").fetchone()[0]
    assert n == 2, (
        f"la connessione riusata vede ancora {n} righe invece di 2: serve uno "
        "snapshot stantio, cioe' e' veloce e sbagliata")


def test_repeated_reads_open_one_connection_not_one_each(tmp_path, monkeypatch):
    """Il meccanismo, misurato dove sta il guadagno: N letture ripetute devono
    aprire UNA connessione, non N.

    La prima versione di questo test contava le connessioni di un recall vero e
    passava senza misurare niente — su trenta fatti la fusione non parte
    (soglia 50) e il grafo entita' e' vuoto, quindi i punti caldi non vengono
    mai chiamati: **2 connessioni contate, con una soglia a 25**. Le circa cento
    connessioni di un recall vengono dalla FUSIONE, che in un test sintetico non
    si accende. Quindi qui si misura il meccanismo, che e' verificabile, e il
    guadagno end-to-end si misura sul corpus reale come per gli altri cicli.
    """
    aperte = []
    vera = sqlite3.connect

    def spia(*a, **k):
        aperte.append(str(a[0]) if a else "?")
        return vera(*a, **k)

    p = tmp_path / "molte_letture.db"
    conn = vera(p)
    conn.execute("CREATE TABLE t (id TEXT PRIMARY KEY, v TEXT)")
    conn.executemany("INSERT INTO t VALUES (?, ?)",
                     [(str(i), f"v{i}") for i in range(40)])
    conn.commit()
    conn.close()

    monkeypatch.setattr(sqlite3, "connect", spia)
    for i in range(40):                     # quanti get() fa una fusione
        with read_connection(p) as c:
            c.execute("SELECT v FROM t WHERE id=?", (str(i),)).fetchone()
    monkeypatch.setattr(sqlite3, "connect", vera)

    assert len(aperte) == 1, (
        f"quaranta letture hanno aperto {len(aperte)} connessioni: il primo "
        "accesso — 1,9 ms — si sta pagando a ogni lettura invece di una volta")
