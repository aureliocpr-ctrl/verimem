"""«Lo stipendio annuo è 45.000 euro» era GENERICO come «il sistema è veloce».

``is_specific_claim`` decide se un claim asserisce qualcosa di verificabile, ed
è la base sotto il requisito di evidenza: un claim specifico e senza fonte
prende un soffitto di fiducia di 0,6 e va al giudice di secondo livello, che lo
promuove o lo quarantina. **Un claim generico non ci arriva nemmeno.**

Misurato prima della cura::

    False  <- Lo stipendio annuo e' 45.000 euro.
    True   <- Lo stipendio annuo e' 45000 euro.
    False  <- Il wheel pesa 122.057.313 byte.
    True   <- Il wheel pesa 122057313 byte.
    True   <- Il magazzino contiene 480 pallet.
    False  <- Il sistema e veloce.

🔑 LA CAUSA, ed è la ragione per cui questo file esiste separato dagli altri
due: ``extract_quantities`` tace sui numeri ambigui — è la cura che ha chiuso un
difetto peggiore, il gate che **certificava come vero** un numero che la fonte
contraddice di mille volte. Ma il suo silenzio vuol dire «non so QUANTO», e
questa funzione chiede un'altra cosa: «c'è qualcosa da verificare?». Le due
domande erano state confuse, e chi scriveva un numero all'europea sfuggiva al
requisito di evidenza **proprio perché il suo numero era meno verificabile**.

⏰ IL DIFETTO ERA DORMIENTE, e questo è ciò che il test presidia davvero:
``ENGRAM_EVIDENCE_REQUIREMENT`` è opt-in e sta a ``False``, quindi nessuno è
stato morso. Si sarebbe svegliato il giorno dell'accensione — cioè il giorno in
cui la regola nuova sarebbe entrata già con un buco dentro. **Un difetto che non
morde oggi non è un difetto minore: è un difetto che nessuno vedrà arrivare.**
"""
from __future__ import annotations

import pytest

from verimem.evidence_requirement import (
    evidence_requirement_enabled,
    is_specific_claim,
)


@pytest.mark.parametrize("claim", [
    "Lo stipendio annuo e' 45.000 euro.",      # un gruppo di migliaia
    "Il wheel pesa 122.057.313 byte.",         # più gruppi: l'estrattore non lo vede affatto
    "Il fatturato e' 1.250.000 euro.",
])
def test_un_numero_AMBIGUO_e_comunque_una_affermazione_specifica(claim):
    """Il cuore: non misurabile non vuol dire non verificabile.

    Sono i numeri grandi scritti all'europea — giacenze, byte, fatturati,
    popolazioni — cioè esattamente quelli su cui un'evidenza serve di più.
    """
    assert is_specific_claim(claim)


@pytest.mark.parametrize("claim", [
    "Lo stipendio annuo e' 45000 euro.",
    "Il magazzino contiene 480 pallet.",
    "La tolleranza e' 0.125 mm.",
    "Il contratto scade nel 2027.",            # la strada dell'anno, che c'era già
])
def test_CONTROLLO_i_claim_gia_specifici_lo_restano(claim):
    """La strada vecchia non deve essere stata spostata dalla nuova."""
    assert is_specific_claim(claim)


@pytest.mark.parametrize("claim", [
    "Il sistema e' veloce.",
    "La memoria funziona bene.",
    "",
])
def test_CONTROLLO_POSITIVO_i_claim_GENERICI_restano_generici(claim):
    """⚠️ LA POPOLAZIONE OPPOSTA, e qui non è una formalità: una funzione che
    rispondesse sempre «sì» passerebbe i due test qui sopra e renderebbe
    specifico ogni claim del corpus — cioè spegnerebbe la distinzione che
    questa funzione esiste per fare, invece di ripararla."""
    assert not is_specific_claim(claim)


def test_IL_FLAG_E_SPENTO_e_il_test_lo_DICE_invece_di_dipenderne():
    """Perché il difetto era dormiente, scritto dove non si può perdere.

    Il requisito di evidenza è opt-in. Questo test non chiede che sia acceso —
    non è una decisione di questo file — ma **registra lo stato**: se un giorno
    diventasse rosso, vorrebbe dire che qualcuno ha acceso il requisito, e chi
    legge saprebbe che da quel momento questa classe di claim non passa più
    senza evidenza. È l'unica riga del file che parla di configurazione e non
    di comportamento, e serve a datare l'accensione.
    """
    assert evidence_requirement_enabled() is False
