"""Aprire uno store non deve cambiare IL NUCLEO (D-0009).

⚠️ LA GRANDEZZA MISURATA QUI È IL NUCLEO, NON IL FILE, e la differenza non è
una sfumatura: misurando i byte, quattro costruttrici su quattro risultano
colpevoli; misurando le sei tabelle del nucleo, una sola lo è.

    costruttore                          NUCLEO    tabelle proprie aggiunte
    adjudication_log.AdjudicationLog     intatto   adjudications
    decay_job._ensure_last_decay_column  CAMBIA    (nessuna) -> facts: last_decay_at
    gateway.GatewayKeys                  intatto   gateway_keys
    document_index.DocumentIndex         intatto   chunks, sqlite_sequence

Tre sono CO-INQUILINE: creano la propria tabella nello stesso file SQLite. Il
file cresce, il nucleo resta identico, e vietarlo sarebbe una cura contro un
comportamento legittimo. Le loro celle qui sono verdi e servono da presidio: se
un domani una di loro tocca `facts`, questo banco lo dice prima della CI.

Una sola aggiunge una colonna a `facts` fuori dalla scala delle migrazioni —
ma NON aprendo: `_ensure_last_decay_column` ha un solo chiamante in tutto il
prodotto (`decay_job.py:168`, dentro `run_decay_pass`), quindi è la potatura a
migrare fuori scala, non un'apertura. È un difetto vero e vive nel suo banco,
perché mescolarlo qui direbbe «aprire» di una cosa che apertura non è.

Resta invece qui la scala stessa: `ensure_schema_version` promuoveva la
versione di un passo senza applicare DDL, e quella è la porta da cui il nucleo
cambia numero senza cambiare schema.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from verimem.schema import TABELLE_DEL_NUCLEO


def _store_a_versione(tmp_path: Path, versione: int = 16) -> Path:
    """Uno store con una tabella del nucleo e una versione dichiarata.

    Costruito qui e non copiato da uno store vero: un banco non tocca lo store
    di nessuno, nemmeno in lettura.

    La tabella delle versioni si crea col DDL DEL PRODOTTO e non a mano: una
    copia qui dentro diverge in silenzio dall'originale, e il primo rosso di
    questo banco è stato proprio quello — `no such column: upgraded_at`, cioè
    una cella rossa per un difetto suo invece che del prodotto.
    """
    from verimem.migrations import _VERSION_TABLE_DDL

    p = tmp_path / "semantic.db"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT, "
                "topic TEXT, created_at REAL)")
    con.execute("INSERT INTO facts (id, proposition, topic, created_at) "
                "VALUES ('uno', 'La soglia vale 19.0s.', 'prova/nucleo', 0.0)")
    con.execute(_VERSION_TABLE_DDL)
    con.execute("INSERT INTO _schema_version (db_id, version) VALUES ('semantic', ?)",
                (versione,))
    con.commit()
    con.close()
    return p


def _impronta_del_nucleo(p: Path) -> dict[str, tuple[str, ...]]:
    """Le tabelle del nucleo presenti e le loro colonne. Nient'altro.

    Quello che una co-inquilina aggiunge di suo NON entra qui: è la ragione per
    cui questo righello dà un verdetto diverso da uno che pesa il file.
    """
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        presenti = {
            nome for (nome,) in con.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'")
            if nome in TABELLE_DEL_NUCLEO
        }
        return {
            nome: tuple(r[1] for r in con.execute(f'PRAGMA table_info("{nome}")'))
            for nome in sorted(presenti)
        }
    finally:
        con.close()


def _versione(p: Path) -> int | None:
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        riga = con.execute(
            "SELECT version FROM _schema_version WHERE db_id = 'semantic'").fetchone()
        return int(riga[0]) if riga else None
    finally:
        con.close()


def _apre_senza_toccare_il_nucleo(p: Path, apri) -> None:
    """Il contratto: aprire può aggiungere roba propria, non toccare il nucleo."""
    prima = _impronta_del_nucleo(p)
    versione_prima = _versione(p)

    apri(p)

    dopo = _impronta_del_nucleo(p)
    if dopo != prima:
        cambiate = {
            t: set(dopo.get(t, ())) ^ set(prima.get(t, ()))
            for t in set(prima) | set(dopo)
            if prima.get(t) != dopo.get(t)
        }
        raise AssertionError(
            f"aprire ha cambiato il nucleo: {cambiate}. Chi apre uno store non "
            f"deve riscriverne lo schema fuori dalla scala delle migrazioni — e "
            f"la versione dichiarata è passata da {versione_prima} a "
            f"{_versione(p)}, cioè il numero non racconta il cambio")


def test_il_registro_delle_aggiudicazioni_non_tocca_il_nucleo(tmp_path: Path) -> None:
    """Verde oggi: crea `adjudications`, che è roba sua. Presidio per domani."""
    from verimem.adjudication_log import AdjudicationLog

    _apre_senza_toccare_il_nucleo(_store_a_versione(tmp_path),
                                  lambda p: AdjudicationLog(p))


def test_le_chiavi_del_gateway_non_toccano_il_nucleo(tmp_path: Path) -> None:
    """Verde oggi: crea `gateway_keys`, che è roba sua. Presidio per domani."""
    from verimem.gateway import GatewayKeys

    _apre_senza_toccare_il_nucleo(_store_a_versione(tmp_path), lambda p: GatewayKeys(p))


def test_l_indice_dei_documenti_non_tocca_il_nucleo(tmp_path: Path) -> None:
    """Verde oggi: crea `chunks`, che è roba sua. Presidio per domani."""
    from verimem.document_index import DocumentIndex

    _apre_senza_toccare_il_nucleo(_store_a_versione(tmp_path),
                                  lambda p: DocumentIndex(db_path=p))


def test_la_scala_non_promuove_un_numero_che_lo_schema_non_sostiene(
        tmp_path: Path) -> None:
    """ROSSO: la stampa cieca a un passo promuove 16 -> 17 senza le colonne.

    ⚠️ La stampa cieca è DELIBERATA e il commento nel prodotto la difende
    («the legitimate no-DDL-yet case»): su un bootstrap fresco non c'è DDL da
    applicare e stampare è giusto. Il difetto non è che esista, è che nessuno
    verifichi il presupposto — e `schema_corrisponde()` sa verificarlo.

    Il salto di UN passo è l'unico che ci arriva: due o più il codice li
    rifiuta già («migration ladder is not contiguous»). La cura non deve
    riscrivere quella difesa, solo chiudere il passo che le sfugge.
    """
    from verimem.migrations import ensure_schema_version

    p = _store_a_versione(tmp_path, versione=16)
    prima = _impronta_del_nucleo(p)

    con = sqlite3.connect(p)
    try:
        with pytest.raises(RuntimeError, match="zero DDL"):
            ensure_schema_version(con, db_id="semantic", target_version=17,
                                  migrations=[])
    finally:
        con.close()

    # Il rifiuto conta solo se il file è rimasto dov'era: un'eccezione dopo la
    # scrittura lascerebbe lo store promosso e il chiamante convinto del
    # contrario, che è peggio del difetto di partenza.
    assert _versione(p) == 16, (
        f"la scala ha rifiutato MA aveva già promosso la versione a "
        f"{_versione(p)}: il rifiuto arriva dopo la scrittura")
    assert _impronta_del_nucleo(p) == prima, "e il nucleo è rimasto intatto"


def test_il_rifiuto_dice_i_due_numeri_il_file_e_il_comando(tmp_path: Path) -> None:
    """D-0009: un rifiuto che non dice come uscirne costringe a cercare.

    E chi cerca nel momento sbagliato apre il file a mano, cioè fa proprio la
    cosa che il rifiuto voleva impedire. Quattro elementi, non tre: la versione
    TROVATA, quella richiesta, QUALE file, e il comando che scioglie il blocco.
    La versione trovata serve perché senza di lei il messaggio dice che
    qualcosa non va senza dire da dove si parte.
    """
    from verimem.migrations import ensure_schema_version
    from verimem.schema import COMANDO_DI_MIGRAZIONE

    p = _store_a_versione(tmp_path, versione=16)
    con = sqlite3.connect(p)
    try:
        with pytest.raises(RuntimeError) as caduto:
            ensure_schema_version(con, db_id="semantic", target_version=17,
                                  migrations=[])
    finally:
        con.close()

    testo = str(caduto.value)
    mancano = [nome for nome, pezzo in (
        ("la versione trovata (16)", "16"),
        ("la versione richiesta (17)", "17"),
        ("il file", p.name),
        ("il comando", COMANDO_DI_MIGRAZIONE.split(" {")[0]),
    ) if pezzo not in testo]
    assert not mancano, f"al rifiuto mancano {mancano}. Dice: {testo}"


def test_aprire_dichiara_quale_store_e_come_l_ha_trovato(tmp_path: Path,
                                                        monkeypatch) -> None:
    """L'altra metà di D-0009: se l'apertura tocca lo schema, lo dica.

    `SemanticMemory.__init__` esegue lo script dello schema aprendo, e restare
    fuori dalla scala è una scelta MOTIVATA nel codice (due bump dimenticati
    ruppero le scritture in produzione). Quindi la cura non è vietare: è che
    l'apertura dichiari QUALE file ha aperto e COME L'HA TROVATO.

    Lo stato va letto prima del tocco, perché dopo non esiste più: una volta
    eseguito lo script, «com'era» non è più recuperabile da nessuna parte.
    """
    import verimem.observability as obs
    from verimem.semantic import SemanticMemory

    visti: list[tuple[str, dict]] = []
    monkeypatch.setattr(obs, "emit",
                        lambda nome, **p: visti.append((nome, p)))

    p = _store_a_versione(tmp_path, versione=16)
    SemanticMemory(db_path=p)

    aperture = [(n, c) for n, c in visti if n == "store.opened"]
    assert aperture, (
        f"aprire non ha dichiarato niente: eventi visti {[n for n, _ in visti]}. "
        f"Uno store aperto senza dichiarazione è esattamente il caso in cui non "
        f"si sa più quale file il prodotto ha toccato")
    _, campi = aperture[0]
    assert campi.get("percorso") == str(p), (
        f"la dichiarazione non dice QUALE store: {campi}")
    assert campi.get("versione_applicativa") == 16, (
        f"la dichiarazione non dice come l'ha trovato PRIMA del tocco: {campi}")


def test_la_versione_del_nucleo_ha_sempre_un_criterio() -> None:
    """Presidio: se il nucleo sale di versione, la mappa delle attese lo segue.

    `schema_corrisponde` torna False quando non ha un criterio per una versione
    — scelta giusta — ma significa che alzare `VERSIONE_DEL_NUCLEO` a 18 senza
    aggiungere la voce 18 ad `ATTESE_PER_VERSIONE` spegne in silenzio chi si
    appoggia a lei, con un messaggio corretto che nessuno sta leggendo mentre
    cambia un numero.
    """
    from verimem.schema import ATTESE_PER_VERSIONE, VERSIONE_DEL_NUCLEO

    assert VERSIONE_DEL_NUCLEO in ATTESE_PER_VERSIONE, (
        f"il codice dichiara la versione {VERSIONE_DEL_NUCLEO} ma "
        f"`ATTESE_PER_VERSIONE` conosce solo {sorted(ATTESE_PER_VERSIONE)}: "
        f"ogni store verrebbe rifiutato, e il messaggio direbbe la verità a "
        f"nessuno")
    assert ATTESE_PER_VERSIONE[VERSIONE_DEL_NUCLEO], (
        "il criterio c'è ma è vuoto: un insieme vuoto è contenuto in qualunque "
        "schema, quindi `schema_corrisponde` direbbe sempre True")


def test_il_righello_vede_una_colonna_vera(tmp_path: Path) -> None:
    """CONTROLLO POSITIVO: se le celle sopra diventassero verdi, questa dice
    che non è perché il righello ha smesso di guardare.

    Un'impronta che non cambia mai farebbe passare tutto. Qui si verifica che
    sappia cambiare — e che guardi il NUCLEO: la tabella aggiunta da una
    co-inquilina non deve entrarci, o il verdetto tornerebbe quello sbagliato.
    """
    p = _store_a_versione(tmp_path)
    base = _impronta_del_nucleo(p)

    con = sqlite3.connect(p)
    con.execute("ALTER TABLE facts ADD COLUMN prova_del_banco TEXT")
    con.execute("CREATE TABLE roba_di_un_co_inquilino (x INTEGER)")
    con.commit()
    con.close()

    dopo = _impronta_del_nucleo(p)
    assert dopo != base, (
        "l'impronta non è cambiata nemmeno aggiungendo una colonna a `facts`: "
        "il righello è cieco e le celle sopra non provano niente")
    assert "roba_di_un_co_inquilino" not in dopo, (
        "il righello ha contato una tabella che non è del nucleo: misurerebbe "
        "il file invece dell'invariante, ed è l'errore che questo banco corregge")


@pytest.mark.parametrize("nome", ["adjudication_log", "decay_job", "gateway",
                                  "document_index"])
def test_le_quattro_porte_esistono_ancora(nome: str) -> None:
    """Se un modulo sparisce o si rinomina, questo banco deve dirlo invece di
    diventare silenziosamente verde."""
    import importlib

    assert importlib.import_module(f"verimem.{nome}") is not None
