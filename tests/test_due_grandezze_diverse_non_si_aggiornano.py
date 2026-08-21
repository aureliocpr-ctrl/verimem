"""«1 failed e 11767 passed» ritirato da «8019 warnings»: due misure diverse.

CASO REALE, ws7 il 2026-08-20 alle 19:28. Tre `verimem save` con la STESSA
source e lo stesso topic; il terzo ha ritirato il primo con reason
`same-source evolution`:

    MORTO  (grounding 99.7)  «La cella stampa 1 failed e 11767 passed.»
    VIVO   (grounding 99.8)  «Su b7bc7b77 la cella py3.13 stampa 8019 warnings.»

Non e' un valore che si aggiorna: sono DUE GRANDEZZE della stessa cella, e
perdere la prima significa perdere il verdetto di una serata.

PERCHE' I RAMI CHE C'ERANO NON BASTAVANO. `_entita_diverse` separava gia' due
attributi di uno stesso soggetto (`contrasting_attrs` — «il gate LEGGE in 45 ms»
contro «il gate SCRIVE in 300 ms»), ma quella superficie lavora sui
`content_tokens` e `passed`/`warnings` non vi risultano contrastanti. Le UNITA'
delle quantita' invece li separano, e l'estrattore esisteva gia':

    extract_quantities(«...1 failed e 11767 passed»)  -> {('failed',1.0), ('passed',11767.0)}
    extract_quantities(«...8019 warnings»)            -> {('warning', 8019.0)}

IL CONTROLLO E' OBBLIGATORIO QUANTO IL CASO: se le unita' si INTERSECANO e'
lo stesso tipo di misura e l'aggiornamento legittimo deve continuare a ritirare
il vecchio. Una guardia che spegne anche quello e' il difetto gemello.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from verimem.anti_confab_gate import _entita_diverse


def _f(testo: str) -> SimpleNamespace:
    return SimpleNamespace(proposition=testo)


@pytest.mark.parametrize("a, b", [
    # il caso di ws7, verbatim dal corpus
    ("La cella stampa 1 failed e 11767 passed.",
     "Su b7bc7b77 la cella py3.13 stampa 8019 warnings."),
    # stessa forma, in inglese
    ("The cell reports 1 failed and 11767 passed.",
     "The cell reports 8019 warnings."),
    # due grandezze di un processo
    ("Il processo ha 0.40 GB di RSS.",
     "Il processo ha 12 thread."),
])
def test_due_grandezze_diverse_NON_si_aggiornano(a: str, b: str) -> None:
    assert _entita_diverse(_f(a), _f(b)) is True, (
        "due misure di grandezze diverse sono state trattate come un valore "
        "che si aggiorna: la seconda ritira la prima e il dato e' perso")


@pytest.mark.parametrize("a, b", [
    # IL CONTROLLO: stessa unita' = stesso tipo di misura = evoluzione legittima
    ("Il paziente Rossi pesa 70 chilogrammi.", "Il paziente Rossi pesa 78 chilogrammi."),
    ("Il file pesa 10 MB.", "Il file pesa 12 MB."),
    ("The file weighs 10 MB.", "The file weighs 12 MB."),
])
def test_CONTROLLO_stessa_unita_resta_una_evoluzione(a: str, b: str) -> None:
    assert _entita_diverse(_f(a), _f(b)) is False, (
        "la guardia ha spento un aggiornamento legittimo: stessa unita' vuol "
        "dire stesso tipo di misura, e il valore nuovo deve ritirare il vecchio")
