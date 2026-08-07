"""«SAFE: ALL three quarantine sources» — ma le fonti non sono tre.

ws4 l'ha letto nel codice il 2026-08-07 e me l'ha mandato perché **io
avevo raccomandato quello strumento in `GOVERNANCE.md` un'ora prima**,
chiamando quelle condizioni «tre condizioni di sicurezza».

`requalify_quarantined` recupera un fatto quarantinato se passa tre
controlli — L1, `detect_injection`, e l'admission gate — e il suo docstring
li chiama «ALL three quarantine sources». Ma `classify_admission` viene
invocata con `topic/proposition/status/writer_role/source_episodes`: **il
punteggio del moat non entra**, e nemmeno la contraddizione col corpus.

Misurato sul corpus reale, sui 717 quarantinati vivi:

    con un verdetto del moat : 209
      di cui SOTTO 40        : 158   ← il moat ha detto «la fonte non lo sostiene»
      fra 40 e 90            :  22
      sopra 90               :  29
    mai giudicati            : 508

⇒ **158 fatti sono stati fermati da un presidio che quel controllo non
guarda.** Se non fanno più scattare L1, lo strumento li riporta nel recall
senza che nessuno riguardi la ragione per cui erano fermi.

Questo test non cambia il comportamento: lo **fissa**, perché la parola
«SAFE» nel docstring dice il contrario di quello che il codice fa, e una
caratterizzazione è il modo per non lasciare che la frase resti sola.
"""
from __future__ import annotations

import pathlib
import sqlite3

import pytest

from verimem.admission_cleanup import requalify_quarantined
from verimem.client import Memory


@pytest.fixture()
def store(tmp_path):
    return Memory(tmp_path / "m.db")


def _quarantina(m: Memory, testo: str, *, gs: float | None) -> str:
    fid = m.add(testo, topic="misure")["id"]
    with sqlite3.connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET status = 'quarantined', "
                    "grounding_score = ? WHERE id = ?", (gs, fid))
    return fid


def _recuperabili(m: Memory) -> int:
    return requalify_quarantined(
        pathlib.Path(m.semantic.db_path), dry_run=True)["recoverable"]


def test_un_fatto_BOCCIATO_DAL_MOAT_risulta_recuperabile(store):
    """Il caso dei 158: il moat ha detto «la fonte non lo sostiene» (3.2 su
    100) e le tre condizioni non lo vedono nemmeno. Non è un'ipotesi: è
    quello che lo strumento risponde."""
    _quarantina(store, "the depot in Turin holds 40 crates", gs=3.2)
    assert _recuperabili(store) == 1


def test_e_lo_stesso_numero_di_un_fatto_MAI_giudicato(store):
    """La prova che il punteggio non entra: due fatti identici tranne il
    verdetto danno lo stesso esito."""
    _quarantina(store, "the depot in Turin holds 40 crates", gs=3.2)
    _quarantina(store, "the yard in Milan holds 12 pallets", gs=None)
    assert _recuperabili(store) == 2


def test_un_fatto_che_fa_ancora_scattare_L1_NON_e_recuperabile(store):
    """La guardia che regge: il presidio che lo strumento GUARDA funziona,
    e questo test serve a non far leggere il file come «non funziona
    niente»."""
    _quarantina(store, "I have verified that the migration is complete.",
                gs=None)
    assert _recuperabili(store) == 0


def test_il_dry_run_NON_scrive(store):
    """Il default è dry_run, ed è l'unica ragione per cui questo strumento
    non ha già fatto danno: nessuno l'ha mai eseguito in apply."""
    fid = _quarantina(store, "the depot in Turin holds 40 crates", gs=3.2)
    requalify_quarantined(pathlib.Path(store.semantic.db_path), dry_run=True)
    with sqlite3.connect(store.semantic.db_path) as con:
        stato = con.execute("SELECT status FROM facts WHERE id = ?",
                            (fid,)).fetchone()[0]
    assert stato == "quarantined"
