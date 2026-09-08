"""`semantic._rango_di_fiducia` è la funzione che sa dire «non lo so», e fino a
oggi non aveva un test suo: `git grep -n _rango_di_fiducia -- tests` su main
(7b9e8ca1) → nessuna riga. Segnalato da @ws6 Aldo l'08/09; la cella arriva prima
che altro codice ci si appoggi.

Perché conta adesso: la cura del rango (ramo `ws3/rango-stato-sconosciuto`) la
mette nel percorso caldo del gate — `_rango_per_supersessione` la chiama a ogni
scrittura che può ritirare un fatto. Una funzione nel percorso caldo senza test
propri è debito, e questo è il momento in cui si paga poco.

Il contratto, dal codice (`semantic.py:599-628`), non da come lo ricordo:
    status is None      -> None
    status noto         -> il suo rango
    status ignoto       -> None      (`.get(status)` senza default: «non lo so»)
"""
from __future__ import annotations

import pytest

from verimem.semantic import (
    _STATUS_RANK,
    _rango_di_fiducia,
    _row_passes_status_filter,
)


@pytest.mark.parametrize("status", sorted(_STATUS_RANK))
def test_ogni_stato_noto_ha_il_suo_rango(status):
    assert _rango_di_fiducia(status) == _STATUS_RANK[status]


def test_lo_stato_assente_e_None_non_zero():
    assert _rango_di_fiducia(None) is None


@pytest.mark.parametrize("ignoto", [
    "user_manual",       # 2.494 fatti vivi nello store di casa (08/09)
    "bootstrap_rule", "bootstrap_lesson", "diary", "lesson_manual",
    "bench_manual", "pending",
    "",                  # stringa vuota: non è uno stato, non è «debole»
    "REVIEW", "Verified",  # maiuscole: la tabella è case-sensitive
])
def test_uno_stato_che_la_tabella_non_conosce_e_None_e_non_zero(ignoto):
    r = _rango_di_fiducia(ignoto)
    assert r is None, f"{ignoto!r} -> {r!r}: «non lo so» non è un numero"


def test_None_e_zero_non_sono_la_stessa_cosa():
    """Il cuore del docstring: `.get(status, 0)` traduce «non lo so» in «vale
    poco», e solo la seconda autorizza un ritiro."""
    assert _rango_di_fiducia("user_manual") is None
    assert _STATUS_RANK.get("user_manual", 0) == 0
    assert _STATUS_RANK["legacy_unverified"] == 0
    # cioè: col vecchio default uno stato ignoto valeva quanto `legacy_unverified`


class _Row(dict):
    """La riga che il filtro di lettura riceve (`sqlite3.Row` si comporta così
    per ciò che serve qui: accesso per chiave)."""


def test_LIMITE_DICHIARATO_il_filtro_di_lettura_usa_ancora_il_default_zero():
    """Il docstring di `_rango_di_fiducia` dichiara che `min_status`
    (`_row_passes_status_filter`) usa ancora `.get(status, 0)`, di proposito:
    «lì l'errore NASCONDE un fatto, e chi legge può abbassare la soglia; qui
    l'errore lo RITIRA».

    Questo test FISSA il limite invece di lasciarlo solo scritto: uno stato
    ignoto passa il filtro dove passerebbe un `legacy_unverified` (rango 0) e
    non dove passerebbe un `model_claim`. Se un domani il filtro cambia, questa
    cella lo dice — ed è il punto che il design di «held» deve guardare, perché
    uno stato nuovo non ancora in `_STATUS_RANK` sarebbe servito come il più
    debole, non come voluto.
    """
    riga = _Row(status="user_manual")
    assert _row_passes_status_filter(riga, min_status="legacy_unverified") is True
    assert _row_passes_status_filter(riga, min_status="model_claim") is False
