"""T150 — `quarantined_by` nomina IL LAYER che ha agito, non la FAMIGLIA.

Il difetto, trovato sul tronco rosso del 19/09 e classificato prima di essere
spiegato: la colonna diceva `'moat'` mentre il layer che aveva trattenuto era
`'L4-grounding'`. Due nomi per la stessa decisione — chi legge la colonna non
può incrociarla con i layer della ricevuta, e `quarantine_log` non può dire
QUALE controllo ha fermato la scrittura.

È la classe di T77 («la CLI scriveva "gate" al posto del layer»): un'etichetta
di famiglia al posto del nome proprio. `moat` continua a esistere dove è un
fatto e non un'etichetta — il campo `moat: failed` della ricevuta.

⚠️ PERCHÉ QUESTE CELLE NON SCRIVONO NIENTE. La cella che ha scoperto il difetto
(`test_quarantined_by_nomina_chi_ha_deciso`) costruisce una coppia e la fa
giudicare: si è accesa il 19/09 non perché l'etichetta fosse peggiorata, ma
perché il PUNTEGGIO di quella coppia è sceso da una banda incerta (`L4-review`,
dove `moat` non è 'failed') a 0.0 (`L4-grounding`, dove lo è). Misurava il
giudice credendo di misurare l'etichetta, e si sarebbe spenta da sola il giorno
in cui il giudice cambia idea.

`chi_ha_quarantinato` è una funzione pura: si chiama con gli argomenti che
interessano e il verdetto non dipende da nessun modello. Il costo è che non
prova la giuntura col write path — per quella resta la cella alla porta.
"""
from __future__ import annotations

import pytest

from verimem.client import chi_ha_quarantinato

#: Come arriva davvero una ricevuta quando il moat boccia: il layer parla nei
#: warning E compare fra quelli che hanno agito. Copiato dalla misura del
#: 19/09 su `dca8b406`, non ricostruito a mente:
#:     moat='failed'  grounding_score=0.0  layer=['L4-grounding']
MOAT_BOCCIA = {
    "moat": "failed",
    "warnings": [{"layer": "L4-grounding"}],
    "agito": ["L4-grounding"],
}


def test_quando_il_moat_boccia_l_etichetta_e_il_LAYER_non_la_famiglia():
    """Il RED di T150. Oggi rende 'moat'; deve rendere 'L4-grounding'."""
    etichetta = chi_ha_quarantinato(
        MOAT_BOCCIA["moat"], MOAT_BOCCIA["warnings"],
        agito=MOAT_BOCCIA["agito"])
    assert etichetta == "L4-grounding", (
        f"l'etichetta e' {etichetta!r}: e' il nome della FAMIGLIA, e il layer "
        f"che ha agito ({MOAT_BOCCIA['agito']}) non e' ricostruibile da chi "
        "legge la colonna. Il campo `moat: failed` dice gia' la famiglia."
    )


def test_l_etichetta_e_SEMPRE_uno_dei_layer_che_hanno_agito():
    """L'invariante, sulle forme in cui il moat boccia con layer diversi.

    Non è una ripetizione del test sopra: quello pianta UN valore atteso,
    questo dice che la proprietà vale per QUALSIASI layer, così la cura non
    può essere un `if` sul nome 'L4-grounding'.
    """
    for layer in ("L4-grounding", "L4.1", "L4-review", "L2-contraddizione"):
        etichetta = chi_ha_quarantinato(
            "failed", [{"layer": layer}], agito=[layer])
        assert etichetta == layer, (
            f"con un solo layer che ha agito ({layer!r}) l'etichetta e' "
            f"{etichetta!r}: deve nominare quel layer"
        )


def test_CONTROLLO_quando_il_moat_NON_boccia_l_etichetta_era_gia_giusta():
    """Il controllo positivo: la popolazione che funzionava DEVE restare verde.

    Se questa cella si spegne, la cura ha rotto il ramo che andava bene e il
    rosso sopra non dimostra niente.
    """
    etichetta = chi_ha_quarantinato(
        "passed", [{"layer": "L4-review"}], agito=["L4-review"])
    assert etichetta == "L4-review", (
        f"l'etichetta e' {etichetta!r}: questo ramo era gia' corretto prima "
        "della cura e non doveva cambiare"
    )


def test_CONTROLLO_la_precedenza_dello_screen_dello_store_non_si_tocca():
    """`store-screen` vince su tutto, anche quando il moat boccia.

    Sta nel codice con la sua misura (34 scritture su 1268, 2,7%): dire «moat»
    quando il gate aveva AMMESSO e lo screen ha ribaltato e' un'attribuzione
    falsa. La cura di T150 non deve avvicinarsi a questo ramo.
    """
    etichetta = chi_ha_quarantinato(
        "failed", [{"layer": "L4-grounding"}],
        agito=["store-screen", "L4-grounding"])
    assert etichetta == "store-screen", (
        f"l'etichetta e' {etichetta!r}: lo screen dello store ha la precedenza "
        "e la cura di T150 l'ha spostata"
    )


@pytest.mark.parametrize("agito", [(), ("",)])
def test_senza_layer_che_hanno_agito_resta_la_famiglia(agito):
    """Il ripiego, e perché NON è una scappatoia.

    Se il moat boccia e nessun layer risulta fra quelli che hanno agito, non
    c'è un nome proprio da dare: `'moat'` resta, ed è meglio di `'gate'`
    perché dice almeno quale famiglia. Questa cella esiste perché la cura non
    deve produrre `'gate'` — che è l'etichetta generica che T77 ha tolto — né
    una stringa vuota.
    """
    etichetta = chi_ha_quarantinato("failed", [], agito=agito)
    assert etichetta == "moat", (
        f"senza layer che hanno agito l'etichetta e' {etichetta!r}: il ripiego "
        "deve restare 'moat', non 'gate' e non vuoto"
    )
