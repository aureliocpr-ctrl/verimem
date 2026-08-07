"""Il moat dice «verificato al 99», e il fatto finisce in quarantena lo stesso.

TROVATO DA ws5 (il suo «caso 4») e ampliato qui::

    moat passa + parola L1 : moat=passed  gs=96.810  status=quarantined  ['L1.10','L1.15']
    moat passa, niente L1  : moat=passed  gs=99.278  status=quarantined  ['L1.15']

Anche il secondo — «Il modulo di fatturazione è stato testato in produzione»,
con una fonte che lo sostiene al **99,278** — viene trattenuto. Il MOAT, cioè
il meccanismo forte che il prodotto mette in copertina, dice «verificato», e
uno screen lessicale lo scavalca.

Si lega al numero di ws4: **il 90,2% della quarantena del corpus non viene dal
moat ma dallo screen lessicale — 1728 su 1915** — e alla misura di questa notte
sulla precisione di L1, ~40%.

⚠️ QUESTO FILE NON CAMBIA LA PRECEDENZA, e la ragione è che non è una decisione
da prendere di notte: L1 esiste per intercettare le auto-affermazioni («ho
verificato che funziona»), che sono la confabulazione tipica di un agente — e
una fonte «che sostiene» può essere stata scritta dallo stesso agente che
afferma. Ribaltare la precedenza aprirebbe esattamente quella porta.

Quello che si cura è che **chi legge sappia CHI ha deciso**. Oggi la ricevuta
dice `quarantined` e basta: il moat può aver passato con 99 e la decisione
essere di uno screen lessicale, e chi la riceve non ha modo di distinguere una
quarantena per contenuto falso da una per scelta di parole.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

FONTE = ("Verbale: il modulo di fatturazione e stato testato e funziona "
         "correttamente in produzione.")


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


def test_una_quarantena_decisa_da_L1_lo_dichiara(mem):
    """IL CUORE: il moat ha passato, la quarantena è di L1, e ora si vede."""
    r = mem.add("Ho verificato che il modulo di fatturazione funziona "
                "correttamente.", topic="az/q", source=FONTE)
    assert r.get("status") == "quarantined"
    assert r.get("moat") == "passed", "il banco non riproduce il caso di ws5"
    assert r.get("quarantined_by") == "L1", r.get("quarantined_by")


def test_una_quarantena_decisa_dal_MOAT_lo_dichiara(mem):
    """L'altro verso: la fonte NON sostiene, e lì la decisione è del moat."""
    r = mem.add("Il modulo di fatturazione ha 9999 utenti attivi.",
                topic="az/w",
                source="Verbale: il modulo ha 12 utenti attivi.")
    assert r.get("status") == "quarantined"
    assert r.get("moat") == "failed"
    assert r.get("quarantined_by") == "moat", r.get("quarantined_by")


def test_un_fatto_AMMESSO_non_dichiara_nessun_decisore(mem):
    """IL PRESIDIO: il campo compare solo dove c'è una quarantena da
    spiegare. Su una scrittura ordinaria la ricevuta resta com'era."""
    r = mem.add("Il magazzino centrale ha 4200 metri quadrati.", topic="az/m",
                source="Planimetria: magazzino centrale, 4200 metri quadrati.")
    assert r.get("status") != "quarantined"
    assert "quarantined_by" not in r, r.get("quarantined_by")


def test_LA_PRECEDENZA_NON_CAMBIA(mem):
    """⚠️ IL PRESIDIO CHE VALE PIÙ DI TUTTI. Questo file DICHIARA, non
    ribalta: un fatto che L1 tratteneva deve continuare a essere trattenuto.

    Se questo test cade, qualcuno ha fatto cedere lo screen lessicale davanti
    a un moat che passa — e ha aperto la porta all'agente che si scrive da solo
    la fonte con cui si dà ragione. È una decisione di prodotto, non una cura
    di notte."""
    r = mem.add("Ho verificato che il modulo di fatturazione funziona "
                "correttamente.", topic="az/q", source=FONTE)
    assert r.get("status") == "quarantined", (
        "la precedenza e' cambiata: L1 non trattiene piu'")
