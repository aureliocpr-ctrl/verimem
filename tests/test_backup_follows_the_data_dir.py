"""Il backup legge dallo store configurato e scrive in quello di default.

`DEFAULT_BACKUP_ROOT = Path.home() / ".engram" / "backups"` è cablato e
calcolato all'IMPORT, quindi non vede né `ENGRAM_DATA_DIR` né
`VERIMEM_DATA_DIR`. Misurato il 2026-07-29 su uno store di prova con due fatti:

    $ ENGRAM_DATA_DIR=<tmp> verimem backup-all --tier manual
    semantic ok: semantic-20260729-234940-956861.db  rows: 2
    $ find <tmp> -name '*semantic-2026*'      -> niente
    $ ls ~/.engram/backups/manual/            -> il file è lì

Il backup CONTIENE i 2 fatti dello store di prova ed è finito nella cartella dei
backup del corpus reale, che ne ha 6448. Stesso schema di nome, stessa
directory: un restore che pesca il file sbagliato sostituisce 6448 fatti con 2.

Non è un'ipotesi di laboratorio — è successo tre volte in dieci minuti mentre
provavo il comando, e i tre file sono ancora lì.
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest


def _store(dir_: Path, n: int) -> Path:
    """Uno store minimo con ``n`` fatti, senza dipendere dal write path."""
    (dir_ / "semantic").mkdir(parents=True, exist_ok=True)
    db = dir_ / "semantic" / "semantic.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY, "
                "proposition TEXT)")
    for i in range(n):
        con.execute("INSERT OR REPLACE INTO facts VALUES (?, ?)",
                    (f"f{i}", f"fatto numero {i}"))
    con.commit()
    con.close()
    return db


def test_the_backup_lands_under_the_configured_data_dir(monkeypatch):
    d = Path(tempfile.mkdtemp(prefix="bk_dir_"))
    _store(d, 3)
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(d))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(d))
    monkeypatch.setenv("VERIMEM_DATA_DIR", str(d))

    from verimem.backup import default_backup_root
    root = Path(default_backup_root())
    assert str(d) in str(root), (
        f"i backup di questo store finiscono fuori da esso: {root}"
    )
    assert ".engram" not in str(root) or str(d) in str(root), root


def test_two_stores_do_not_share_a_backup_folder(monkeypatch):
    """Il danno concreto: due store, due cartelle. Altrimenti un file di 2
    fatti sta accanto a uno di 6448 con lo stesso schema di nome."""
    a = Path(tempfile.mkdtemp(prefix="bk_a_"))
    b = Path(tempfile.mkdtemp(prefix="bk_b_"))
    _store(a, 2)
    _store(b, 50)

    from verimem.backup import default_backup_root
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(a))
    root_a = Path(default_backup_root())
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(b))
    root_b = Path(default_backup_root())

    assert root_a != root_b, (
        f"due store diversi scrivono i backup nella stessa cartella: {root_a}"
    )


def test_an_explicit_root_still_wins(monkeypatch, tmp_path):
    """Chi passa una destinazione la ottiene: il default non deve togliere una
    scelta a chi la sta già facendo."""
    d = Path(tempfile.mkdtemp(prefix="bk_expl_"))
    _store(d, 1)
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(d))

    from verimem.backup import create_backup
    dest = tmp_path / "altrove"
    info = create_backup(d / "semantic" / "semantic.db", dest, tier="manual")
    assert str(dest) in str(info.path), info.path


@pytest.mark.parametrize("var", ["VERIMEM_DATA_DIR", "ENGRAM_DATA_DIR",
                                 "HIPPO_DATA_DIR"])
def test_it_reads_the_env_at_call_time_not_at_import(monkeypatch, var):
    """Il valore era una costante calcolata all'import: cambiare l'ambiente
    dopo non aveva effetto, ed è il caso di ogni test e di ogni processo che
    configura lo store dopo aver importato la libreria."""
    d = Path(tempfile.mkdtemp(prefix=f"bk_{var}_"))
    _store(d, 1)
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv(var, str(d))

    from verimem.backup import default_backup_root
    assert str(d) in str(default_backup_root()), var
