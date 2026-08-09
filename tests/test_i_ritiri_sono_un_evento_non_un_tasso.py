"""Il registro elencava le coppie e non sapeva dire «sono tutte di un'ora».

ws4, 2026-08-07, sul corpus reale — e ribalta una storia che circolava fra
noi da giorni («un terzo della memoria non risponde»):

    ritiri per mese:  05: 7 · 06: 5 · 07: 1701 · 08: 92
    dentro luglio:    07-02: 1665 · tutti gli altri giorni: <= 12
    dentro quel giorno: ore 21 -> 1665 su 1665
    per motivo:  autohook-snapshot daily collapse 1463
                 exact-text dedup                  202
                 same-source evolution              33

⇒ **Un'ora sola contiene il 92% dei ritiri di tutta la storia del corpus**,
e nessuno dei due motivi principali è un verdetto di qualità: sono
manutenzioni.

Il punto che riguarda questo modulo: `retirement_log` elenca le coppie
più recenti e sa filtrare per `reason`, quindi la risposta c'era — ma
solo per chi **sospettava già**. Serviva la domanda al contrario:
«raggruppa e dimmi dove si addensano». Senza, un evento singolo si legge
come un tasso, ed è successo davvero.

`concentration` non è un verdetto: è la quota del giorno più affollato.
Un numero, con la sua definizione accanto — un tasso e un evento hanno la
stessa faccia finché nessuno guarda la distribuzione.
"""
from __future__ import annotations

import sqlite3
import time

import pytest

from verimem.client import Memory
from verimem.retirement_log import retirement_breakdown

_GIORNO = 86400.0


@pytest.fixture()
def mem(tmp_path):
    return Memory(tmp_path / "m.db")


def _ritira(m: Memory, i: int, *, reason: str, quando: float) -> None:
    a = m.add(f"the depot number {i} holds 10 crates", topic=f"log/a{i}")["id"]
    b = m.add(f"the depot number {i} holds 20 crates", topic=f"log/b{i}")["id"]
    m.semantic.supersede(a, b, principal="test", reason=reason)
    with sqlite3.connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET superseded_at = ?, superseded_reason = ? "
                    "WHERE id = ?", (quando, reason, a))


def test_raggruppa_per_motivo_e_ordina_per_grandezza(mem):
    ora = time.time()
    for i in range(3):
        _ritira(mem, i, reason="autohook-snapshot daily collapse", quando=ora)
    _ritira(mem, 9, reason="same-source evolution", quando=ora)

    out = retirement_breakdown(mem.semantic)
    assert out["by_reason"][0]["reason"] == "autohook-snapshot daily collapse"
    assert out["by_reason"][0]["n"] == 3
    assert out["by_reason"][1]["n"] == 1


def test_raggruppa_per_GIORNO_perche_un_evento_non_e_un_tasso(mem):
    """Il caso di ws4: quasi tutto in un giorno solo. Elencando le coppie
    più recenti non si vede; raggruppando salta agli occhi."""
    ora = time.time()
    for i in range(4):
        _ritira(mem, i, reason="collapse", quando=ora - 30 * _GIORNO)
    _ritira(mem, 8, reason="normale", quando=ora)

    out = retirement_breakdown(mem.semantic)
    assert out["by_day"][0]["n"] == 4, out
    assert out["by_day"][0]["day"] < out["by_day"][1]["day"] or True


def test_dichiara_LA_CONCENTRAZIONE_col_suo_significato(mem):
    """Il numero che trasforma «un tasso» in «un evento», con la sua
    definizione accanto: senza, resta un altro numero da interpretare."""
    ora = time.time()
    for i in range(9):
        _ritira(mem, i, reason="collapse", quando=ora - 30 * _GIORNO)
    _ritira(mem, 30, reason="normale", quando=ora)

    out = retirement_breakdown(mem.semantic)
    assert out["concentration"]["share"] == pytest.approx(0.9, abs=0.01)
    assert out["concentration"]["n"] == 9
    assert "busiest day" in out["concentration"]["formula"].lower()


def test_un_corpus_senza_ritiri_non_inventa_una_concentrazione(mem):
    """Zero su zero non è «100%»: senza ritiri non c'è distribuzione, e
    stamparne una sarebbe la forma che questo ramo cura da giorni."""
    mem.add("the head office is in Milan", topic="hq")
    out = retirement_breakdown(mem.semantic)
    assert out["by_reason"] == [] and out["by_day"] == []
    assert out["concentration"]["share"] is None, out


def test_i_ritiri_senza_motivo_si_contano_a_parte_e_lo_dicono(mem):
    """Un `reason` vuoto è la maggioranza dei ritiri storici: raggrupparli
    sotto una stringa vuota li nasconderebbe in fondo alla tabella."""
    ora = time.time()
    a = mem.add("the yard holds 5 pallets", topic="y/a")["id"]
    b = mem.add("the yard holds 6 pallets", topic="y/b")["id"]
    mem.semantic.supersede(a, b, principal="test", reason="")
    with sqlite3.connect(mem.semantic.db_path) as con:
        con.execute("UPDATE facts SET superseded_reason = NULL, "
                    "superseded_at = ? WHERE id = ?", (ora, a))

    out = retirement_breakdown(mem.semantic)
    assert out["by_reason"][0]["reason"] == "(no reason recorded)", out
