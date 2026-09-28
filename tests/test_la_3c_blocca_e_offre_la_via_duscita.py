"""D-0012 — aprire uno store vecchio si BLOCCA, e il blocco ha una via d'uscita.

Scritte PRIMA del prodotto, e il loro rosso è stato questo:

    Failed: DID NOT RAISE <class 'verimem.schema.StoreDaMigrare'>
    ModuleNotFoundError: No module named 'verimem.store_migrate'
    AssertionError: la costante promette comandi che la CLI non ha: ['store']
    Failed: DID NOT RAISE <class 'verimem.schema.StoreTroppoNuovo'>
    4 failed, 2 passed EXIT=1

Le due verdi erano quella giusta — uno store allineato si apriva già — e il
controllo positivo, che dice se il righello sa vedere un file cambiato.

Le cinque celle sono le condizioni poste con D-0012, rese eseguibili. La
condizione che le tiene insieme è che **comando e blocco vivano nella stessa
richiesta**: un blocco senza via d'uscita è il difetto che questa fetta nasce
per non ripetere — `COMANDO_DI_MIGRAZIONE` nominava `verimem store migrate` e
quel comando non esisteva.

Perché si blocca invece di migrare in silenzio, misurato il 19/09 su copie:

    SemanticMemory su una copia a v16   nucleo 2 -> 3 tabelle, facts +21 colonne
    SemanticMemory su una copia a v7    versione applicativa 7 -> 17

E perché il self-heal non sparisce ma si sposta: aprendo, il prodotto stampa 21
righe «a migration bump was forgotten — column added mechanically». È una rete
messa dopo un incidente vero (due bump dimenticati ruppero le scritture in
produzione). Toglierla sarebbe stato un cambio di disegno mascherato da
rifinitura; spostarla dentro un comando esplicito la rende visibile.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
from pathlib import Path

import pytest

from verimem.schema import TABELLE_DEL_NUCLEO


def _store_a_versione(tmp_path: Path, versione: int = 16) -> Path:
    """Uno store del nucleo a una versione dichiarata.

    La tabella delle versioni si crea col DDL DEL PRODOTTO: scriverla a mano
    diverge in silenzio, ed è già costata un rosso per colpa del banco invece
    che del prodotto (`no such column: upgraded_at`).
    """
    from verimem.migrations import _VERSION_TABLE_DDL

    p = tmp_path / "semantic.db"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT, "
                "topic TEXT, created_at REAL)")
    con.execute("INSERT INTO facts (id, proposition, topic, created_at) "
                "VALUES ('uno', 'La soglia vale 19.0s.', 'prova/3c', 0.0)")
    con.execute(_VERSION_TABLE_DDL)
    con.execute("INSERT INTO _schema_version (db_id, version) VALUES ('semantic', ?)",
                (versione,))
    con.commit()
    con.close()
    return p


def _impronta(p: Path) -> tuple[int, str]:
    """Dimensione e sha: «non si è rotto» non è «non è cambiato»."""
    dati = p.read_bytes()
    return len(dati), hashlib.sha256(dati).hexdigest()


def _nucleo(p: Path) -> dict[str, tuple[str, ...]]:
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        presenti = {n for (n,) in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")
            if n in TABELLE_DEL_NUCLEO}
        return {n: tuple(r[1] for r in con.execute(f'PRAGMA table_info("{n}")'))
                for n in sorted(presenti)}
    finally:
        con.close()


# ---------------------------------------------------------------- cella 1 ---
def test_uno_store_vecchio_si_rifiuta_e_il_file_resta_identico(
        tmp_path: Path) -> None:
    """v16 → `StoreDaMigrare`, e il file **identico byte a byte**.

    I due assert non sono ridondanti: un rifiuto sollevato DOPO aver toccato il
    file lascia lo store migrato e il chiamante convinto del contrario — cioè
    peggio del difetto di partenza. L'impronta è size + sha perché «si apre
    ancora» non è «non è cambiato».
    """
    from verimem.schema import StoreDaMigrare
    from verimem.semantic import SemanticMemory

    p = _store_a_versione(tmp_path, versione=16)
    prima = _impronta(p)

    with pytest.raises(StoreDaMigrare) as caduto:
        SemanticMemory(db_path=p)

    assert _impronta(p) == prima, (
        f"il rifiuto è arrivato DOPO aver toccato il file: "
        f"{prima} -> {_impronta(p)}")
    testo = str(caduto.value)
    for pezzo in ("16", "17", p.name):
        assert pezzo in testo, f"al rifiuto manca {pezzo!r}. Dice: {testo}"


# ---------------------------------------------------------------- cella 2 ---
def test_uno_store_allineato_si_apre_come_oggi(tmp_path: Path) -> None:
    """v17 si apre. È la cella che vieta la cura peggiore del male.

    Il rischio di questa fetta non è lasciar passare uno store rotto: è
    CHIUDERE FUORI quelli buoni. Sul campo vero i file allineati sono 6 su 76,
    e fra loro c'è quello in uso — se questa cella cade, la fetta va fermata.
    """
    from verimem.semantic import SemanticMemory

    p = tmp_path / "semantic.db"
    SemanticMemory(db_path=p)          # creato dal prodotto: è allineato
    dopo_creazione = _nucleo(p)

    SemanticMemory(db_path=p)          # riaperto: non deve cambiare nulla

    assert _nucleo(p) == dopo_creazione, (
        "riaprire uno store allineato ne ha cambiato il nucleo")


# ---------------------------------------------------------------- cella 3 ---
def test_il_comando_migra_una_copia_vecchia_con_backup_e_ricevuta(
        tmp_path: Path) -> None:
    """Una copia v7 → v17 col comando, e la ricevuta dice cosa è successo.

    Il backup va **verificato contando le righe**, non creduto: una copia che
    esiste non è una copia che contiene. La ricevuta porta versione prima e
    dopo, le colonne toccate e il file di backup, perché una migrazione che non
    lascia traccia è indistinguibile da una migrazione silenziosa — che è il
    difetto da cui nasce tutta questa fetta.
    """
    from verimem.store_migrate import migra_lo_store

    p = _store_a_versione(tmp_path, versione=7)
    righe_prima = sqlite3.connect(f"file:{p}?mode=ro", uri=True).execute(
        "SELECT count(*) FROM facts").fetchone()[0]

    ricevuta = migra_lo_store(p)

    assert ricevuta.versione_prima == 7 and ricevuta.versione_dopo == 17
    assert ricevuta.colonne_aggiunte, "la ricevuta non dice cosa ha aggiunto"

    backup = Path(ricevuta.backup)
    assert backup.is_file(), f"il backup dichiarato non esiste: {backup}"
    righe_backup = sqlite3.connect(f"file:{backup}?mode=ro", uri=True).execute(
        "SELECT count(*) FROM facts").fetchone()[0]
    assert righe_backup == righe_prima, (
        f"il backup ha {righe_backup} righe invece di {righe_prima}: una copia "
        f"che esiste non è una copia che contiene")

    from verimem.semantic import SemanticMemory
    SemanticMemory(db_path=p)          # dopo la migrazione si apre


# ---------------------------------------------------------------- cella 4 ---
def test_uno_store_piu_nuovo_del_codice_si_rifiuta(tmp_path: Path) -> None:
    """Il rifiuto vale nei DUE versi.

    Uno store scritto da una versione futura non si «aggiusta» aprendolo: il
    codice non sa cosa contiene, e migrarlo all'indietro perderebbe dati che
    non sa di avere.
    """
    from verimem.schema import StoreTroppoNuovo
    from verimem.semantic import SemanticMemory

    p = _store_a_versione(tmp_path, versione=99)
    prima = _impronta(p)

    with pytest.raises(StoreTroppoNuovo):
        SemanticMemory(db_path=p)

    assert _impronta(p) == prima, "ha toccato uno store che non sa leggere"


# ---------------------------------------------------------------- cella 5 ---
def test_ogni_comando_citato_dal_nucleo_esiste_nella_cli() -> None:
    """Il presidio esteso a `schema.py`, dov'è nato il difetto.

    ⚠️ SI CHIEDE ALLA PORTA, NON ALL'IMPORT, e questa cella ha già sbagliato
    due volte prima di arrivarci — sempre verde, sempre col difetto presente:

        1. leggeva il sorgente di `migrations`: il testo vive in `schema.py` e
           arriva lì per import, quindi nel file guardato non compariva;
        2. chiedeva a `typer.main.get_command(app)` dopo aver importato il
           modulo. Importare esegue TUTTO il file, quindi il comando risultava
           registrato — ma con `python -m verimem.cli` il modulo gira come
           `__main__` e `main()` parte a metà file: un comando definito più in
           basso non viene mai registrato. La CLI rispondeva
           `No such command 'migrate'` mentre questa cella era verde.

    Il livello a cui misuri decide il verdetto: l'unico che conta è il
    sottoprocesso, cioè quello che l'utente digita davvero.
    """
    import re
    import subprocess
    import sys

    from verimem.schema import COMANDO_DI_MIGRAZIONE

    citati = [m.groups() for m in
              re.finditer(r"\bverimem\s+([a-z][a-z0-9-]{2,})"
                          r"(?:\s+([a-z][a-z0-9-]{2,}))?", COMANDO_DI_MIGRAZIONE)]
    assert citati, f"la costante non nomina nessun comando: {COMANDO_DI_MIGRAZIONE}"

    def _chiedi(*argomenti: str) -> tuple[int, str]:
        """Interroga la porta e torna (codice, testo), mai None.

        ⚠️ `capture_output` promette stringhe e in CI su Windows ha consegnato
        `None`: la cella cadeva con `TypeError: argument of type 'NoneType' is
        not iterable`, che non dice niente su ciò che stava misurando. Un test
        che si rompe invece di parlare è muto proprio quando serve. Qui le due
        pipe vengono unite e normalizzate a stringa, così un'assenza di output
        diventa un'informazione — «la porta non ha detto niente» — invece di
        un'eccezione.
        """
        esito = subprocess.run(
            [sys.executable, "-m", "verimem.cli", *argomenti, "--help"],
            capture_output=True, text=True, timeout=180)
        return esito.returncode, (esito.stdout or "") + (esito.stderr or "")

    for parti in citati:
        argomenti = [p for p in parti if p]
        codice, detto = _chiedi(*argomenti)
        assert codice == 0 and "No such command" not in detto, (
            f"la costante promette `verimem {' '.join(argomenti)}` ma la porta "
            f"risponde con codice {codice}:\n{detto[:500] or '(nessun output)'}")

    # CONTROLLO POSITIVO: la stessa domanda su un comando inventato deve
    # FALLIRE, o questa cella direbbe di sì a qualunque cosa.
    codice, detto = _chiedi("questo-non-esiste")
    assert codice != 0 or "No such command" in detto, (
        f"la porta accetta un comando inventato: è cieco il righello, non la "
        f"CLI. Codice {codice}, ha detto: {detto[:300] or '(niente)'}")


# ------------------------------------------------------- controllo positivo --
def test_il_banco_sa_vedere_un_file_cambiato(tmp_path: Path) -> None:
    """Se le celle sopra diventassero verdi, questa dice che non è perché il
    righello ha smesso di guardare."""
    p = _store_a_versione(tmp_path)
    prima = _impronta(p)
    shutil.copy2(p, tmp_path / "copia.db")
    assert _impronta(tmp_path / "copia.db") == prima, "una copia è identica"

    con = sqlite3.connect(p)
    con.execute("ALTER TABLE facts ADD COLUMN prova_del_banco TEXT")
    con.commit()
    con.close()
    assert _impronta(p) != prima, (
        "l'impronta non cambia nemmeno aggiungendo una colonna: righello cieco")
