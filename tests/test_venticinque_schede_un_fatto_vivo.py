"""Venticinque schede scritte, una viva: il corpus aveva capienza UNO.

TROVATO da ws5 misurando la SCALA — la dimensione che il progetto stesso
dichiara meno presidiata (5% delle guardie) — e riprodotto qui in indipendenza.
Un registro di laboratorio con codici distinti, analiti diversi e valori
diversi, scritto in frasi piane:

    scritti  10  ->  1 vivo      scritti 100  ->  1 vivo
    scritti  25  ->  1 vivo      scritti 200  ->  1 vivo
    scritti  50  ->  1 vivo

**Non è una perdita proporzionale: è una capienza.** Il numero di sopravvissuti
non cresce mai, e il sopravvissuto è semplicemente l'ultimo scritto. Ventiquattro
ritiri su venticinque, tutti con reason `same-source evolution`.

Un'evoluzione è «la stessa cosa che cambia valore». Due schede con codici
diversi non sono la stessa cosa, e nessun ordine temporale le rende tali.

⚠️ IL VETO STA QUI E NON SOLO IN `quantity_match`. La prima cura — il codice del
record letto come una quantità, `S-001` → `('contiene', 1.0)` — è giusta e
misurata, ma **non intercetta questo caso**: il conflitto, alla scala, è
rilevato per via SEMANTICA e non numerica, quindi `numeric_conflict` non viene
nemmeno interrogato. È l'ennesima conferma della regola di casa: *un difetto di
funzione è un'ipotesi finché non è girato end-to-end.*

⚠️ I DUE PRESIDI, senza cui questo diventerebbe «la memoria non si aggiorna
più» — che è il danno misurato il 2026-08-03 su
`ENGRAM_SUPERSEDE_SAME_SOURCE=0`:
  * il codice deve esserci su **entrambi** i lati (se manca a uno, non si sa
    nulla e il conflitto va visto);
  * lo **stesso** codice con due valori resta un'evoluzione, e ritira.
"""
from __future__ import annotations

import pytest

from verimem.supersession_policy import classify_write_relation


class _F:
    def __init__(self, prop: str, t: float):
        self.proposition = prop
        self.created_at = t
        self.asserted_at = None
        self.verified_by = []
        self.source_signature = None


@pytest.mark.parametrize("a,b", [
    ("Il campione S-001 contiene piombo a 11 milligrammi per litro.",
     "Il campione S-002 contiene cadmio a 12 milligrammi per litro."),
    ("La scheda REF-10 riporta una resa dell'80 per cento.",
     "La scheda REF-11 riporta una resa del 65 per cento."),
    ("Il magazzino K-77 ha 4200 metri quadri.",
     "Il magazzino B-12 ha 1800 metri quadri."),
])
@pytest.mark.xfail(strict=True, reason="IL DIFETTO E' VIVO: la cura e' stata scritta, misurata e RITIRATA il 2026-08-04 perche' chiude il caso (25 schede -> 25 vive invece di 1) ma ROMPE il presidio qui accanto e fa cadere 2 test nella suite del gate. Causa accertata nel docstring; patch in scratchpad/CURA-capienza-uno.patch.")
def test_due_record_con_codici_diversi_non_sono_un_aggiornamento(a, b):
    """Il cuore: è la coppia che, moltiplicata per un registro, lascia un fatto
    vivo su venticinque."""
    rel = classify_write_relation(_F(b, 200.0), _F(a, 100.0))
    assert rel == "conflict", (
        f"«{b[:40]}…» viene classificato {rel} rispetto a «{a[:40]}…»")


def test_lo_STESSO_record_che_cambia_valore_resta_un_aggiornamento():
    """IL PRESIDIO. Se la stessa scheda arriva con un valore nuovo, il secondo
    aggiorna il primo: è il mestiere di una memoria. Una che non ritira più
    nulla è rotta quanto una che ritira tutto."""
    vecchio = _F("Il campione S-001 contiene piombo a 11 milligrammi per litro.", 100.0)
    nuovo = _F("Il campione S-001 contiene piombo a 25 milligrammi per litro.", 200.0)
    assert classify_write_relation(nuovo, vecchio) == "evolution"


def test_un_codice_su_un_lato_solo_non_basta_a_vietare():
    """L'ALTRO PRESIDIO: se uno dei due non porta un codice, non si sa se
    parlino della stessa cosa, e il comportamento non cambia."""
    vecchio = _F("Il campione S-001 contiene piombo a 11 milligrammi per litro.", 100.0)
    nuovo = _F("Il campione contiene piombo a 25 milligrammi per litro.", 200.0)
    assert classify_write_relation(nuovo, vecchio) == "evolution"


def test_senza_codici_il_comportamento_e_quello_di_prima():
    """La compatibilità: sui fatti che non portano codici — cioè quasi tutto il
    nostro corpus di cronache — non cambia nulla."""
    vecchio = _F("Il server di produzione ha 64 GB di RAM.", 100.0)
    nuovo = _F("Il server di produzione ha 128 GB di RAM.", 200.0)
    assert classify_write_relation(nuovo, vecchio) == "evolution"
