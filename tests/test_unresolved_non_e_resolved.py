"""«unresolved» faceva scattare il detector dei claim di fix, che cerca RESOLVED.

TROVATO ripristinando a mano dodici fatti che la supersessione aveva ingoiato
(2026-08-04). Tolti dal ritiro, restavano invisibili per un secondo motivo: la
quarantena. Leggendoli uno per uno, **sei su sei erano falsi positivi**, e due
per questa causa:

    «…riporta due blocchi DISPUTED unresolved con lo stesso record in conflitto»
        -> L1.8: FIX-family claim 'RESOLVED' lacks an evidence ref

Il fatto dice che due conflitti sono **NON risolti**, e il detector lo legge
come se qualcuno dichiarasse di averli risolti. Il docstring del modulo lo
dichiara senza saperlo: «``proposition.upper()`` contains a FIX_KEYWORDS entry
(**substring**)» — e `UNRESOLVED` contiene `RESOLVED`.

È il caso peggiore per un gate anti-confabulazione: non lascia passare una
millanteria, **blocca la sua smentita**. Chi scrive «il problema non è risolto»
si vede chiedere la prova di averlo risolto.

LA CURA C'ERA GIÀ NEL REPO, in un fratello di questo detector:
`l1_tested_detector._has_tested_evidence` confronta **per token** e non per
sottostringa, e il commento accanto spiega perché — «così `test:greenfield` /
`review:approvable_pending` non contano per via di una sottostringa
accidentale» (audit del 2026-06-02). La stessa precauzione non era mai stata
portata sul lato della PROPOSIZIONE. È la classe «la cura c'era e mancava lo
sweep», che questo progetto ha già pagato più volte.

⚠️ IL CONFINE DI PAROLA NON BASTA DA SOLO, e per questo il test guarda anche
il verso opposto: `FIXED`, `RESOLVED`, `PATCHED` e `REPAIRED` come parole
intere devono continuare a far scattare il detector, altrimenti la cura non
sarebbe una correzione ma uno spegnimento.
"""
from __future__ import annotations

import pytest

from verimem.l1_extended_detector import detect_unsupported_fix_claim

#: La parola NEGATA, o inglobata in un'altra: non è un claim di fix.
NON_SONO_CLAIM = [
    "Nella risposta l'esca riporta due blocchi DISPUTED unresolved.",
    "Lo stato della contraddizione e' unresolved e va rivisto a mano.",
    "Il conteggio mostra 87498 contraddizioni unresolved nel corpus.",
    "La colonna resolved_at e' NULL per tutte le righe.",
]

#: I claim veri: devono continuare a chiedere la prova.
SONO_CLAIM = [
    "Ho RESOLVED la race condition nel daemon.",
    "Il bug del parser e' FIXED da stamattina.",
    "La vulnerabilita' e' stata PATCHED nella release.",
    "Il modulo danneggiato e' REPAIRED e funziona.",
]


@pytest.mark.parametrize("prop", NON_SONO_CLAIM)
def test_una_parola_negata_non_e_una_dichiarazione_di_fix(prop):
    """Il cuore: `unresolved` è il CONTRARIO di `resolved`, e `resolved_at` è
    il nome di una colonna. Un gate anti-confabulazione che blocca la smentita
    di un claim invece del claim lavora esattamente al contrario."""
    assert detect_unsupported_fix_claim(proposition=prop, verified_by=[]) is None, (
        f"«{prop}» non dichiara nessun fix e viene trattata come tale")


@pytest.mark.parametrize("prop", SONO_CLAIM)
def test_i_claim_di_fix_VERI_continuano_a_chiedere_la_prova(prop):
    """IL VERSO OPPOSTO, che rende la cura una correzione e non uno
    spegnimento: la parola intera deve continuare a far scattare il detector.
    La regola nasce dalle confabulazioni pre-merge del 2026-05-17."""
    assert detect_unsupported_fix_claim(proposition=prop, verified_by=[]) is not None, (
        f"«{prop}» dichiara un fix senza prova e non viene piu' vista")


def test_la_prova_continua_a_zittire_il_detector():
    """La porta d'uscita legittima non si tocca."""
    assert detect_unsupported_fix_claim(
        proposition="Ho RESOLVED la race condition.",
        verified_by=["commit:abc123def"]) is None


def test_il_caso_REALE_che_ha_fatto_nascere_il_file():
    """Uno dei dodici fatti ripristinati a mano dal corpus di produzione,
    testuale. Era quarantinato da questo detector."""
    reale = ("Nella risposta di hippo_recall_history l'esca per ad518e85b39a "
             "riporta due blocchi DISPUTED unresolved con lo stesso record in "
             "conflitto")
    assert detect_unsupported_fix_claim(proposition=reale, verified_by=[]) is None
