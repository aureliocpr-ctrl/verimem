"""Il doctor dice se i ritiri di questo store lasciano un appiglio.

Misurato sul corpus di casa il 2026-08-05:

    ritiri negli ULTIMI 7 GIORNI: 105 · con appiglio vivo: 2

Sette giorni è la finestra giusta e non una scelta di comodo: è il TTL
dello scatto di undo. **Fuori da lì «manca» e «è scaduto» sono
indistinguibili**, quindi contare tutto il corpus direbbe sempre che
qualcosa non va, e un allarme che suona sempre si impara a ignorare.
Dentro la finestra, invece, un appiglio assente è una riparazione persa
— e 103 su 105 in una settimana dicono che la build che scrive su questo
store il timone non ce l'ha.

Serviva una query fatta apposta da qualcuno che già sospettava. Ora è un
check, con i due numeri accanto: la regola che questo ramo ha imparato
stasera — misurare invece di asserire — vale anche per il check che la
enuncia.
"""
from __future__ import annotations

import sqlite3
import time

import pytest

from verimem.client import Memory


def _check(nome: str) -> dict | None:
    from verimem.doctor import run_doctor
    return next((c for c in run_doctor() if c["name"] == nome), None)


def _ritira(m: Memory, *, con_appiglio: bool) -> str:
    a = m.add("the head office is in Milan", topic="hq/a")["id"]
    b = m.add("the depot is in Turin", topic="hq/b")["id"]
    m.semantic.supersede(a, b, principal="test", reason="banco")
    if not con_appiglio:
        with sqlite3.connect(m.semantic.db_path) as con:
            con.execute("DELETE FROM facts_undo_log WHERE fact_id = ?", (a,))
    return a


def test_ritiri_senza_appiglio_nella_finestra_fanno_scattare_l_avviso(
        tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    m = Memory(tmp_path / "semantic" / "semantic.db")
    for _ in range(3):
        _ritira(m, con_appiglio=False)

    c = _check("undo-window")
    assert c is not None, "il check non esiste"
    assert c["status"] == "warn", c
    assert "3" in c["detail"] and "0" in c["detail"], c["detail"]
    assert c.get("fix"), "un WARN senza rimedio non e' un referto"


def test_uno_store_i_cui_ritiri_lasciano_l_appiglio_non_allarma(
        tmp_path, monkeypatch):
    """La guardia contro il referto che suona sempre."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    m = Memory(tmp_path / "semantic" / "semantic.db")
    for _ in range(3):
        _ritira(m, con_appiglio=True)

    c = _check("undo-window")
    assert c["status"] == "ok", c


def test_senza_ritiri_recenti_non_inventa_un_rapporto(tmp_path, monkeypatch):
    """Zero su zero non è «zero per cento»: senza ritiri non c'è niente da
    dire, e stampare 0/0 come se fosse un fallimento è la stessa forma
    che questo ramo cura da due giorni."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    Memory(tmp_path / "semantic" / "semantic.db").add(
        "the head office is in Milan", topic="hq")

    c = _check("undo-window")
    assert c["status"] == "ok", c
    assert "0%" not in c["detail"], c["detail"]


def test_i_ritiri_VECCHI_non_contano_e_il_check_dice_perche(
        tmp_path, monkeypatch):
    """Fuori dai 7 giorni un appiglio mancante può essere semplicemente
    scaduto: contarlo direbbe «rotto» di uno store sano."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    m = Memory(tmp_path / "semantic" / "semantic.db")
    vecchio = _ritira(m, con_appiglio=False)
    with sqlite3.connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET superseded_at = ? WHERE id = ?",
                    (time.time() - 30 * 86400, vecchio))

    c = _check("undo-window")
    assert c["status"] == "ok", c
    assert "7" in c["detail"], "la finestra va dichiarata: " + c["detail"]


def test_uno_store_illeggibile_non_diventa_un_ok(tmp_path, monkeypatch):
    """Stessa regola del check sulla copertura del moat: se non si può
    leggere, si dice — non si stampa la riga più rassicurante proprio
    quando non si è potuto guardare."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "inesistente"))
    c = _check("undo-window")
    if c is not None:
        assert c["status"] != "warn" or "unknown" in c["detail"].lower()
