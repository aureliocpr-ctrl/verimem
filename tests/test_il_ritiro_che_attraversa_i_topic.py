"""«Il ritiro attraversa i topic» separa due popolazioni con una colonna.

ws4, 2026-08-07, riprodotto qui in indipendenza sul corpus reale:

    ritiri DENTRO lo stesso topic :  266
    ritiri FRA topic diversi      : 1538
      di cui `autohook-snapshot daily collapse` : 1463  (95.1%)

⇒ Il 92% dei 1804 ritiri è HOUSEKEEPING — un collasso di snapshot
giornalieri e una deduplica di testi byte-identici — e la supersessione
«che mangia i fatti veri» riguarda ~130 casi, non 1758. Il numero che
girava fra noi era l'housekeeping.

⚠️ **Espongo l'OSSERVABILE, non il verdetto.** `cross_topic` è certo: è
il confronto di due stringhe salvate. «Housekeeping» è
un'INTERPRETAZIONE, misurata al 95,1% su questo corpus — quindi vive
nella dichiarazione, non in un'etichetta per riga. Mettere
`housekeeping: true` su ogni riga sarebbe asserire una causa in un caso
su venti dove non vale: la classe che questo ramo cura da due giorni.

E serve a qualcosa di preciso: chi implementerà «versionare invece di
ritirare» deve versionare i **266 DENTRO**, non i 1538 FRA — quindi i 266
devono essere ELENCABILI, non solo contati.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.retirement_log import retirement_breakdown, retirement_log


@pytest.fixture()
def mem(tmp_path):
    return Memory(tmp_path / "m.db")


def _ritira(m: Memory, i: int, *, stesso_topic: bool) -> str:
    a = m.add(f"the depot {i} holds 10 crates", topic=f"log/t{i}")["id"]
    b = m.add(f"the depot {i} holds 20 crates",
              topic=(f"log/t{i}" if stesso_topic else f"altro/t{i}"))["id"]
    m.semantic.supersede(a, b, principal="test", reason="banco")
    return a


def test_la_riga_dice_se_il_ritiro_attraversa_i_topic(mem):
    dentro = _ritira(mem, 0, stesso_topic=True)
    fra = _ritira(mem, 1, stesso_topic=False)

    righe = {r["loser_id"]: r for r in retirement_log(mem.semantic)}
    assert righe[dentro]["cross_topic"] is False, righe[dentro]
    assert righe[fra]["cross_topic"] is True, righe[fra]


def test_un_vincitore_MANCANTE_non_diventa_ne_l_uno_ne_l_altro(mem):
    """Se il vincitore non esiste, i topic non si possono confrontare:
    None dice «non confrontabile», False direbbe «stesso topic» — e sul
    corpus reale un caso c'è."""
    import sqlite3
    a = _ritira(mem, 2, stesso_topic=True)
    with sqlite3.connect(mem.semantic.db_path) as con:
        con.execute("UPDATE facts SET superseded_by = 'ffffffffffff' "
                    "WHERE id = ?", (a,))

    r = next(x for x in retirement_log(mem.semantic) if x["loser_id"] == a)
    assert r["cross_topic"] is None, r


def test_i_DENTRO_si_possono_ELENCARE_non_solo_contare(mem):
    """Il punto pratico: chi implementa «versionare invece di ritirare»
    deve poter guardare i 266, uno per uno."""
    dentro = _ritira(mem, 3, stesso_topic=True)
    _ritira(mem, 4, stesso_topic=False)

    soli = retirement_log(mem.semantic, cross_topic=False)
    assert [r["loser_id"] for r in soli] == [dentro], soli
    assert len(retirement_log(mem.semantic, cross_topic=True)) == 1
    assert len(retirement_log(mem.semantic)) == 2, "senza filtro escono tutti"


def test_il_riassunto_conta_le_due_popolazioni(mem):
    _ritira(mem, 5, stesso_topic=True)
    _ritira(mem, 6, stesso_topic=False)
    _ritira(mem, 7, stesso_topic=False)

    sc = retirement_breakdown(mem.semantic)["by_scope"]
    assert sc["same_topic"] == 1 and sc["cross_topic"] == 2, sc


def test_l_interpretazione_sta_nella_DICHIARAZIONE_non_nella_riga(mem):
    """«Housekeeping» è misurato al 95,1%: nella dichiarazione, col suo
    numero e col suo margine d'errore. Una riga NON porta un'etichetta
    che sarebbe falsa in un caso su venti."""
    _ritira(mem, 8, stesso_topic=False)

    bd = retirement_breakdown(mem.semantic)
    nota = bd["scope_means"]
    assert "95" in nota, nota
    assert "housekeeping" in nota.lower()
    for r in retirement_log(mem.semantic):
        assert "housekeeping" not in r, r
