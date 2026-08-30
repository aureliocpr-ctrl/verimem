"""La terza potatura stava FUORI dall'esenzione `come_fonte`, e ha accecato la fonte.

CRONACA. `extract_quantities(text, *, come_fonte=False)` ha un bivio solo, e la
sua docstring lo dichiara col NUMERO: «``come_fonte=True`` legge il testo
INTERO, saltando **le due** potature». Le due sono `claim_span` e
`_senza_identificatori`, e stanno entrambe sulla riga del bivio::

    claim = text if come_fonte else _senza_identificatori(claim_span(text))
    _date = _spans_delle_date(claim)
    _riferimenti = _spans_dei_riferimenti(claim)   # <-- la TERZA, SOTTO il bivio

Il 28/08 (`29ab5544`) ho aggiunto `_spans_dei_riferimenti` — «art. 3 non e' la
quantita' 3» — **due righe sotto il bivio**, quindi fuori dall'esenzione: si
applicava identica in entrambe le modalita'. Misurato il 30/08 sugli otto casi
del presidio del 07/08: **5/8 come CLAIM e 5/8 come FONTE**, cioe' `art.15`,
`pag.7` e `fig.3` invisibili **anche a chi sa di avere una fonte fra le mani** —
dove quel numero c'e' davvero, e il claim che lo cita non se lo sta inventando.

🔑 LA LEZIONE ERA NEL COMMENTO, E NOMINAVA IL NUMERO. «Le due potature»: chi
aggiunge la terza deve dirlo al bivio, o l'esenzione smette di essere completa
senza che nessuna riga diventi rossa. Sei moduli del gate leggono questa
funzione — contare le porte veniva prima di aprirne una nuova.

⚠️ E QUESTO PRESIDIO MISURA ENTRAMBE LE POPOLAZIONI, perche' una sola non
distingue la cura dall'annullamento della cura precedente:

    [1] lato FONTE  — i numeri dopo un riferimento DEVONO tornare visibili
    [2] lato CLAIM  — e la potatura del 28/08 DEVE restare in piedi

Se passasse solo [1], avrei «curato» rimuovendo `_spans_dei_riferimenti`, che e'
la regressione opposta. Se passasse solo [2], la cura non c'e'.
"""

from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities

#: gli otto casi del presidio del 07/08 (`test_grad_3_era_invisibile...`).
#: In una FONTE ognuno di questi numeri e' presente: leggerlo e' il mestiere.
DOPO_UNA_ABBREVIAZIONE = [
    ("grad.3", 3.0),
    ("temp.22", 22.0),
    ("l'art.15 del codice", 15.0),
    ("vedi pag.7", 7.0),
    ("il n.42 del registro", 42.0),
    ("tot.300 pezzi", 300.0),
    ("fig.3", 3.0),
    ("Nr.5 im Lager", 5.0),
]

#: i tre che `29ab5544` ha voluto rendere muti NEL CLAIM: li' «art. 15» e'
#: un puntatore a una norma, non un valore misurato da confrontare con la fonte.
SOLO_PUNTATORI_NEL_CLAIM = [
    "l'articolo 15 del codice prevede la penale",
    "vedi pagina 7 del manuale",
    "come mostra la figura 3",
]


def _valori(testo: str, *, come_fonte: bool) -> set[float]:
    return {v for _u, v in extract_quantities(testo, come_fonte=come_fonte)}


# ------------------------------------------------- [1] IL LATO FONTE, IL BUCO --
@pytest.mark.parametrize("frase,valore", DOPO_UNA_ABBREVIAZIONE)
def test_una_fonte_vede_il_numero_dopo_un_riferimento(frase: str, valore: float):
    """IL CUORE. Chi chiede `come_fonte=True` SA di avere una fonte davanti e
    vuole leggerla per intero. Un numero che li' c'e' deve risultare presente,
    o il claim che lo cita sembra inventarselo e viene quarantinato da vero."""
    visti = _valori(frase, come_fonte=True)
    assert valore in visti, (
        f"«{frase}» come FONTE -> {visti or 'set()'}: il numero e' NEL testo e "
        f"la lettura-fonte non lo vede. E' il buco che `29ab5544` ha aperto "
        f"mettendo la terza potatura sotto il bivio invece che sopra."
    )


# --------------------------------- [2] LA POPOLAZIONE OPPOSTA: LA CURA REGGE --
@pytest.mark.parametrize("claim", SOLO_PUNTATORI_NEL_CLAIM)
def test_un_claim_non_afferma_il_numero_del_proprio_riferimento(claim: str):
    """L'ALTRA META', senza la quale la prima si soddisfa cancellando la cura.
    In un CLAIM «l'articolo 15» non afferma la quantita' 15: e' un puntatore, e
    contestarlo alla fonte produceva la quarantena di fatti veri."""
    visti = _valori(claim, come_fonte=False)
    assert not visti, (
        f"«{claim}» come CLAIM -> {visti}: il numero di un riferimento e' "
        f"tornato a essere un'affermazione quantitativa; `29ab5544` e' annullata."
    )


def test_il_bivio_separa_le_due_letture():
    """La riga di sintesi che rende leggibile un rosso parziale: senza questa,
    «5/8» e «8/8» si distinguono solo leggendo otto righe di parametrizzazione."""
    come_fonte = sum(v in _valori(f, come_fonte=True)
                     for f, v in DOPO_UNA_ABBREVIAZIONE)
    come_claim = sum(not _valori(c, come_fonte=False)
                     for c in SOLO_PUNTATORI_NEL_CLAIM)
    assert (come_fonte, come_claim) == (len(DOPO_UNA_ABBREVIAZIONE),
                                        len(SOLO_PUNTATORI_NEL_CLAIM)), (
        f"fonte {come_fonte}/{len(DOPO_UNA_ABBREVIAZIONE)} · "
        f"claim {come_claim}/{len(SOLO_PUNTATORI_NEL_CLAIM)}"
    )
