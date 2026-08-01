"""Il consiglio «spezza» sta su L4, e a trattenere il backlog sono gli L1.

Misurato sul corpus vivo 2026-07-30, sui 513 quarantinati:

    quante affermazioni contiene un fatto trattenuto
      1        48   ( 9%)
      2-3      80   (16%)
      4-9     156   (30%)
      10+     230   (45%)      lunghezza mediana 852 char

Il 91% ne contiene piu' di una, il 45% dieci o piu'. Non sono fatti respinti
ingiustamente: sono NARRAZIONI DI SESSIONE che il gate valuta come un blocco
unico, e un blocco con dieci affermazioni chiede dieci evidenze.

E infatti a trattenerli non e' il moat ma i detector lessicali — rieseguendo il
gate con l'evidenza citata spostata in verified_by, dei 164 che ne citano una
42 passano e 122 restano fermi su:

    L1.13  53   completion claim senza closing criteria
    L1.15  35
    L1.10  22   works/confirmed claim senza runtime evidence
    L1.12  22   + L1.9, L1.5, L1.14, L1.11

lo stesso fatto ne accende piu' di uno insieme. Il consiglio che risolve il 91%
dei casi — «contiene N affermazioni, spezzala» — l'ho cablato ieri sul solo L4.
Qui manca, ed e' dove serve.
"""
from __future__ import annotations

import pytest

MULTI = (
    "SELF-IMPROVE CYCLE #2 COMPLETO 2026-05-12: bug strutturale in "
    "corpus_health_score risolto, la suite e' verde, e il rilascio e' stato "
    "consegnato al cliente mentre il monitoraggio resta osservato."
)
SINGOLO = "Il rilascio 0.8.0 e' stato completato."


def _warn(prop: str):
    from verimem.l1_completion_detector import detect_unsupported_completion_claim
    return detect_unsupported_completion_claim(proposition=prop, verified_by=[])


def test_a_multi_claim_proposition_is_told_to_split():
    w = _warn(MULTI)
    assert w is not None, "il detector non e' scattato sul caso multi-claim"
    assert "affermazioni" in w.advice or "assertions" in w.advice, (
        f"il consiglio non dice che il fatto contiene piu' affermazioni:\n{w.advice}"
    )


def test_the_advice_still_lists_the_evidence_forms():
    """Non sostituisce il consiglio esistente: lo affianca."""
    w = _warn(MULTI)
    assert "pytest:" in w.advice and "task:" in w.advice, w.advice


def test_a_single_claim_is_not_told_to_split():
    """Dire «spezza» a una frase che dice una cosa sola e' rumore, e il rumore
    e' come la meta' utile di un messaggio smette di essere letta."""
    w = _warn(SINGOLO)
    assert w is not None
    assert "affermazioni" not in w.advice and "assertions" not in w.advice, w.advice


def test_the_verdict_does_not_change():
    """Questo e' un consiglio, non un cancello: chi non ha l'evidenza resta
    trattenuto esattamente come prima."""
    with_ev = None
    from verimem.l1_completion_detector import detect_unsupported_completion_claim
    with_ev = detect_unsupported_completion_claim(
        proposition=MULTI, verified_by=["pytest:suite_PASS"])
    assert with_ev is None, "l'evidenza valida deve continuare a far passare"
    assert _warn(MULTI) is not None, "senza evidenza deve continuare a fermare"


@pytest.mark.parametrize("prop", ["", None])
def test_empty_input_is_still_no_warning(prop):
    assert _warn(prop) is None
