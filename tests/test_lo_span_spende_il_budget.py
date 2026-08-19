"""Lo span deve SPENDERE il budget che dichiara.

`select_relevant_span` ordina le unita' per somiglianza lessicale col claim e le
prende finche' c'e' posto. Fermarsi alla PRIMA che non entra scarta anche tutte
le successive piu' CORTE — e le righe di DATI (numeri, poche parole) stanno in
fondo al ranking proprio perche' lessicalmente non somigliano a niente.

Il costo, misurato il 19/08 sul corpus servito: span mediano 206 caratteri fra i
quarantinati e 332 fra gli ammessi, con ZERO span su 2.812 che arrivano a 1400 —
su un `focus_budget` dichiarato di 1500. Il budget non era troppo grande ne'
troppo piccolo: non veniva speso.

Il difetto NON si vede dal punteggio del moat (99.982 con e senza la riga di
dati): si vede da `L4.1`, che chiede allo SPAN se contiene i numeri del claim e
segnala come "non nella fonte" valori che nella fonte c'erano.
"""
from __future__ import annotations

import pytest

from verimem.grounding_gate import select_relevant_span
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

_PROSA = "\n".join(
    f"La misurazione numero {i} e' stata eseguita sul corpus in condizioni stabili "
    f"e il risultato e' stato registrato dal banco automatico."
    for i in range(1, 21)
)
_DATI = "\n".join(
    f"riga{i:02d}   {1000 + i * 7}   {i * 3}.{i}%   {i * 11}" for i in range(1, 21)
)
FONTE = _PROSA + "\n" + _DATI
BUDGET = 1500


def test_lo_span_non_si_ferma_alla_prima_riga_che_non_entra() -> None:
    """Con righe corte ancora disponibili, lo span deve avvicinarsi al budget."""
    span = select_relevant_span(FONTE, "il valore 1077 e la percentuale 33.11", budget=BUDGET)
    scarto = BUDGET - len(span)
    riga_piu_corta = min(len(r) for r in FONTE.splitlines() if r.strip())
    assert scarto < riga_piu_corta, (
        f"lo span lascia {scarto} caratteri liberi ma la riga piu' corta ne occupa "
        f"{riga_piu_corta}: almeno una riga entrerebbe ancora"
    )


def test_il_numero_che_il_claim_afferma_entra_nello_span() -> None:
    """Il caso reale: la prova sta in una riga di dati, che il ranking mette in fondo."""
    claim = "La misurazione ha dato il valore 1077 e la percentuale 33.11 per cento."
    span = select_relevant_span(FONTE, claim, budget=BUDGET)
    assert "1077" in span and "33.11" in span


def test_l4_1_non_accusa_un_fatto_vero_di_avere_numeri_inventati() -> None:
    """La conseguenza che costa: il fatto e' vero, la fonte lo contiene, e il
    giudice riceve uno span da cui il numero e' stato escluso."""
    claim = "La misurazione ha dato il valore 1077 e la percentuale 33.11 per cento."
    span = select_relevant_span(FONTE, claim, budget=BUDGET)
    assert valori_non_nella_fonte(claim, span) == []


@pytest.mark.parametrize("claim", [
    "La misurazione numero 7 e' stata eseguita in condizioni stabili.",
    "Il risultato e' stato registrato dal banco automatico.",
    "La misurazione numero 19 e' stata eseguita sul corpus.",
])
def test_i_fatti_sostenuti_dalla_prosa_restano_puliti(claim: str) -> None:
    """I tre SANI: la cura non deve cambiare cio' che gia' funzionava."""
    span = select_relevant_span(FONTE, claim, budget=BUDGET)
    assert valori_non_nella_fonte(claim, span) == []


def test_un_numero_davvero_assente_resta_segnalato() -> None:
    """Il controllo che puo' fallire: una cura che allarga lo span non deve
    zittire L4.1. Se questo diventa verde, il veto e' stato aperto."""
    falso = "La misurazione ha dato il valore 9999 e la percentuale 88.88 per cento."
    span = select_relevant_span(FONTE, falso, budget=BUDGET)
    segnalati = {v.come_scritto() for v in valori_non_nella_fonte(falso, span)}
    assert {"9999", "88.88"} <= segnalati
