"""Il forget ripulisce il suo db, non quelli accanto — misurato il 2026-08-24.

Il README promette: «True forget (GDPR): deleted data cannot resurface via
history or time travel — shipped, probe-tested». Con la configurazione di DEFAULT
e' vero, e `test_il_dato_cancellato_non_riemerge` lo presidia bene: copre `search`,
il time travel (`recall_as_of`), l'accesso diretto e scansiona «ogni colonna di
ogni tabella. Niente scorciatoie sulle vie note».

Ma scansiona UN SOLO FILE, `mem.semantic.db_path`. Con `VERIMEM_AUDIT_LOG=1` il
prodotto scrive anche `adjudications.db`, che ha una colonna `proposition TEXT NOT
NULL` (`adjudication_log.py:109`) e che nessuno ripulisce al `delete`::

    add("...codice fiscale ... RSSMRA85T10A562S.")
    delete(fid, purge_history=True)   ->  True
    il segreto compare in   adjudications.db : adjudications.proposition = 1

⚖️ NON E' UN BUG DEL FORGET, ed e' la ragione per cui questo file marca `xfail`
invece di rompere la suite: un audit trail che si cancella non e' un audit trail.
La tensione fra il diritto alla cancellazione e l'auditabilita' e' reale e la
decisione non e' tecnica — o il forget ripulisce anche l'audit (e l'audit perde il
suo scopo), o il README dichiara l'eccezione. Finche' non e' decisa, questo test
tiene il fatto VISIBILE: `strict=True`, quindi il giorno in cui qualcuno lo cura
il test diventa rosso e chiede di essere aggiornato, invece di tacere.

⚠️ Chi accende l'audit log lo fa quasi sempre per CONFORMITA'. E' l'unico che paga
la differenza, ed e' l'unico che oggi non viene avvisato.
"""
from __future__ import annotations

import glob
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory

SEGRETO = "RSSMRA85T10A562S"
FRASE = f"Il codice fiscale di Mario Rossi e' {SEGRETO}."


def _dove_compare_in_tutta_la_cartella(radice: Path, ago: str) -> list[str]:
    """Ogni colonna di ogni tabella di OGNI file, non del solo db principale.

    E' la stessa esaustivita' di `test_il_dato_cancellato_non_riemerge`, spostata
    di un livello: da «tutte le vie dentro un file» a «tutti i file».
    """
    trovato: list[str] = []
    for f in glob.glob(str(radice / "**" / "*"), recursive=True):
        if not os.path.isfile(f):
            continue
        try:
            con = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
        except sqlite3.Error:
            continue
        try:
            for (t,) in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"):
                for col in con.execute(f"PRAGMA table_info({t})"):
                    n = con.execute(
                        f"SELECT COUNT(*) FROM {t} WHERE CAST({col[1]} AS TEXT) "
                        f"LIKE ?", (f"%{ago}%",)).fetchone()[0]
                    if n:
                        trovato.append(f"{os.path.basename(f)}:{t}.{col[1]}={n}")
        except sqlite3.Error:
            pass
        finally:
            con.close()
    return trovato


def _scrivi_e_cancella(audit: str, monkeypatch) -> list[str]:
    monkeypatch.setenv("VERIMEM_AUDIT_LOG", audit)
    radice = Path(tempfile.mkdtemp())
    mem = Memory(str(radice / "g.db"))
    ric = mem.add(FRASE, topic="pii")
    fid = ric.get("id")
    assert _dove_compare_in_tutta_la_cartella(radice, SEGRETO), (
        "il fatto non e' nemmeno stato scritto: il test non proverebbe nulla")
    assert mem.delete(fid, purge_history=True) is True
    return _dove_compare_in_tutta_la_cartella(radice, SEGRETO)


def test_CONTROLLO_col_default_il_dato_sparisce_davvero(monkeypatch):
    """La popolazione opposta, e rende leggibile l'xfail qui sotto.

    Senza l'audit log il forget fa esattamente cio' che il README promette. Se un
    giorno cadesse ANCHE questo, il difetto non sarebbe piu' «una porta scoperta»
    ma «il forget non funziona», che e' un'altra gravita'.
    """
    resti = _scrivi_e_cancella("0", monkeypatch)
    assert not resti, f"il dato cancellato sopravvive col DEFAULT: {resti}"


@pytest.mark.xfail(strict=True, reason=(
    "noto e non deciso (2026-08-24): con VERIMEM_AUDIT_LOG=1 la proposizione "
    "resta in adjudications.db. Non e' un bug del forget — e' la tensione fra "
    "cancellazione e auditabilita', e la scelta (ripulire l'audit oppure "
    "dichiarare l'eccezione nel README) non e' tecnica. strict: quando viene "
    "decisa, questo diventa rosso e chiede di essere aggiornato."))
def test_con_l_audit_acceso_il_segreto_resta_nel_db_fratello(monkeypatch):
    """La riga del README non distingue le due configurazioni: qui la differenza
    e' misurata, cosi' chi accende l'audit sa cosa sta accettando."""
    resti = _scrivi_e_cancella("1", monkeypatch)
    assert not resti, f"il dato cancellato sopravvive in: {resti}"
