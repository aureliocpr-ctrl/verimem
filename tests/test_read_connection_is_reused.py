"""Le letture del read path riusano una connessione invece di aprirne cento.

CONTATE, non stimate: 102 connessioni per query — 71 su semantic.db, 31 su
entity_kg.db. A 2,224 ms l'una (misura sotto) fanno 227 ms su un recall di 686,9,
il 33%. Dopo il cablaggio, contate di nuovo: 5 per query, 11 ms, il 2,7%.

Una versione precedente di questo commento diceva **45,2%**, ottenuto
cronometrando solo apertura e chiusura dentro quattro recall: quello strumento
era un contextmanager avvolto attorno a ``_connect``, quindi misurava anche se
stesso. La cifra sopra e' invece aritmetica su due quantita' contate
separatamente, che non richiede di fidarsi di un cronometro.

CINQUE, NON UNA, ed e' il limite che conta: il riuso e' per THREAD, e il read
path crea un thread NUOVO per ogni query (semantic.py, ``hippo-rerank`` e
``hippo-ppr-fusion``). Le ~63 letture dentro una query collassano su 4-5
connessioni — da li' vengono i 227 ms — e poi il thread muore e la query dopo
riparte da zero. Misurato: 5 per query, piatte su sei query, 51 delle 66 aperte
dai thread ``hippo-*``. Farle sopravvivere richiederebbe worker persistenti per
gli 11 ms che restano: non vale il meccanismo, ma non va descritto come "una
connessione invece di cento" — sono cinque per query, ogni query.

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
solo PRAGMA e mai DML — il suo commento lo dice a chiare lettere.

E il presidio che era scritto qui non presidiava niente: c'era un ``rollback``
all'uscita, dichiarato capace di "chiudere qualunque transazione lasciata aperta
da un cursore non esaurito", e non ne chiude nessuna
(``test_only_closing_the_cursor_ends_a_read_transaction``). L'invariante sta
sui CHIAMANTI — lasciare morire il cursore dentro il blocco — e da oggi e'
verificata sull'AST invece che sperata
(``test_no_reader_keeps_a_cursor_alive``).
"""
from __future__ import annotations

import contextlib
import sqlite3
import threading

import pytest

from verimem import semantic as sem
from verimem._sqlite_pragma import close_read_connections, read_connection


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


