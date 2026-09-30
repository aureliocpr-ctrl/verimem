"""T188 — `2.5e-3` diventa due numeri, e uno dei due non esiste.

⚠️ QUESTA CELLA ERA ROSSA SUL TRONCO `42a09da9` (22/09) E LO È ANCORA su `46f250e3`
(30/09, misurato: accuse [2.5, 3.0]). La cura va nel PARSER (la strada c del 22/09),
dopo T223 che tocca lo stesso file, e vale per le sole forme che non si confondono.

IL PERIMETRO, deciso col raggio sullo store (30/09, sola lettura: 18476 fatti, 409 con
un token in notazione e, 162 con l'esponente letto come un valore):
  · diventano UN numero le forme con il decimale nella mantissa o il segno
    nell'esponente — `2.5e-3`, `1e-5`, `3E+2`: 24 fatti;
  · le forme NUDE (`1e3`, `4e10`: 386 fatti) restano fuori, come oggi: possono essere
    pezzi di identificativi, e leggere frammenti di SHA come grandezze è una strada
    già falsificata (commento di `_QUANT_RE` in quantity_match.py).

IL CASO. Un claim VERO, con la sua fonte accanto che lo conferma, viene
accusato di due valori che nella frase non ci sono::

    claim  'La soglia e 2.5e-3 metri.'
    fonte  'Verbale: la soglia e 0.0025 metri.'
    accuse [2.5, 3.0]

La causa sta a monte del confronto, nel parser::

    'La soglia e 2.5e-3 metri.'  ->  [('', 2.5), ('metro', 3.0)]
    'Il modulo ha 1e3 utenti.'   ->  NIENTE

`2.5e-3` viene spezzato in `2.5` e `3`, e quel `3` prende per unità la parola
che segue. Entra nel confronto, non si trova nella fonte, e diventa un'accusa.

⚠️ NON È UN BUCO DELLA NOTAZIONE SCIENTIFICA, e la differenza conta perché
indirizza la cura. Il prodotto dichiara il proprio perimetro e lo rispetta::

    _SCIENTIFICA_RE = (\\d{1,15}(?:[.,]\\d{1,15})?)[ \\t]{0,4}[x×*][ \\t]{0,4}10\\^(-?\\d{1,4})
      '1 x 10^3' -> '1000'   ·   '1.5 x 10^6' -> '1500000'   ·   '2 × 10^3' -> '2000'
      '1e3'      -> invariato  (fuori perimetro PER DISEGNO)

La forma `x 10^n` funziona, **e funziona nei due sensi**: è il controllo
positivo di questo file. Il difetto è l'INCOERENZA dentro la notazione `e` —
`1e3` viene ignorato (giusto, per un perimetro che non la copre) e `2.5e-3`
viene letto male. «Non supportato» deve voler dire «non produco quantità»,
non «ne produco due sbagliate»; oggi a separare i due comportamenti è il
punto decimale.

RAGGIO sullo store, misurato il 22/09 e riportato nel messaggio di consegna:
i numeri e i casi stanno lì, perché un raggio senza i casi accanto non si può
contestare.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities
from verimem.valore_non_nella_fonte import valori_non_nella_fonte


def _accuse(claim: str, fonte: str) -> list[float]:
    return sorted({float(getattr(v, "valore", getattr(v, "value", 0)))
                   for v in valori_non_nella_fonte(claim, fonte)})


# ───────────────────────────  il difetto: ROSSO oggi  ────────────────────────

def test_un_claim_vero_in_notazione_e_non_viene_accusato():
    """Il caso che apre T188: la fonte conferma, e il gate accusa lo stesso."""
    accuse = _accuse("La soglia e 2.5e-3 metri.",
                     "Verbale: la soglia e 0.0025 metri.")
    assert accuse == [], (
        f"accusato di {accuse}: la fonte scrive lo STESSO valore in un'altra "
        f"grafia, e il 3.0 non esiste nemmeno nella frase")


def test_il_parser_non_spezza_la_notazione_in_due_numeri():
    """La causa, un passo più a monte: `2.5e-3` è UN numero, non due.

    Il `3` che esce da qui è quello che poi diventa l'accusa sopra, e si porta
    dietro come unità la parola che segue.
    """
    quantita = extract_quantities("La soglia e 2.5e-3 metri.")
    valori = sorted(v for _, v in quantita)
    assert 3.0 not in valori, (
        f"{quantita}: l'esponente è diventato una quantità a sé, con l'unità "
        f"della parola che segue")


def test_accusare_per_il_motivo_sbagliato_non_e_accusare():
    """⚠️ Il caso che sembra funzionare e non funziona.

    Qui il claim è FALSO (la fonte dice 9.9) e il gate accusa — ma accusa
    `[2.5, 3.0]`, cioè i due pezzi della grafia spezzata, non il valore
    contestato. Un'accusa giusta per caso resta una diagnosi sbagliata, e
    chi legge la ricevuta va a cercare un `3` che non c'è.
    """
    accuse = _accuse("La soglia e 2.5e-3 metri.",
                     "Verbale: la soglia e 9.9 metri.")
    assert 3.0 not in accuse, (
        f"accuse {accuse}: il claim è falso davvero, ma il valore accusato è "
        f"un pezzo della notazione, non la misura")


# ────────────────  il CONTROLLO POSITIVO: la forma supportata  ───────────────

@pytest.mark.parametrize("claim, fonte", [
    ("La soglia e 2.5 x 10^-3 metri.", "Verbale: la soglia e 0.0025 metri."),
    ("La soglia e 0.0025 metri.", "Verbale: la soglia e 2.5 x 10^-3 metri."),
])
def test_la_forma_supportata_funziona_nei_due_sensi(claim, fonte):
    """⚠️ Senza queste due righe, i tre rossi sopra si potrebbero «curare»
    spegnendo il confronto, e nessuno se ne accorgerebbe.

    `x 10^n` è il perimetro dichiarato: qui deve tacere, e in ENTRAMBI i sensi
    — claim esteso contro fonte scientifica e viceversa.
    """
    assert _accuse(claim, fonte) == [], claim


def test_un_valore_che_la_fonte_non_contiene_resta_accusato():
    """Il secondo controllo positivo: il modulo deve ancora accusare."""
    accuse = _accuse("La soglia e 9999 metri.",
                     "Verbale: la soglia e 0.0025 metri.")
    assert 9999.0 in accuse, (
        f"accuse {accuse}: il modulo non accusa più un valore assente, quindi "
        f"non sta misurando niente")


# ─────────  le forme che non si confondono: UN numero, nel parser  ─────────

@pytest.mark.parametrize("frase, valore", [
    ("La soglia e 2.5e-3 metri.", 0.0025),
    ("La soglia e 2,5e-3 metri.", 0.0025),
    ("La perdita e 1e-5 grammi.", 0.00001),
    ("La portata e 3E+2 litri.", 300.0),
])
def test_la_notazione_e_non_ambigua_e_un_numero_solo(frase, valore):
    """Il decimale nella mantissa o il segno nell'esponente dicono che e' un numero:
    il parser deve restituirne UNO, con il suo valore, e nessun pezzo."""
    valori = sorted(v for _, v in extract_quantities(frase))
    assert len(valori) == 1 and abs(valori[0] - valore) < 1e-12, (
        f"{frase!r} -> {valori}: atteso un valore solo, {valore}")


@pytest.mark.parametrize("claim, fonte", [
    ("La portata e 3E+2 litri.", "Verbale: la portata e 300 litri."),
    ("La portata e 300 litri.", "Verbale: la portata e 3E+2 litri."),
])
def test_la_notazione_e_e_la_forma_estesa_sono_lo_stesso_numero(claim, fonte):
    """Come per `x 10^n`, nei due sensi: la grafia non e' un'accusa."""
    assert _accuse(claim, fonte) == [], claim


# ──────────  il PERIMETRO: le forme nude restano fuori, e lo si presidia  ──────────

@pytest.mark.parametrize("frase", [
    "Il modulo ha 1e3 utenti.",
    "La build 4518e290 e' verde.",
])
def test_le_forme_nude_restano_fuori_perimetro(frase):
    """⚠️ GUARDIA, verde gia' oggi: una forma nuda puo' essere un identificativo
    (uno SHA fatto di cifre e di una sola «e»), e la cura non deve cominciare a
    leggerla come grandezza. Se un giorno lo si vorra', si misura prima."""
    assert extract_quantities(frase) == set(), (
        f"{frase!r} -> {extract_quantities(frase)}: una forma nuda e' diventata una grandezza")
