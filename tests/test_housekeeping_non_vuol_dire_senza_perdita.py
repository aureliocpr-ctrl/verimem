"""«Housekeeping» descrive il MECCANISMO, non l'esito — e la mia
dichiarazione lo lasciava intendere.

Un'ora fa ho consegnato `scope_means` (commit `4121e7a9`) con dentro
«95.1% housekeeping», citando la misura di ws4. Il meccanismo era ed è
giusto: quei ritiri vengono da un hook automatico, trovato nel codice.
Poi ws5 e ws4 sono andati a guardare **cosa succede al contenuto**, con
due metodi diversi, e la parola non regge come rassicurazione.

ws5, sul master che ne ha ritirati 389:

    topic distinti fra i 389 ritirati : 389   → 389 checkpoint DIVERSI,
                                                non versioni dello stesso fatto
    testo ritirato                    : 1.053.033 caratteri
    testo del master                  :     2.694 caratteri
    rapporto 390,9 : 1  →  sopravvive lo 0,26% del testo
    contenuto SPECIFICO sopravvissuto : 0 su 8
      (id di fatti, URL di pull request, path: nessuno è nel master)

ws4, con metodo diverso su 1463 coppie: si perde l'88,7% del vocabolario,
e 3695 dei token persi sono id/path/flag. E ha ritirato il proprio
«housekeeping funziona come deve»: era un giudizio non misurato — aveva
classificato la causa e dedotto l'innocenza.

🔑 **Non è compressione, è sostituzione**: un master di 2.694 caratteri ha
preso il posto di un milione senza conservarne i puntatori — cioè
esattamente ciò che un handoff serve a trasmettere.

Questo test pretende che la dichiarazione porti la PERDITA insieme al
meccanismo. `cross_topic` resta un osservabile e non cambia; cambia la
frase che lo accompagna, perché «housekeeping» da sola si legge «non ti
preoccupare».
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.retirement_log import retirement_breakdown


@pytest.fixture()
def mem(tmp_path):
    m = Memory(tmp_path / "m.db")
    a = m.add("the depot holds 10 crates", topic="log/a")["id"]
    b = m.add("the depot holds 20 crates", topic="altro/b")["id"]
    m.semantic.supersede(a, b, principal="test", reason="banco")
    return m


def test_la_dichiarazione_porta_la_PERDITA_non_solo_il_meccanismo(mem):
    nota = retirement_breakdown(mem.semantic)["scope_means"].lower()
    assert "0.26" in nota or "0,26" in nota, nota
    assert "substitution" in nota or "not compression" in nota, nota


def test_dichiara_che_i_PUNTATORI_sono_quelli_che_si_perdono(mem):
    """Il dato che rende la perdita concreta invece che statistica: gli id,
    i path e le URL sono proprio ciò che un handoff serve a trasmettere."""
    nota = retirement_breakdown(mem.semantic)["scope_means"].lower()
    assert "0 of 8" in nota or "0/8" in nota, nota


def test_NON_dice_piu_che_l_housekeeping_e_a_posto(mem):
    """La parola resta — descrive un meccanismo vero — ma non può stare da
    sola: ws4 ha ritirato il proprio «funziona come deve» perché era un
    giudizio non misurato."""
    nota = retirement_breakdown(mem.semantic)["scope_means"]
    assert "housekeeping" in nota.lower(), "il meccanismo resta descritto"
    for frase in ("works as it should", "harmless", "no loss", "safe"):
        assert frase not in nota.lower(), (frase, nota)


def test_l_osservabile_NON_cambia(mem):
    """La correzione riguarda la FRASE, non il dato: `cross_topic` è il
    confronto di due stringhe e resta quello che era."""
    bd = retirement_breakdown(mem.semantic)
    assert bd["by_scope"]["cross_topic"] == 1
    assert bd["by_scope"]["same_topic"] == 0


def test_dichiara_CHI_ha_misurato_e_con_quale_metodo(mem):
    """Due misure indipendenti con metodi diversi valgono più di una: chi
    legge deve poter risalire, e la seconda è ciò che ha fatto ritirare la
    prima lettura."""
    nota = retirement_breakdown(mem.semantic)["scope_means"]
    assert "2026-08-07" in nota
    assert "vocabulary" in nota.lower() or "88.7" in nota, nota