def test_only_closing_the_cursor_ends_a_read_transaction(tmp_path):
    """Smentisce cio' che questo file affermava fino al 26/07.

    C'era un ``conn.rollback()`` all'uscita, con un commento che diceva "chiude
    qualunque transazione lasciata aperta da un cursore non esaurito". FALSO,
    misurato: con un cursore vivo a meta' risultato, ``rollback()``,
    ``commit()``, ``interrupt()`` e i comandi ``ROLLBACK``/``COMMIT``/``END``
    lasciano la transazione APERTA — gli ultimi tre rifiutano con "no
    transaction is active", che e' la spiegazione: la lettura non e' tenuta
    dalla transazione del driver, e' tenuta da uno STATEMENT non finalizzato, e
    solo chi possiede il cursore puo' finalizzarlo. Il presidio non esisteva, e
    per questo il rollback e' stato rimosso invece di annotato.

    DUE ERRORI DI STRUMENTO, entrambi commessi qui prima di arrivarci:
    ``conn.in_transaction`` e' cieco alle read transaction (dice sempre False),
    e ``PRAGMA journal_mode=WAL`` — il rilevatore che funziona — MUTA il journal
    mode: alla seconda lettura sullo stesso file e' un no-op che non solleva
    piu' niente. Quindi un file fresco per ogni osservazione, e una sola.

    E QUESTO TEST NON FALSIFICA LA RIMOZIONE, va detto perche' e' il rilievo con
    cui il critic gate ha votato contro: rimettendo il ``conn.rollback()`` nel
    modulo, i test di questo file passano 9 su 9 identici. Non e' una lacuna
    colmabile — e' la definizione di cio' che e' stato rimosso. Un'istruzione
    senza effetti osservabili non e' distinguibile da nessun test, altrimenti
    avrebbe effetti. La rimozione poggia sulla MISURA qui sotto (nessuna azione
    sulla connessione chiude la transazione, quindi quella riga non faceva cio'
    che dichiarava) e sul contratto di sola lettura, non su una regressione
    catturata.
    """
    def fresco(nome: str):
        p = tmp_path / nome
        c = sqlite3.connect(p)
        c.execute("CREATE TABLE t (id TEXT PRIMARY KEY, v TEXT)")
        c.executemany("INSERT INTO t VALUES (?, ?)",
                      [(str(i), f"v{i}") for i in range(50)])
        c.commit(); c.close()
        return p

    def aperta_dopo(nome: str, azione) -> bool:
        with read_connection(fresco(nome)) as conn:
            cur = conn.execute("SELECT v FROM t")   # cursore VIVO: senza tenerlo
            cur.fetchone()                          # in una locale, niente tx
            with contextlib.suppress(sqlite3.OperationalError):
                azione(conn, cur)
            assert conn.in_transaction is False, "in_transaction ora VEDE le read tx"
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                return False
            except sqlite3.OperationalError:
                return True
            finally:
                cur.close()

    assert aperta_dopo("a.db", lambda c, u: None)
    assert aperta_dopo("b.db", lambda c, u: c.rollback()), (
        "rollback() ora chiude le read transaction: il presidio in-place e' "
        "diventato possibile, rivalutare _sqlite_pragma.read_connection")
    assert aperta_dopo("c.db", lambda c, u: c.commit())
    assert aperta_dopo("d.db", lambda c, u: c.interrupt())
    assert aperta_dopo("e.db", lambda c, u: c.execute("ROLLBACK"))
    assert not aperta_dopo("f.db", lambda c, u: u.close()), (
        "chiudere il cursore non chiude piu' la transazione: era l'UNICA cosa "
        "che la chiudeva, e su cui poggia l'invariante dei chiamanti")
    close_read_connections()


