"""Far trovare il soggetto italiano SENZA declassare le self-claim.

Il 25/08 avevo curato la prima meta' (`1900b83b`) e aperto una falla: con i
marcatori di verbo italiani `subject_head` trovava «migrazioni», ma
`SOFTWARE_HEADS` e' inglese, quindi il classificatore non riconosceva la
self-claim, `_is_domain_professional_fact` tornava True e **L1 veniva declassato**.
Risultato: «Le migrazioni sono completate» — una self-claim non sostenuta —
entrava come `model_claim`. Revertito il 26/08 (`dd904750`) dopo che la CI ha
mostrato 17 test rossi.

    marcatori IT soli          self-claim domain=True   ⛔ falla
    marcatori IT + teste IT    self-claim domain=False  ✅

⚠️ LE DUE META' VANNO INSIEME, e questo file esiste per impedire che vengano
separate di nuovo: chi aggiunge i verbi senza le teste riapre la falla, e i test
che la prendono (`test_il_gate_leggeva_solo_il_maschile_singolare`) NON importano
`subject_extract` — passano dal gate, quindi un censimento degli importatori non
li trova. E' cosi' che mi e' sfuggito.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import _is_domain_professional_fact
from verimem.subject_extract import subject_head


@pytest.mark.parametrize("frase,testa", [
    ("Il consiglio ha approvato il bilancio.", "consiglio"),
    ("La squadra ha completato la migrazione.", "squadra"),
    ("Il comitato ha respinto il ricorso.", "comitato"),
])
def test_il_soggetto_italiano_viene_trovato(frase, testa):
    """La meta' che serve: senza soggetto il rimedio di L1 non scatta mai in
    italiano e il gate quarantina fatti che il giudice sostiene a 98-99."""
    assert subject_head(frase) == testa


@pytest.mark.parametrize("frase", [
    "Il consiglio ha approvato il bilancio.",
    "Il comitato ha respinto il ricorso.",
])
def test_un_fatto_di_terzi_resta_declassabile(frase):
    """Un fatto su un organo terzo DEVE poter alleggerire L1: e' lo scopo."""
    assert _is_domain_professional_fact(frase) is True


@pytest.mark.parametrize("frase", [
    "Le migrazioni sono completate.",
    "Il modulo e stato rilasciato.",
    "La migrazione e completata.",
    "Il servizio e pronto per la produzione.",
])
def test_LA_META_CHE_MI_ERA_SFUGGITA_le_selfclaim_NON_si_declassano(frase):
    """⚠️ IL PRESIDIO CHE MANCAVA AL MIO BANCO DI IERI.

    Una self-claim sul proprio software non e' un «third-party professional
    fact»: se `_is_domain_professional_fact` la dichiara tale, L1 viene declassato
    e la self-claim entra. E' il difetto centrale che il gate esiste per fermare —
    «unsupported "it works" claims quarantined» — quindi vale piu' dell'asimmetria
    di lingua che la cura vuole chiudere.
    """
    assert _is_domain_professional_fact(frase) is False, (
        f"«{frase}» e' una self-claim e verrebbe declassata: L1 non escala piu' e "
        f"la frase entra come model_claim")
