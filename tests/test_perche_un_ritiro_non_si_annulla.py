"""`reversible: False` confonde tre situazioni, e si curano in modi diversi.

Misurato sul corpus di casa il 2026-08-05 alle 23:08: la manutenzione
automatica ha ritirato cinque fatti e il registro li dichiara tutti
`reversible: False`. Il perché però non è lo stesso per ogni riga, e
l'operatore che legge fa cose diverse:

- **nessuno scatto è mai stato preso** — il ritiro è stato eseguito da una
  build senza il timone (è il caso di quei cinque: il worker gira
  dall'albero condiviso). Non c'è niente da recuperare, e il segnale utile
  è che il codice in esecuzione non lascia appigli;
- **la finestra è scaduta** — lo scatto c'era, il TTL di 7 giorni è
  passato. Niente da fare oggi, ma il prodotto FUNZIONAVA: è un problema
  di tempi, non di build;
- **è già stato annullato** — qualcuno ha usato il timone e il fatto è
  stato ri-ritirato dopo. Qui la storia è un ping-pong, e cercare l'undo
  è cercare la cosa sbagliata.

Un solo `False` per tre stati è la stessa forma che questo ramo cura da
due giorni: un'etichetta che non distingue il ramo. Qui non è nemmeno
assertiva — è muta — ma manda comunque a fare la cosa sbagliata in due
casi su tre.
"""
from __future__ import annotations

import sqlite3
import time

import pytest

from verimem.client import Memory
from verimem.retirement_log import retirement_log, survivability_counts


@pytest.fixture()
def mem(tmp_path):
    return Memory(tmp_path / "m.db")


def _coppia(m: Memory) -> tuple[str, str]:
    a = m.add("the head office is in Milan", topic="hq/a")["id"]
    b = m.add("the depot is in Turin", topic="hq/b")["id"]
    return a, b


def test_un_ritiro_col_suo_appiglio_e_reversibile_e_non_spiega_niente(mem):
    """Quando si può annullare, il campo del perché non serve e non deve
    riempire la riga di rumore."""
    a, b = _coppia(mem)
    mem.semantic.supersede(a, b, principal="test", reason="banco")

    r = retirement_log(mem.semantic)[0]
    assert r["reversible"] is True
    assert r.get("irreversible_because") is None, r


def test_senza_scatto_dice_che_scatto_non_ce_n_e(mem):
    """Il caso dei cinque ritiri della manutenzione: la build che li ha
    eseguiti non lascia appigli."""
    a, b = _coppia(mem)
    mem.semantic.supersede(a, b, principal="test", reason="banco")
    with sqlite3.connect(mem.semantic.db_path) as con:
        con.execute("DELETE FROM facts_undo_log WHERE fact_id = ?", (a,))

    r = retirement_log(mem.semantic)[0]
    assert r["reversible"] is False
    assert r["irreversible_because"] == "no snapshot", r


def test_una_finestra_scaduta_lo_dice_invece_di_tacere(mem):
    """Lo scatto c'era: il prodotto ha funzionato, sono passati i sette
    giorni. È un'informazione diversa da «non c'è mai stato»."""
    a, b = _coppia(mem)
    mem.semantic.supersede(a, b, principal="test", reason="banco")
    with sqlite3.connect(mem.semantic.db_path) as con:
        con.execute("UPDATE facts_undo_log SET ttl_expires_at = ? "
                    "WHERE fact_id = ?", (time.time() - 60, a))

    r = retirement_log(mem.semantic)[0]
    assert r["reversible"] is False
    assert r["irreversible_because"] == "undo window expired", r


def test_un_appiglio_gia_usato_lo_dice(mem):
    """Ping-pong: annullato e poi ri-ritirato. Cercare l'undo qui è
    cercare la cosa sbagliata."""
    a, b = _coppia(mem)
    mem.semantic.supersede(a, b, principal="test", reason="banco")
    with sqlite3.connect(mem.semantic.db_path) as con:
        con.execute("UPDATE facts_undo_log SET undone_at = ? "
                    "WHERE fact_id = ?", (time.time(), a))

    r = retirement_log(mem.semantic)[0]
    assert r["reversible"] is False
    assert r["irreversible_because"] == "already undone", r


def test_una_riga_sola_per_ritiro_anche_con_piu_scatti(mem):
    """Guardia sulla mia stessa query: il LEFT JOIN sul registro degli
    undo duplicherebbe la riga se un fatto avesse due scatti. Un registro
    che conta due volte lo stesso ritiro e' peggio di uno che tace."""
    a, b = _coppia(mem)
    mem.semantic.supersede(a, b, principal="test", reason="banco")
    with sqlite3.connect(mem.semantic.db_path) as con:
        con.execute(
            "INSERT INTO facts_undo_log (op_id, op_type, fact_id, "
            "pre_row_json, created_at, undone_at, ttl_expires_at) "
            "VALUES (?,?,?,?,?,?,?)",
            ("gemello", "supersede", a, "{}", time.time(), None,
             time.time() + 999))

    righe = [r for r in retirement_log(mem.semantic) if r["loser_id"] == a]
    assert len(righe) == 1, righe


def test_il_contatore_dice_quanti_ritiri_si_possono_ancora_annullare(mem):
    """La finestra di riparazione ha una dimensione, e il quartetto non la
    diceva: «1796 ritirati» non dice se se ne recupera uno o mille."""
    a, b = _coppia(mem)
    c = mem.add("the branch is in Rome", topic="hq/c")["id"]
    mem.semantic.supersede(a, b, principal="test", reason="banco")
    mem.semantic.supersede(c, b, principal="test", reason="banco")
    with sqlite3.connect(mem.semantic.db_path) as con:
        con.execute("DELETE FROM facts_undo_log WHERE fact_id = ?", (c,))

    q = survivability_counts(mem.semantic)
    assert q["retired"] == 2
    assert q["retired_reversible"] == 1, q
    assert "retired_reversible" in q["formula"]
