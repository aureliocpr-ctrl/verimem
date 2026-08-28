"""«Art. 3» non è la quantità 3 — e finché lo è, copre un numero inventato.

Misurato il 28/08 sulla porta SDK, A/B a variabile singola (stessa fonte,
stesso modello di frase, cambia **solo** la cifra)::

    fonte: un contratto con Art. 3 .. Art. 8
    claim: «Il numero di rate previste dal contratto e' N»   (la fonte NON
                                                              parla di rate)

    N = 3, 6, 8   ->  AMMESSO 100.0 / 100.0 / 96.2   ·  L4.1 muto  0/3
    N = 91, 97, 43 -> quarantinato 0.2 ovunque       ·  L4.1 parla 3/3

⇒ la numerazione degli articoli **inocula sé stessa** come valore valido della
fonte: `extract_quantities` legge «Art. 4 - … 5%» come ``[('', 4.0), ('', 5.0)]``
e il 4 diventa indistinguibile da una quantità. Qualunque documento a sezioni
numerate — contratti, leggi, regolamenti, protocolli, norme tecniche —
immunizza i propri numeri di sezione, e l'intervallo coperto (2..8) è **quello
più usato nei claim ordinari**: «3 rate», «6 mesi», «5 giorni».

È la stessa famiglia degli anni nudi, che il modulo già esclude: un numero che
**nomina** una parte del documento non è una grandezza misurata.
"""

from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities

CONTRATTO = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 5%. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)


def _nudi(testo: str) -> set[float]:
    return {v for u, v in extract_quantities(testo, come_fonte=True) if not u}


@pytest.mark.parametrize("n", [3.0, 4.0, 7.0, 8.0])
def test_il_numero_dell_articolo_non_e_una_quantita(n: float) -> None:
    assert n not in _nudi(CONTRATTO), (
        f"«Art. {n:g}» non e' la quantita' {n:g}: se lo diventa, un claim che "
        f"inventa {n:g} risulta sostenuto dalla fonte")


@pytest.mark.parametrize("testo", [
    "Art. 5 - Il termine e' fissato.",
    "Articolo 5 del regolamento.",
    "comma 5 della norma citata.",
    "Sez. 5 del capitolato.",
    "punto 5 dell'ordine del giorno.",
    "Allegato 5 al contratto.",
    "Section 5 of the agreement.",
    "clause 5 of the contract.",
    "paragraph 5 states otherwise.",
    "Annex 5 lists the exclusions.",
    "Table 5 reports the totals.",
])
def test_le_forme_di_riferimento_non_producono_quantita(testo: str) -> None:
    assert 5.0 not in _nudi(testo), f"«{testo}» non contiene la quantita' 5"


# ── ciò che NON deve cambiare ────────────────────────────────────────────
def test_le_quantita_con_unita_restano() -> None:
    q = extract_quantities(CONTRATTO, come_fonte=True)
    assert ("euro", 148000.0) in q
    assert ("euro", 22000.0) in q


def test_un_numero_nudo_senza_riferimento_resta_una_quantita() -> None:
    """Il controllo che deve poter fallire: la potatura non deve mangiare i
    numeri nudi ordinari, altrimenti cura il falso negativo creando un buco
    molto più grande."""
    assert 3.0 in _nudi("Le rate previste sono 3.")
    assert 12.0 in _nudi("I file interessati sono 12.")


def test_una_quantita_che_segue_un_riferimento_resta() -> None:
    """«comma 2 prevede 5 giorni»: il 2 è un riferimento, il 5 una quantità.

    ⚠️ RESIDUO DICHIARATO, misurato scrivendo questo test: qui il 2 **non**
    viene potato, perché acquisisce l'unità fasulla ``prevede`` — la parola che
    lo segue — e la potatura agisce solo sul numero **nudo**. Non riapre il
    difetto curato (un claim che inventa un «2» nudo non trova ``('prevede',
    2.0)``), ma l'estrazione resta sbagliata: ``prevede`` non è un'unità, e
    ``_NON_UNIT_WORDS`` non lo contiene. È un difetto **adiacente**, non questo.
    """
    q = extract_quantities("Il comma 2 prevede 5 giorni di preavviso.",
                           come_fonte=True)
    assert ("giorno", 5.0) in q, "l'unità è normalizzata al singolare"
    assert 2.0 not in {v for u, v in q if not u}, (
        "il 2 del comma non deve restare un numero NUDO: è così che copriva "
        "un numero inventato")
