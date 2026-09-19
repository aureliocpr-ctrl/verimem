"""Migrare uno store è un ATTO, non un effetto collaterale dell'aprirlo (D-0012).

Fino a questa fetta, aprire uno store vecchio lo migrava sul posto: misurato il
19/09 su copie, `SemanticMemory` porta un file da v7 a v17 alla prima apertura,
aggiunge 21 colonne a `facts` e una tabella al nucleo, senza avviso e senza
ritorno. Chi apriva un backup per leggerlo se lo ritrovava aggiornato — cioè non
era più un backup.

Ora l'apertura si ferma (`schema.verifica_apribile` in `SemanticMemory`), e la
migrazione si chiede: `verimem store migrate <file>`. Il self-heal non è stato
tolto — è la rete messa dopo un incidente vero, due bump di versione dimenticati
che ruppero le scritture in produzione — si è **spostato qui**, dove chi lo
esegue lo vede.

Tre cose che questo modulo fa e che il vecchio percorso non faceva:

1. **il backup si conta, non si crede.** Una copia che esiste non è una copia
   che contiene; e verificarla sull'impronta del file è un falso allarme, perché
   il backup di SQLite compatta e lo sha cambia a contenuto identico. Si contano
   le righe di `facts`, prima e dopo.
2. **la ricevuta dice cosa è successo**: versione prima e dopo, le colonne
   aggiunte, il file di backup. Una migrazione che non lascia traccia è
   indistinguibile da una migrazione silenziosa.
3. **si rifiuta di andare all'indietro.** Uno store più nuovo del codice non si
   «aggiusta»: il codice non sa cosa contiene.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from .schema import (
    VERSIONE_DEL_NUCLEO,
    Marcatura,
    StoreTroppoNuovo,
    leggi_stato,
)


class BackupNonVerificato(RuntimeError):
    """Il backup c'è ma non contiene quello che dovrebbe. Non si migra."""


@dataclass(frozen=True)
class Ricevuta:
    """Che cosa è stato fatto a quale file. Il valore di questo comando sta qui.

    `colonne_aggiunte` è vuoto quando lo store era già allineato: la migrazione
    è idempotente e dirlo è meglio che tacere.
    """

    percorso: Path
    versione_prima: int | None
    versione_dopo: int | None
    backup: Path
    righe_verificate: int
    colonne_aggiunte: dict[str, tuple[str, ...]] = field(default_factory=dict)
    tabelle_aggiunte: tuple[str, ...] = ()

    def __str__(self) -> str:
        righe = [
            f"store      {self.percorso}",
            f"versione   {self.versione_prima} -> {self.versione_dopo}",
            f"backup     {self.backup}  ({self.righe_verificate} righe verificate)",
        ]
        for tabella, colonne in sorted(self.colonne_aggiunte.items()):
            righe.append(f"colonne    {tabella}: +{', '.join(colonne)}")
        if self.tabelle_aggiunte:
            righe.append(f"tabelle    +{', '.join(self.tabelle_aggiunte)}")
        if not self.colonne_aggiunte and not self.tabelle_aggiunte:
            righe.append("colonne    nessuna: lo schema era già quello della versione")
        return "\n".join(righe)


def _conta_i_fatti(percorso: Path) -> int:
    """Le righe di `facts`, lette senza toccare il file."""
    con = sqlite3.connect(f"file:{percorso}?mode=ro", uri=True)
    try:
        return int(con.execute("SELECT count(*) FROM facts").fetchone()[0])
    except sqlite3.DatabaseError:
        return -1
    finally:
        con.close()


