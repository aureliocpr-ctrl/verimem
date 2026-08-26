r"""Una falsità accompagnata da una verità PRESA DALLA FONTE entra a 100.

Il giudice premia la SOVRAPPOSIZIONE con la fonte, non l'implicazione della
frase intera. Misurato alla porta (`run_validation_gate`), fuori da pytest, con
la fonte fissa e una sola variabile per riga::

    fonte «test_alpha PASSED / test_beta SKIPPED»
    falsità fissa: «il test_beta è PASSED» (la fonte dice SKIPPED)

    da sola ................................. downgrade  g=  3.3   bloccata
    + verità DALLA FONTE, prima ............. persist    g=100.0   AMMESSA
    + verità DALLA FONTE, dopo .............. persist    g=100.0   AMMESSA
    + verità DALLA FONTE, ai lati ........... persist    g=100.0   AMMESSA
    + verità NON dalla fonte («Roma è in Italia»)   downgrade g=0.7  bloccata
    + verità generica («due più due fa quattro»)    downgrade g=1.2  bloccata

⇒ Tre ammesse e tre bloccate: la variabile che le separa è **da dove viene la
verità che accompagna**. Una verità qualunque non salva niente; una presa dalla
fonte sì.

⚠️ IL CASO PEGGIORE NON È QUESTO, ed è in un altro dominio::

    fonte  «Il magazzino di Ancona misura 2600 mq. Il responsabile è Mancini.»
    claim  «Il responsabile è Mancini e il magazzino di BOLOGNA misura 2600 mq.»
    -> persist, g=92.3

La metratura di Ancona attribuita a Bologna: una **sostituzione di entità**, la
forma classica della confabulazione, che è esattamente ciò per cui il gate
esiste. Si salda col fatto `0b7fa9a222d1` (17/08): «sostituzioni di entità
ammesse: 3 su 7» — allora se ne conosceva il numero, adesso il meccanismo.

⚖️ PERCHÉ xfail(strict) E NON UNA CURA. La causa è nel CE: il punteggio misura
quanto il claim ATTINGE dalla fonte, non quanto la fonte lo IMPLICA, e le due
cose divergono appena la frase contiene più di un'affermazione. Curarlo vuol
dire toccare il giudice, e questo file non lo fa. Quando qualcuno lo cura, gli
xfail diventano XPASS e la suite chiede di togliere il marcatore: il difetto fa
rumore quando SMETTE di esistere.

📌 Una differenza NON spiegata, e la dichiaro invece di tacerla: nel dominio dei
test la falsità passa anche con un valore che nella fonte non c'è affatto
(«novemila righe», 99.9), nei magazzini no (4200 mq, 0.2). La regola della
sovrapposizione spiega i casi ammessi in entrambi i domini, non questa
asimmetria residua.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import run_validation_gate

SRC_TEST = "   test_alpha PASSED\n   test_beta SKIPPED"
SRC_MAG = "Il magazzino di Ancona misura 2600 mq. Il responsabile e' Mancini."


def _bloccato(claim: str, source: str) -> bool:
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=source, grounding_llm=None,
                            ground_write=True)
    return getattr(r, "action", "?") != "persist"


def test_presidio_la_falsita_DA_SOLA_e_bloccata():
    """La controparte necessaria: senza di lei non si distingue «il gate non
    vede questa falsità» da «il gate non vede le falsità»."""
    assert _bloccato("Il test_beta e PASSED.", SRC_TEST)
    assert _bloccato("Il magazzino di Bologna misura 2600 mq.", SRC_MAG)


def test_presidio_una_verita_NON_dalla_fonte_non_salva_la_falsita():
    """L'altra metà del criterio: accompagnare con una verità qualunque non
    basta. È questa riga che rende «la verità viene DALLA FONTE» una causa e
    non una coincidenza."""
    assert _bloccato("Roma e in Italia e il test_beta e PASSED.", SRC_TEST)
    assert _bloccato("Due piu due fa quattro e il test_beta e PASSED.", SRC_TEST)


@pytest.mark.xfail(strict=True, reason=(
    "il giudice premia la sovrapposizione con la fonte: una verita' presa da li' "
    "porta dentro la falsita' che le sta accanto (misurato: 100.0)"))
def test_una_verita_dalla_fonte_non_deve_far_passare_la_falsita():
    assert _bloccato("Il test_alpha e PASSED e il test_beta e PASSED.", SRC_TEST)


@pytest.mark.xfail(strict=True, reason=(
    "sostituzione di entita' ammessa a 92.3: la metratura di Ancona attribuita "
    "a Bologna, accompagnata da una verita' presa dalla fonte"))
def test_una_sostituzione_di_entita_non_deve_passare_in_compagnia():
    assert _bloccato(
        "Il responsabile e' Mancini e il magazzino di Bologna misura 2600 mq.",
        SRC_MAG)
