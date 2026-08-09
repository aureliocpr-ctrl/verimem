"""«Cancellato» deve dire DOVE è ancora leggibile.

Misurato da ws5 il 2026-08-05 sulla macchina reale: il worker Auto-Dream
copia l'INTERO semantic.db in ``dreams/auto-<ts>/`` ogni ~35 minuti e ne
conserva 3, e le copie MANUALI (``dream_<ts>``) non ruotano MAI — quella del
12 maggio contiene ancora 60 fatti che nel vivo non esistono più. Il forget
riesce su tutte le tabelle del DB vivo (grafo compreso, verificato), ma:

    chi cancella un dato ORA lo lascia leggibile nelle copie precedenti
    finché non ruotano — e per sempre nelle copie manuali.

Non è un bug del backup: è che nessuno lo DICE. Stessa classe dei ritiri
invisibili — l'azione riesce, l'effetto è parziale, nessuna superficie lo
dichiara. Questi test pinnano il contratto della dichiarazione:

1. una copia che contiene ancora il fatto viene TROVATA e riportata;
2. una copia che non lo contiene non viene riportata (niente allarmi falsi);
3. la distinzione auto (ruota) / manuale (non ruota mai) arriva al chiamante,
   perché è la differenza fra "per due ore" e "per sempre";
4. la ricevuta del forget porta l'avviso;
5. l'osservabilità non rompe mai la cancellazione: se le copie sono
   illeggibili, il fatto viene cancellato lo stesso.
"""
from __future__ import annotations

import shutil
import sqlite3

import pytest

from verimem.client import Memory
from verimem.residual_copies import residual_copies_for

_DEBITO = "Il cliente Rossi ha un debito di 5000 euro."


@pytest.fixture()
def store_con_copie(tmp_path):
    """Uno store vivo + due copie: una auto (ruota) e una manuale (mai)."""
    data_dir = tmp_path / "engram"
    (data_dir / "semantic").mkdir(parents=True)
    db = data_dir / "semantic" / "semantic.db"
    m = Memory(db)
    fid = m.add(_DEBITO, topic="privacy/clienti", verified_by=["doc"])["id"]

    dreams = data_dir / "dreams"
    for name in ("auto-1785879169", "dream_1778837941"):
        d = dreams / name
        d.mkdir(parents=True)
        # come il worker vero: copia .db + -wal + -shm. Copiare il solo .db
        # produce una copia MUTILATA (le scritture recenti vivono nel WAL
        # finché non c'è un checkpoint) — sbagliato nel mio primo banco, e
        # utile saperlo: una copia senza WAL non è la copia che si crede.
        for suf in ("", "-wal", "-shm"):
            src = db.with_name(db.name + suf)
            if src.exists():
                shutil.copy(src, d / (db.name + suf))
    return m, db, fid, data_dir


def test_trova_le_copie_che_contengono_ancora_il_fatto(store_con_copie):
    _m, db, fid, _dd = store_con_copie
    found = residual_copies_for(db, fid)
    names = {c["name"] for c in found}
    assert names == {"auto-1785879169", "dream_1778837941"}, found
    assert all(c["contains"] for c in found)


def test_una_copia_senza_il_fatto_non_viene_riportata(store_con_copie):
    _m, db, _fid, dd = store_con_copie
    altra = dd / "dreams" / "auto-1785879169" / "semantic.db"
    con = sqlite3.connect(altra)
    con.execute("DELETE FROM facts")
    con.commit()
    con.close()
    found = residual_copies_for(db, _fid)
    assert {c["name"] for c in found} == {"dream_1778837941"}, (
        "una copia che non contiene il fatto non deve produrre un allarme")


def test_distingue_le_copie_che_ruotano_da_quelle_che_non_ruotano(store_con_copie):
    _m, db, fid, _dd = store_con_copie
    per_nome = {c["name"]: c for c in residual_copies_for(db, fid)}
    assert per_nome["auto-1785879169"]["rotates"] is True
    assert per_nome["dream_1778837941"]["rotates"] is False, (
        "la differenza fra 'per qualche ora' e 'per sempre' deve arrivare "
        "a chi legge l'avviso")


def test_la_ricevuta_del_forget_porta_l_avviso(store_con_copie):
    m, _db, fid, _dd = store_con_copie
    res = m.forget_with_report(fid)
    assert res["removed"] is True
    assert m.semantic.get(fid) is None, "la cancellazione deve avvenire"
    copie = res.get("residual_copies") or []
    assert len(copie) == 2, res
    assert any(not c["rotates"] for c in copie), (
        "l'avviso deve dire che una copia non ruota mai")


def test_l_avviso_non_rompe_mai_la_cancellazione(store_con_copie, monkeypatch):
    """Se la scansione delle copie fallisce, il fatto si cancella lo stesso."""
    m, _db, fid, _dd = store_con_copie
    import verimem.residual_copies as rc
    monkeypatch.setattr(rc, "residual_copies_for",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("boom")))
    res = m.forget_with_report(fid)
    assert res["removed"] is True
    assert m.semantic.get(fid) is None
    assert res.get("residual_copies") == [], (
        "degrada a lista vuota, non solleva")
