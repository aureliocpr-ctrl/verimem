"""L'anno di «March 12, 2027» non è la quantità 2027 — e finché lo è, copre.

Misurato il 28/08 alla porta SDK, A/B a variabile singola (stessa fonte, stesso
modello di frase, cambia **solo** la cifra). Il claim è **inventato in tutti i
casi**: la fonte non parla di unità di prodotto::

    fonte: «The delivery deadline is March 12, 2027. The review meeting is
            scheduled for July 4, 2031. …»
    claim: «The contract covers N units of product.»

    N = 2027, 2031   ->  AMMESSO 99.9 / 96.2      ·  L4.1 muto  0/2
    N = 2044, 1987, 3129 ->  quarantinato          ·  L4.1 parla 3/3

⇒ `_DATA_RE` cattura «March 12» **ma non l'anno**, quindi `2027` esce dalla
soppressione e finisce fra le quantità **senza unità**, indistinguibile da
qualunque altro numero nudo.

È lo **stesso meccanismo** dei numeri d'articolo (`Art. 4` → `('', 4.0)`,
curato in `29ab5544`), e la stessa famiglia degli anni nudi che il modulo già
esclude: **un numero che fa parte di una DATA non è una grandezza misurata.**

⚠️ In italiano il difetto non si vedeva: «al 12 marzo 2027» ha l'anno preceduto
dal mese, e la guardia `_introdotto_da_una_parola_temporale` lo escludeva già.
In inglese l'anno segue «12,» — un numero, non una parola temporale — e passa.
**Il difetto era invisibile nella lingua in cui misuravamo di più.**
"""

from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities

FONTE_EN = (
    "The delivery deadline is March 12, 2027. "
    "The review meeting is scheduled for July 4, 2031. "
    "The late-delivery penalty is 2% of the contract value per week. "
    "The contract value is 148000 euro."
)


def _nudi(testo: str) -> set[float]:
    return {v for u, v in extract_quantities(testo, come_fonte=True) if not u}


@pytest.mark.parametrize("anno", [2027.0, 2031.0])
def test_l_anno_di_una_data_inglese_non_e_una_quantita(anno: float) -> None:
    assert anno not in _nudi(FONTE_EN), (
        f"«…, {anno:g}» fa parte di una data: se resta una quantita' nuda, un "
        f"claim che inventa {anno:g} risulta sostenuto dalla fonte")


@pytest.mark.parametrize("testo", [
    "The deadline is March 12, 2027.",
    "The deadline is 12 March 2027.",
    "Il termine e' fissato al 12 marzo 2027.",
    "Scadenza 1° marzo 2027.",
])
def test_le_forme_di_data_non_lasciano_l_anno_nudo(testo: str) -> None:
    assert 2027.0 not in _nudi(testo), f"«{testo}» non contiene la quantita' 2027"


# ── ciò che NON deve cambiare ────────────────────────────────────────────
def test_le_quantita_con_unita_restano() -> None:
    q = extract_quantities(FONTE_EN, come_fonte=True)
    assert ("euro", 148000.0) in q


def test_un_anno_che_NON_e_in_una_data_resta_una_quantita() -> None:
    """Il controllo che deve poter fallire: la potatura non deve mangiare ogni
    numero di quattro cifre, altrimenti cura un falso negativo aprendone uno
    molto più grande."""
    assert 2027.0 in _nudi("The total is 2027.")
    assert 3129.0 in _nudi("The total is 3129.")


def test_una_quantita_accanto_a_una_data_resta() -> None:
    """«March 12, 2027 … 148000 euro»: la data perde il suo anno, la somma no."""
    q = extract_quantities(
        "Due on March 12, 2027 the party shall pay 148000 euro.",
        come_fonte=True)
    assert ("euro", 148000.0) in q
    assert 2027.0 not in {v for u, v in q if not u}
