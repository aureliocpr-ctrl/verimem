"""Un marcatore di osservazione non chiude la via di ammissione delle prove indipendenti.

LIVELLO: funzione pubblica `advisory_eligible` (anti_confab_gate.py), letta dal
write path a `if l1_escalates and documents is not None and
advisory_eligible(warnings)`. Alla porta il caso esige il rilevatore semantico
in modo observe (che emette `L3-semantic-observe` PRIMA di quella riga), uno
store di documenti e un `verified_by` indipendente: costruibile, ma carica il
giudice, e la domanda qui e' puramente lessicale. Il presidio sta alla
funzione, ed e' dichiarato.

Contesto (2026-09-03). ws7, falsificando la cura 0cec6422 (anello ④), ha
trovato che la dichiarazione «gli altri punti `startswith("L1")` non cambiano
un verdetto per il solo marcatore» era falsa in UN punto: `advisory_eligible`
ha semantica ALL («True iff EVERY warning is from the L1 lexical family»), e
un marcatore di osservazione NON-L1 gia' nei warnings — `L3-semantic-observe`
nasce a monte della chiamata — la fa rispondere False. Un marcatore che per
convenzione e' «surfaced, never a block reason» chiudeva cosi' una via di
AMMISSIONE. Predizione depositata prima di misurare (lead, 19:44):
«advisory_eligible([L1.10, L3-semantic-observe]) oggi = False». Confermata.

La cura: la funzione guarda solo gli avvisi che possono decidere, cioe'
scarta i layer advisory con la stessa superficie unica (`_is_advisory_layer`)
usata da `_blocking_layers` e da `chi_ha_quarantinato`. Corollario dichiarato:
una ricevuta fatta di SOLI marcatori non ha «una storia L1 da rilassare» e
risponde False, come la ricevuta vuota — prima rispondeva True per
`L1-domain-advisory-observe` da solo.
"""
from __future__ import annotations

from verimem.anti_confab_gate import advisory_eligible


def _ws(*layers: str) -> list[dict]:
    return [{"layer": layer} for layer in layers]


def test_un_marcatore_non_l1_non_chiude_la_via():
    """Il cuore: `L3-semantic-observe` accanto a un L1 vero non toglie a L1 il
    ruolo di «tutta la storia»."""
    assert advisory_eligible(_ws("L1.10", "L3-semantic-observe")) is True
    assert advisory_eligible(_ws("L1.10", "L1.15", "L3-supersession-observe")) is True


def test_un_marcatore_l1_non_aggiunge_niente():
    assert advisory_eligible(_ws("L1.10", "L1-domain-precision-observe")) is True


def test_CONTROLLO_un_l3_vero_chiude_ancora():
    """La popolazione opposta: un layer semantico VERO resta parte della storia,
    e con lui L1 non e' piu' tutta la storia. Senza questa cella una cura che
    ignorasse l'intera famiglia L3 passerebbe i test sopra."""
    assert advisory_eligible(_ws("L1.10", "L3-contradiction")) is False
    assert advisory_eligible(_ws("L1.10", "L4-grounding")) is False


def test_soli_marcatori_equivalgono_a_nessuna_storia():
    """Corollario dichiarato nel docstring del modulo: senza un avviso L1 vero
    non c'e' niente da rilassare, come per la ricevuta vuota."""
    assert advisory_eligible([]) is False
    assert advisory_eligible(_ws("L1-domain-advisory-observe")) is False
    assert advisory_eligible(_ws("L3-semantic-observe")) is False
