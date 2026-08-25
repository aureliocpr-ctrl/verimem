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
