"""`e'` e' un marcatore di verbo quanto `è` — e senza, il soggetto sparisce.

`_VERB_MARK` (`subject_extract.py:29`) elenca i verbi finiti che chiudono il
sintagma del soggetto: `ha|hanno|è|sono|era|erano|viene|vengono`. **C'e' `è`
accentata e non c'e' `e'`**, la forma ASCII con cui l'italiano si scrive quando
manca la tastiera italiana — o quando si normalizzano gli accenti.

Senza marcatore, `subject_of()` torna vuoto, il soggetto e' «non risolvibile» e
`is_domain_professional` fallisce **prima** di guardare il dominio: la carve-out
`domain-precision`, che esiste per non escalare i fatti di terzi, **non viene
nemmeno raggiunta**.

MISURATO PRIMA DI CURARE (celle del registro dell'esame):

  `W7-72`  isolamento, UNA cosa cambiata:
           «La perizia e' stata conclusa…»  soggetto `''`         0 su 4
           «La perizia è stata conclusa…»   soggetto `'perizia'`  4 su 4
           forma attiva con `ha`            soggetto `'geometra'` 3 su 3
  `W7-73`  il corpus scrive `e'` **976** volte contro **357** con `è` — il
           TRIPLO — e **174** fatti vivi perdono il soggetto per l'apostrofo.
  `W7-74`  ma ALLA PORTA l'esito cambia in **1 caso su 24**: il **93,7%** di
           quei 174 sta dove `L1` non gira comunque. **La cura e' piccola e il
           suo effetto misurato e' minimo** — e va detto insieme al resto.

⚠️ IL RISCHIO, DICHIARATO PRIMA: aggiungere `e'` **allarga** cio' che il
classificatore legge come third-party ⇒ **piu' carve-out attivate** ⇒ `L1`
escala **di meno**. E' il verso dei **falsi permessi**. Il dossier ㉕ misura che
il verso che arriva all'utente e' il **falso allarme**, quindi la direzione e'
quella giusta — **ma le due popolazioni si guardano entrambe**, ed e' il motivo
per cui i self-claim stanno qui sotto come controllo che deve poter fallire.
"""

from __future__ import annotations

import pytest

from verimem.subject_extract import is_domain_professional, subject_of

#: POPOLAZIONI APPAIATE: la stessa frase nelle due grafie. Cambia UNA cosa.
COPPIE_IT = [
    ("La perizia e' stata conclusa dal geometra incaricato.",
     "La perizia è stata conclusa dal geometra incaricato."),
    ("L'istruttoria e' stata chiusa dal responsabile del procedimento.",
     "L'istruttoria è stata chiusa dal responsabile del procedimento."),
    ("Il collaudo dell'impianto e' stato completato dalla commissione.",
     "Il collaudo dell'impianto è stato completato dalla commissione."),
    ("La spedizione e' stata evasa dal centro logistico.",
     "La spedizione è stata evasa dal centro logistico."),
]
#: EN: la stessa forma in inglese non deve muoversi (usa `was`, gia' in lista).
FRASI_EN = [
    "The inspection was completed by the commission.",
    "The shipment was dispatched by the logistics centre.",
]
#: CONTROLLO CHE DEVE POTER FALLIRE: i self-claim restano NON-domain in
#: entrambe le grafie. Se la cura li facesse passare, allargherebbe la
#: carve-out proprio dove `L1` deve escalare, e andrebbe rifiutata.
SELF_CLAIM = [
    "Ho completato la migrazione e tutti i test passano.",
    "La migrazione e' completata e tutti i test passano.",
    "La migrazione è completata e tutti i test passano.",
    "I have finished the refactoring and the suite is green.",
]


@pytest.mark.parametrize("apo,acc", COPPIE_IT)
def test_le_due_grafie_estraggono_lo_stesso_soggetto(apo: str, acc: str) -> None:
    """Il cuore della cura: `e'` e `è` sono lo stesso verbo, quindi il
    sintagma del soggetto e' lo stesso."""
    assert subject_of(apo) == subject_of(acc) != ""


@pytest.mark.parametrize("apo,acc", COPPIE_IT)
def test_le_due_grafie_danno_lo_stesso_verdetto_di_dominio(apo: str,
                                                           acc: str) -> None:
    """E se il soggetto e' lo stesso, il verdetto del classificatore lo e'."""
    assert is_domain_professional(apo) == is_domain_professional(acc) is True


@pytest.mark.parametrize("frase", FRASI_EN)
def test_l_inglese_non_si_muove(frase: str) -> None:
    """CONTROLLO: la cura tocca una forma italiana e non deve spostare
    l'inglese, che usa un marcatore gia' in lista."""
    assert is_domain_professional(frase) is True


@pytest.mark.parametrize("frase", SELF_CLAIM)
def test_i_self_claim_restano_fuori_in_entrambe_le_grafie(frase: str) -> None:
    """CONTROLLO CHE DEVE POTER FALLIRE: allargare il marcatore di verbo non
    deve allargare la carve-out ai self-claim — che sono esattamente cio' che
    `L1` esiste per fermare. Se questo test cadesse, la cura andrebbe
    RIFIUTATA, non aggiustata."""
    assert is_domain_professional(frase) is False


def test_il_marcatore_e_nella_lista() -> None:
    """La cura in una riga: `e'` fra i verbi finiti che chiudono il soggetto."""
    from verimem.subject_extract import _VERB_MARK
    assert _VERB_MARK.search("La perizia e' stata conclusa.") is not None
