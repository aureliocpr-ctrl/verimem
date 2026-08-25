"""L1.16 conosce «firmato» e non «signed»: il veto e' bilingue a meta'.

Misurato il 2026-08-25 dalla porta, stessa struttura, variabile singola = la lingua:

    IT «Il direttore ha firmato il contratto in due copie.»   quarantined 98,5 [L1.16]
    EN «The director signed the contract in two copies.»      model_claim 95,5 []

Il pattern di `l1_approval_detector` e' gia' bilingue — `approvato|autorizzato|
ratificato|firmato` accanto a `approved|authorized|ratified|blessed` — ma due
coppie restano scoperte, e in versi OPPOSTI::

    firmato    presente   signed    ASSENTE (c'e' solo `sign[- ]off`/`signed[- ]off`)
    blessed    presente   benedetto ASSENTE

Le altre dieci coppie provate (approvato/approved, autorizzato/authorized,
ratificato/ratified, accettato/accepted, concesso/granted, deliberato/resolved,
vistato/endorsed, confermato/confirmed, validato/validated, siglato/initialled)
sono allineate: o entrambe presenti o entrambe assenti.

⚠️ «benedetto» in italiano non e' un'attestazione reale — nessuno scrive «il
bilancio e' benedetto» — quindi la sua assenza non e' un difetto da curare: la
registro perche' il censimento sia completo, non perche' vada colmata.
La coppia che conta e' `firmato/signed`: chi scrive un verbale in inglese oggi non
viene mai fermato da L1.16, chi lo scrive in italiano si'.
"""
from __future__ import annotations

import pytest

from verimem.l1_approval_detector import _APPROVAL_PATTERN


def _riconosce(frase: str) -> bool:
    return bool(_APPROVAL_PATTERN.search(frase))


@pytest.mark.parametrize("it,en", [
    ("Il consiglio ha approvato il bilancio.", "The board approved the budget."),
    ("Il consiglio ha autorizzato la spesa.", "The board authorized the expense."),
    ("Il consiglio ha ratificato l'accordo.", "The board ratified the agreement."),
    ("Il direttore ha firmato il contratto.", "The director signed the contract."),
])
def test_la_stessa_attestazione_e_riconosciuta_nelle_due_lingue(it, en):
    """L'invariante: se un verbo di attestazione fa scattare il veto in una
    lingua, deve farlo anche nell'altra. Non chiede che scatti sempre — chiede
    che le due lingue siano trattate allo stesso modo."""
    assert _riconosce(it) == _riconosce(en), (
        f"il veto vede «{it}» = {_riconosce(it)} e «{en}» = {_riconosce(en)}: "
        f"chi scrive nella lingua scoperta non viene mai fermato da L1.16")


def test_CONTROLLO_un_verbo_che_non_e_attestazione_non_scatta_in_nessuna_lingua():
    """La popolazione opposta: allineare non deve voler dire allargare il veto.

    Se una cura futura facesse scattare L1.16 su verbi qualunque, questo
    diventerebbe rosso — e sarebbe un danno peggiore dell'asimmetria.
    """
    for frase in ("Il tecnico ha misurato la caldaia.",
                  "The technician measured the boiler.",
                  "Il team ha completato la migrazione.",
                  "The team completed the migration."):
        assert not _riconosce(frase), f"«{frase}» non e' un'attestazione"


@pytest.mark.parametrize("verbo", ["autorizzato", "ratificato", "firmato"])
def test_il_plurale_italiano_e_riconosciuto_come_il_singolare(verbo):
    """Il PLURALE, che in inglese non esiste come forma distinta.

    `approvato` porta tutte e quattro le forme (`approvato|approvata|approvati|
    approvate`), gli altri tre verbi solo le due singolari. Ma l'inglese non
    flette il participio — `signed` copre «the document is signed» e «the
    documents are signed» — quindi il pattern e' completo per l'inglese e monco
    per l'italiano su una forma che in italiano e' comunissima:
    «i contratti sono stati firmati» non fa scattare nulla.

    Non e' un lessico che manca: e' una lingua che flette contro una che non
    flette, e il pattern e' stato scritto contando le parole invece delle forme.
    """
    plurale = verbo[:-1] + "i"       # firmato -> firmati
    femm_pl = verbo[:-1] + "e"       # firmato -> firmate
    for forma in (plurale, femm_pl):
        assert _riconosce(f"i documenti sono stati {forma}"), (
            f"«{forma}» non fa scattare il veto mentre «{verbo}» si': in italiano "
            f"il plurale e' una forma normale, non un caso limite")


def test_CENSITO_e_non_colmato_le_forme_composte_inglesi_senza_gemello():
    """Registrato perche' il censimento sia completo, NON perche' vada curato.

    `sign off` / `signed off` / `blessed` non hanno un gemello italiano nel
    pattern. I candidati sarebbero «controfirmato» e «benedetto»: il primo e' un
    atto diverso dalla firma (non un sinonimo), il secondo non e' un'attestazione
    che qualcuno scriva in un verbale. Colmarli allargherebbe il veto senza
    coprire un caso reale.
    """
    assert _riconosce("the document is signed off")
    assert not _riconosce("il documento e' controfirmato")
