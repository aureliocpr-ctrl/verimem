"""`subject_head` non trovava MAI il soggetto in italiano: mancavano i marcatori
di verbo, non le teste.

Misurato il 2026-08-25. `_VERB_MARK` ha 65 voci e sono TUTTE inglesi: senza un
marcatore la funzione non sa dove finisce il soggetto e torna stringa vuota. Il
percorso che ne dipende e' quello che ALLEGGERISCE il gate — `subject_head`
alimenta `_is_domain_professional_fact`, che a sua volta declassa L1 a
osservazione (`L1-domain-precision-observe`, anti_confab_gate:2854). Quindi in
italiano il rimedio non scattava mai e L1 quarantinava fatti che il giudice
sosteneva a 98-99.

⚠️ NON ERANO LE TESTE, e l'ho verificato prima di scrivere questo file: aggiungendo
`consiglio|squadra|comitato|reparto` a `_ORG_UNIT_HEADS` a runtime, `subject_head`
restava VUOTO. Aggiungendo invece i marcatori di verbo italiani torna
'consiglio' / 'squadra' / 'direttore'.

⚠️ E l'inglese non e' completo: `rejected` e `signed` NON sono in `_VERB_MARK`,
quindi «The committee rejected the appeal» e «The department signed the minutes»
tornano vuoti anche se `committee` e `department` sono gia' fra le teste note.
Il buco non e' «l'italiano manca»: e' che la lista dei verbi copre una parte
dell'inglese e nulla dell'italiano.
"""
from __future__ import annotations

import pytest

from verimem.subject_extract import subject_head


@pytest.mark.parametrize("frase,atteso", [
    ("Il consiglio ha approvato il bilancio.", "consiglio"),
    ("La squadra ha completato la migrazione.", "squadra"),
    ("Il direttore ha firmato il contratto.", "direttore"),
    ("Il comitato ha respinto il ricorso.", "comitato"),
])
def test_il_soggetto_italiano_viene_trovato(frase, atteso):
    """Senza questo, in italiano il gate non ha modo di alleggerire L1."""
    assert subject_head(frase) == atteso, (
        f"«{frase}» -> {subject_head(frase)!r}: senza il soggetto, "
        f"`_is_domain_professional_fact` e' False e L1 quarantina")


@pytest.mark.parametrize("frase,atteso", [
    ("The committee rejected the appeal.", "committee"),
    ("The department signed the minutes.", "department"),
])
def test_anche_in_inglese_mancano_verbi(frase, atteso):
    """`committee` e `department` sono GIA' fra le teste note: a mancare e' il
    verbo. Il difetto non e' solo italiano."""
    assert subject_head(frase) == atteso


@pytest.mark.parametrize("frase,atteso", [
    ("The board approved the budget.", "board"),
    ("The team completed the migration.", "team"),
])
def test_CONTROLLO_cio_che_funzionava_continua_a_funzionare(frase, atteso):
    """La popolazione opposta: la cura non deve rompere l'inglese che gia' andava."""
    assert subject_head(frase) == atteso


def test_CONTROLLO_una_frase_senza_soggetto_resta_vuota():
    """E non deve inventare un soggetto dove non c'e'."""
    assert subject_head("Piove.") == ""
    assert subject_head("It rains.") == ""