def _fotografia(percorso: Path) -> dict[str, tuple[str, ...]]:
    """Le tabelle e le loro colonne, per dire dopo che cosa è cambiato."""
    con = sqlite3.connect(f"file:{percorso}?mode=ro", uri=True)
    try:
        nomi = [n for (n,) in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")]
        return {n: tuple(r[1] for r in con.execute(f'PRAGMA table_info("{n}")'))
                for n in sorted(nomi)}
    finally:
        con.close()


def backup_verificato(percorso: Path, destinazione: Path | None = None) -> tuple[Path, int]:
    """Copia lo store e VERIFICA la copia contando le righe. Torna (file, righe).

    Si usa l'API `backup()` di SQLite e non una copia del file: con il journal
    WAL attivo, copiare il solo `.db` lascia fuori le pagine che stanno nel
    `-wal`, e la copia sarebbe indietro di tutto ciò che non è ancora stato
    riversato — un backup che sembra fatto e ha meno righe.
    """
    percorso = Path(percorso)
    if destinazione is None:
        marca_oraria = time.strftime("%Y%m%d-%H%M%S")
        destinazione = percorso.with_name(
            f"{percorso.stem}-pre-migrazione-{marca_oraria}{percorso.suffix}")

    sorgente = sqlite3.connect(f"file:{percorso}?mode=ro", uri=True)
    copia = sqlite3.connect(destinazione)
    try:
        sorgente.backup(copia)
    finally:
        copia.close()
        sorgente.close()

    attese = _conta_i_fatti(percorso)
    trovate = _conta_i_fatti(destinazione)
    if trovate != attese or attese < 0:
        raise BackupNonVerificato(
            f"il backup {destinazione} ha {trovate} righe in `facts` invece di "
            f"{attese}: non migro. Una copia che esiste non è una copia che "
            f"contiene, e questa non contiene.")
    return destinazione, trovate


def migra_lo_store(percorso: str | Path,
                   destinazione_backup: Path | None = None) -> Ricevuta:
    """Porta uno store alla versione di questo codice, dopo un backup verificato.

    L'ordine non è negoziabile: **prima il backup**, poi la migrazione. Un
    backup fatto dopo fotografa il file già cambiato, cioè non è un ritorno.
    """
    percorso = Path(percorso)
    stato = leggi_stato(percorso)
    if stato.marcatura is Marcatura.IGNOTO:
        raise StoreTroppoNuovo(
            f"non migro uno store che non so leggere: {stato}")

    effettiva = (stato.versione if stato.marcatura is Marcatura.VERSIONE
                 else stato.versione_applicativa)
    if effettiva is not None and effettiva > VERSIONE_DEL_NUCLEO:
        raise StoreTroppoNuovo(
            f"lo store dice di essere alla versione {effettiva}, questo codice "
            f"ne gestisce fino alla {VERSIONE_DEL_NUCLEO}: {percorso}. Non lo "
            f"migro all'indietro — perderei quello che non so di avere.")

    backup, righe = backup_verificato(percorso, destinazione_backup)
    prima = _fotografia(percorso)

    # Qui l'apertura è AUTORIZZATA: è il solo punto del prodotto che lo fa, ed è
    # il punto in cui l'utente l'ha chiesta. Applica la scala e, dove serve, il
    # self-heal che prima girava a ogni apertura di chiunque.
    from .semantic import SemanticMemory

    SemanticMemory(db_path=percorso, _migrazione_autorizzata=True)

    dopo = _fotografia(percorso)
    colonne_aggiunte = {
        tabella: tuple(c for c in colonne if c not in prima.get(tabella, ()))
        for tabella, colonne in dopo.items()
        if tabella in prima and colonne != prima[tabella]
    }
    return Ricevuta(
        percorso=percorso,
        versione_prima=effettiva,
        versione_dopo=leggi_stato(percorso).versione_applicativa,
        backup=backup,
        righe_verificate=righe,
        colonne_aggiunte={k: v for k, v in colonne_aggiunte.items() if v},
        tabelle_aggiunte=tuple(sorted(set(dopo) - set(prima))),
    )


__all__ = ["BackupNonVerificato", "Ricevuta", "backup_verificato", "migra_lo_store"]
