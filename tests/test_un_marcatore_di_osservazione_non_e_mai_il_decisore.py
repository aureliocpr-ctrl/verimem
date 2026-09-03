"""Un marcatore di osservazione (`*-observe`) non e' mai nominato decisore.

LIVELLO: funzione pubblica `chi_ha_quarantinato` (client.py), chiamata da DUE
porte — il write path di `Memory.add` e il comando `facts add`. Alla porta il
caso qui misurato non e' costruibile da solo: i marcatori `L1-*-observe`
viaggiano sempre accanto all'hit `L1.x` che li ha generati, e quello, per la
precedenza dichiarata in `chi_ha_quarantinato` («non si tocca»), risponde `L1`
comunque. Il presidio sta quindi alla GIUNTURA, non alla porta, ed e' dichiarato.

Contesto (2026-09-03, lead). La convenzione `*-observe` («surfaced, never a
block reason», anti_confab_gate.py) aveva gia' una superficie unica —
`_is_advisory_layer` + `_blocking_layers` — e due presidi
(`test_quale_layer_ha_deciso_non_solo_gate.py`,
`test_il_presidio_del_layer_e_un_sensore_collegato.py`) che la misuravano con
`L3-semantic-observe` e `L4.1-observe`. Nessuno dei due passava dal ramo
`startswith("L1")` di `chi_ha_quarantinato`, che non consultava
`_is_advisory_layer`: con `L1-domain-precision-observe` DA SOLO in ricevuta la
funzione rispondeva `'L1'` (misurato prima della cura: 3 casi su 3), cioe'
nominava decisore chi si era limitato ad avvisare. E' la classe ④ (il bug e'
la giuntura): la superficie unica c'era, un chiamante non ci passava.
La cura di `test_l120_e_un_avviso_non_un_veto.py` (427b4784) filtrava quei
marcatori nel test e prometteva un presidio alla convenzione: e' questo.

Predizione depositata PRIMA di misurare: «con warnings = [solo
L1-domain-precision-observe] e agito = ['L4-grounding'], oggi la funzione
risponde 'L1'». Confermata (RED); dopo la cura risponde 'L4-grounding'.

La lista dei marcatori si legge dal SORGENTE del pacchetto, non da una copia
qui dentro (classe ①): un marcatore nuovo entra in questi test da solo.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from verimem.client import _blocking_layers, _is_advisory_layer, chi_ha_quarantinato

_PKG = Path(__file__).resolve().parents[1] / "verimem"


def _marcatori_emessi_dal_pacchetto() -> list[str]:
    """Ogni stringa `"...-observe"` che il pacchetto puo' mettere in un `layer`."""
    trovati: set[str] = set()
    for py in _PKG.rglob("*.py"):
        trovati.update(re.findall(
            r'"([A-Za-z0-9._-]+-observe)"', py.read_text(encoding="utf-8")))
    return sorted(trovati)


MARCATORI = _marcatori_emessi_dal_pacchetto()


def test_CONTROLLO_il_grep_vede_i_marcatori_noti():
    """Controllo POSITIVO della lettura del sorgente: se il grep tornasse vuoto,
    i test parametrizzati sotto sparirebbero e leggeremmo «tutto verde» su un
    presidio che non misura niente."""
    assert "L1-domain-precision-observe" in MARCATORI, MARCATORI
    assert "L3-semantic-observe" in MARCATORI, MARCATORI


@pytest.mark.parametrize("marcatore", MARCATORI)
def test_ogni_marcatore_emesso_e_un_avviso_per_la_superficie_unica(marcatore):
    """La convenzione di nomi: chi emette un marcatore di osservazione deve
    finire in `-observe`, e la superficie unica deve riconoscerlo."""
    assert _is_advisory_layer(marcatore), marcatore
    assert _blocking_layers([{"layer": marcatore}]) == [], marcatore


@pytest.mark.parametrize("marcatore", MARCATORI)
@pytest.mark.parametrize("agito", [["L4-grounding"], ["L3-contradiction"], []])
def test_un_marcatore_da_solo_non_e_mai_nominato_decisore(marcatore, agito):
    """Il cuore: chi ha solo avvisato non prende il nome della quarantena. Con
    `agito` vuoto la risposta giusta e' `gate` (stessa cella del presidio
    esistente su `L3-semantic-observe`)."""
    atteso = agito[0] if agito else "gate"
    assert chi_ha_quarantinato(
        "passed", [{"layer": marcatore}], agito=agito) == atteso


def test_CONTROLLO_un_hit_l1_vero_resta_il_decisore():
    """La popolazione OPPOSTA: la precedenza di L1 «non si tocca». Senza questa
    cella, una cura che escludesse l'intera famiglia L1 passerebbe i test sopra
    e leggeremmo «cura riuscita» su un'attribuzione rotta."""
    assert chi_ha_quarantinato(
        "passed", [{"layer": "L1.13"}], agito=["L4-grounding"]) == "L1"
    assert chi_ha_quarantinato(
        "passed",
        [{"layer": "L1.13"}, {"layer": "L1-domain-precision-observe"}],
        agito=["L4-grounding"]) == "L1"
