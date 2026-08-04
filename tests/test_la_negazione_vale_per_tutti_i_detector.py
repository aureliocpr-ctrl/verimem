"""Nove detector L1 su dodici leggevano la SMENTITA come il claim.

TROVATO DA WS5, che ha misurato la mia cura di un'ora prima e l'ha trovata
incompleta: «Il difetto NON è stato risolto» prendeva ancora `L1.10`. Avevo
appena curato la negazione dentro `l1_tested_detector` (L1.15) senza chiedermi
**chi altro fa la stessa cosa** — cioè commettendo la classe che questo progetto
insegue da giorni: *la cura c'era e mancava lo sweep*.

Misurato subito dopo, dodici coppie affermativo/negato:

    L1.10  «Il modulo NON funziona in produzione.»        scatta
    L1.11  «Il sistema NON è pronto per la produzione.»   scatta
    L1.12  «Il servizio NON è sicuro contro SQL injection.» scatta
    L1.13  «La migrazione NON è completata.»              scatta
    L1.14  «Il codice NON è documentato.»                 scatta
    L1.16  «La modifica NON è stata approvata.»           scatta
    L1.17  «Il job NON è monitorato.»                     scatta
    L1.18  «Il processo NON è automatizzato.»             scatta
    L1.15  «Il modulo NON è stato testato.»               silenzio  (curato)

**LA CURA NON VA RIPETUTA NOVE VOLTE.** Copiare la guardia in ogni detector
sarebbe l'altra classe ricorrente — una copia invece della superficie unica — e
fra sei mesi divergerebbero come sono già divergiate le due liste di negatori
trovate il 2026-08-03. La guardia sta **dove passano tutti**, cioè nel punto in
cui `_l1_warnings` raccoglie i warning: da lì vale per i detector di oggi **e
per quelli che verranno scritti domani**, che è la proprietà che distingue una
cura strutturale da una toppa.

Perché conta: un gate anti-confabulazione che punisce «questo non funziona»
scoraggia esattamente la scrittura più preziosa per una memoria verificata — la
smentita, il limite noto, il non-ancora-fatto. Chi è onesto viene quarantinato
e chi tace no.

⚠️ IL PRESIDIO: la negazione deve essere **locale**. Un fatto lungo che dice
«non è stato rilasciato, ma funziona in produzione» contiene un negatore e
contiene un claim vero, e il claim deve restare visibile — altrimenti basterebbe
un «non» in apertura per spegnere il gate su tutto il resto.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import _l1_warnings


def _layer(prop: str) -> set[str]:
    return {str(w.get("layer")) for w in (_l1_warnings(prop, []) or [])}


#: (affermativo, negato) — l'affermativo DEVE scattare, il negato NO.
COPPIE = [
    ("Il modulo funziona in produzione.",
     "Il modulo NON funziona in produzione."),
    ("Il difetto e' stato risolto.",
     "Il difetto NON e' stato risolto."),
    ("Il sistema e' pronto per la produzione.",
     "Il sistema NON e' pronto per la produzione."),
    ("Il servizio e' sicuro contro SQL injection.",
     "Il servizio NON e' sicuro contro SQL injection."),
    ("La migrazione e' completata.",
     "La migrazione NON e' completata."),
    ("Il modulo e' stato testato.",
     "Il modulo NON e' stato testato."),
    ("Il codice e' documentato.",
     "Il codice NON e' documentato."),
    ("Il processo e' automatizzato.",
     "Il processo NON e' automatizzato."),
    ("La modifica e' stata approvata.",
     "La modifica NON e' stata approvata."),
    ("Il job e' monitorato.",
     "Il job NON e' monitorato."),
]


@pytest.mark.parametrize("affermativo,negato", COPPIE)
def test_la_smentita_non_e_il_claim(affermativo, negato):
    """Il cuore, su tutti i detector insieme: la stessa frase negata non deve
    chiedere la prova di ciò che dichiara di NON aver fatto."""
    assert _layer(affermativo), (
        f"il banco e' vacuo: «{affermativo}» non fa scattare nessun detector")
    assert not _layer(negato), (
        f"«{negato}» e' una smentita e prende {sorted(_layer(negato))}")


def test_la_negazione_in_inglese_vale_quanto_quella_italiana():
    """La superficie dei negatori copre undici lingue dal 2026-08-03: la
    guardia deve usarla, non reimplementarne una inglese."""
    assert _layer("The module works in production.")
    assert not _layer("The module does not work in production.")


def test_una_negazione_che_riguarda_ALTRO_non_spegne_il_gate():
    """IL PRESIDIO. Se bastasse un negatore ovunque nella frase, un «non» in
    apertura zittirebbe qualunque claim venga dopo — la guardia diventerebbe un
    interruttore per chi la conosce."""
    prop = "Il modulo non e' stato rilasciato, ma funziona in produzione."
    assert _layer(prop), (
        "la negazione riguarda il rilascio: il claim sul funzionamento resta")


def test_un_fatto_senza_negazione_non_cambia_comportamento():
    """La non-regressione in una riga: senza negatori, tutto come prima."""
    prop = "Il sistema e' pronto per la produzione ed e' stato testato."
    assert {"L1.11", "L1.15"} <= _layer(prop)