def test_no_reader_keeps_a_cursor_alive():
    """L'invariante che protegge davvero, e non e' lasciata alla disciplina.

    Poiche' nessuna azione sulla connessione chiude una read transaction (test
    sopra), l'unica difesa e' che ogni lettore lasci MORIRE il cursore dentro il
    blocco: ``conn.execute(...).fetchone()`` su un temporaneo, mai
    ``cur = conn.execute(...)`` tenuto in una variabile. La connessione e'
    riusata e vive quanto il thread — nel MainThread quanto il processo — quindi
    un cursore appeso bloccherebbe i checkpoint del WAL per tutta quella vita.

    Verificato sull'AST e non a occhio: e' un invariante sui chiamanti, e i
    chiamanti cambiano. Stesso metodo di ``test_every_hot_read_of_the_read_path
    _is_wired``, che e' l'unico che aveva preso il buco del cablaggio.

    E i file li SCOPRE, non li elenca. La prima versione girava su una lista di
    due moduli scelti da me, mentre la docstring afferma l'invariante su OGNI
    lettore: un terzo modulo che usasse ``read_connection`` non sarebbe stato
    guardato. E' lo stesso punto cieco che il 26/07 ha fatto passare 12 rossi —
    gli otto file "correlati" li avevo scelti io, e il piu' esposto non c'era.
    Un controllo universale su una lista mia non e' universale.

    Per la stessa ragione il test FALLISCE se non trova nessun blocco: un
    rename di ``read_connection`` lo renderebbe altrimenti vacuo in silenzio,
    cioe' verde per assenza di cose da controllare.

    IL CRITERIO E' INVERTITO, e ci e' voluto un giro di critic gate. La prima
    versione cercava la forma SBAGLIATA — un ``ast.Assign`` il cui valore e' una
    ``.execute`` — e lasciava passare tutto il resto. Ma la forma sbagliata ha
    molte facce, e il worker "counterexample" ne ha nominate tre che sfuggivano:
    ``cur: T = conn.execute(...)`` (e' un ``AnnAssign``, non un ``Assign``),
    ``(cur := conn.execute(...))``, e soprattutto ``cur = conn.cursor()``
    seguito da ``cur.execute(...).fetchone()``, dove il fetch c'e' ma il cursore
    ha un nome e vive quanto lui. Concluse che "GUARANTEED" era esagerato, e
    aveva ragione. Se ne aggiungono due che erano sfuggite anche a lui:
    ``read_connection`` usata senza ``with`` (un ``__enter__`` a mano evita
    ogni controllo su quel blocco) e i sorgenti fuori da ``verimem/``.

    Quindi ora si esige la forma GIUSTA, che e' una sola: ogni ``.execute(``
    dentro il blocco deve essere l'oggetto di un ``.fetchone()``/
    ``.fetchall()``/``.fetchmany()`` attaccato all'espressione, cosi' che nessun
    nome sopravviva al cursore. E ``.cursor()`` e' vietato senza eccezioni.

    ``tests/`` resta ESCLUSO di proposito: il test qui sopra tiene vivo un
    cursore APPOSTA, perche' e' l'unico modo di osservare una transazione aperta.
    """
    import ast
    import pathlib as _pl

    def e_read_connection(nodo) -> bool:
        if not isinstance(nodo, ast.Call):
            return False
        f = nodo.func
        nome = (f.id if isinstance(f, ast.Name)
                else f.attr if isinstance(f, ast.Attribute) else "")
        return nome == "read_connection"

    sorgenti = [p for d in ("verimem", "benchmark", "scripts")
                if _pl.Path(d).is_dir()
                for p in sorted(_pl.Path(d).rglob("*.py"))]
    ispezionati = 0

    for percorso in sorgenti:
        albero = ast.parse(percorso.read_text(encoding="utf-8"))
        dove = percorso.as_posix()

        # 1) sempre dentro un `with`: un __enter__ a mano evita il resto
        dentro_with = {id(it.context_expr) for nodo in ast.walk(albero)
                       if isinstance(nodo, ast.With) for it in nodo.items
                       if e_read_connection(it.context_expr)}
        for nodo in ast.walk(albero):
            if e_read_connection(nodo) and id(nodo) not in dentro_with:
                pytest.fail(
                    f"{dove}:{nodo.lineno} apre read_connection fuori da un "
                    "`with`: l'uscita non e' garantita e nessun controllo su "
                    "quel blocco puo' funzionare")

        # 2) dentro il blocco, ogni execute va consumato nell'espressione
        for nodo in ast.walk(albero):
            if not isinstance(nodo, ast.With) or not any(
                    e_read_connection(it.context_expr) for it in nodo.items):
                continue
            ispezionati += 1
            consumati = {id(sub.func.value) for sub in ast.walk(nodo)
                         if isinstance(sub, ast.Call)
                         and isinstance(sub.func, ast.Attribute)
                         and sub.func.attr in ("fetchone", "fetchall",
                                               "fetchmany")
                         and isinstance(sub.func.value, ast.Call)}
            for sub in ast.walk(nodo):
                if not (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)):
                    continue
                if sub.func.attr == "cursor":
                    pytest.fail(
                        f"{dove}:{sub.lineno} da' un NOME a un cursore dentro "
                        "read_connection: vive quanto il nome, quindi la read "
                        "transaction resta aperta anche dopo il fetch")
                if sub.func.attr == "execute" and id(sub) not in consumati:
                    pytest.fail(
                        f"{dove}:{sub.lineno} non consuma il cursore "
                        "nell'espressione (serve .fetchone()/.fetchall()/"
                        ".fetchmany() attaccato): il cursore sopravvive, la "
                        "read transaction resta aperta per tutta la vita del "
                        "thread e i checkpoint del WAL non consolidano piu'")

    assert ispezionati >= 6, (
        f"trovati solo {ispezionati} blocchi read_connection: erano 6 il "
        "26/07. Se sono stati rinominati o rimossi questo test non controlla "
        "piu' niente e passa per assenza di lavoro, non per correttezza")


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
