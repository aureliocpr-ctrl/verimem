"""Un `semantic.db` che contiene una riga di testo prendeva un ✓.

Misurato il 21/08 con uno store in cui `semantic/semantic.db` è un file di
testo da 52 byte::

    ✓ data-dir  … (writable=True; stores: semantic/semantic.db 52 B, …)

Un ✓ e una misura, sul file che il prodotto usa come memoria. I `52 B` un umano
attento li nota; il verde dice il contrario e vince lui. La domanda a cui il
check rispondeva era «la directory è scrivibile?», e non è quella che conta per
chi ha perso lo store.

⚖️ IL PRESIDIO CHE VALE QUANTO IL RESTO: un file **vuoto** non è rotto — sqlite
crea il file prima della prima scrittura, e allarmare lì darebbe un falso
positivo a **ogni installazione nuova**, cioè proprio a chi ha più bisogno di
fidarsi del referto. Le due popolazioni sono misurate qui entrambe.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.doctor import _non_e_un_database

_HEADER = b"SQLite format 3" + bytes(1)


# ─────────────────────  il rilevatore, entrambe le popolazioni  ──────────────

def test_un_file_di_testo_non_e_un_database(tmp_path):
    p = tmp_path / "semantic.db"
    p.write_text("questo non e un database sqlite, e nemmeno ci prova")
    assert "NON e' un database sqlite" in _non_e_un_database(p)


def test_un_file_troncato_lo_dice_col_numero(tmp_path):
    p = tmp_path / "semantic.db"
    p.write_bytes(b"SQLi")
    assert "troppo corto" in _non_e_un_database(p)


def test_presidio_un_file_vuoto_NON_e_rotto(tmp_path):
    """sqlite crea il file prima di scriverci: un'installazione nuova non deve
    vedere un allarme."""
    p = tmp_path / "semantic.db"
    p.write_bytes(b"")
    assert _non_e_un_database(p) == ""


def test_presidio_un_database_vero_passa(tmp_path):
    p = tmp_path / "semantic.db"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE t(a)")
    con.commit()
    con.close()
    assert p.read_bytes()[:16] == _HEADER, "il banco non costruisce uno sqlite"
    assert _non_e_un_database(p) == ""


def test_in_dubbio_tace(tmp_path):
    """Un percorso che non si può leggere non produce un'accusa: manderebbe a
    cercare un guasto che non c'è, e il ramo che chiama lo racconta già."""
    assert _non_e_un_database(tmp_path / "non-esiste.db") in ("", "illeggibile")


# ────────────────────────────  il verdetto del check  ────────────────────────

def _data_dir_check(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    from verimem import doctor as _d
    for c in _d.run_doctor():
        if c["name"] == "data-dir":
            return c
    pytest.fail("il check data-dir non compare nel referto")


def _stato(c):
    return c["status"]


def test_il_check_non_da_verde_su_uno_store_illeggibile(tmp_path, monkeypatch):
    (tmp_path / "semantic").mkdir()
    (tmp_path / "semantic" / "semantic.db").write_text("non sono un database")
    c = _data_dir_check(tmp_path, monkeypatch)
    assert _stato(c) != "ok", (
        f"uno store illeggibile prende ancora un verde: {c!r}")


def test_presidio_una_installazione_nuova_resta_verde(tmp_path, monkeypatch):
    """L'altra popolazione: senza store il check deve restare com'era, o la
    cura darebbe un allarme a ogni prima esecuzione."""
    c = _data_dir_check(tmp_path, monkeypatch)
    assert _stato(c) == "ok", (
        f"una installazione nuova ha perso il verde: {c!r}")
