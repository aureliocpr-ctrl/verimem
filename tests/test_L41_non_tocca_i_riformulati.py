"""Un utente che riscrive con parole sue non riscrive i numeri.

IL PRESIDIO CHIESTO DA ws4, e il rischio che aveva segnalato è reale — sul SUO
criterio. Lui aveva misurato la COPERTURA LESSICALE (frazione di parole del
claim assenti dalla fonte) e l'aveva **ritirata prima di consegnarla**::

    | popolazione                   | ammessi dal MOAT | segnalati dalla COPERTURA |
    | INVENTATI (la fonte non ne parla) |   9/10  ❌   |        9/10  ✅          |
    | VERI letterali                    |  10/10  ✅   |        0/10  ✅          |
    | VERI RIFORMULATI (sinonimi)       |   8/8   ✅   |        6/8   ❌          |

    «La copertura da sola non è consegnabile: 6 falsi positivi su 8, e il
     riformulato È IL CASO NORMALE — nessun utente ricopia la fonte, la
     riassume con parole sue.»

Misurato su L4.1, che è un criterio diverso::

    VERI RIFORMULATI (parole diverse, numeri VERI)  passati  5/5
    INVENTATI (numeri FALSI)                        ammessi  0/3

🔑 NON È FORTUNA, È CHE MISURIAMO COSE DIVERSE::

    la copertura guarda le PAROLE  -> un riformulato le cambia    -> falso positivo
    L4.1         guarda i VALORI   -> un riformulato tiene i numeri -> passa

Un utente che riscrive con parole sue **non riscrive i numeri**: 300 bancali
restano 300. È questo che rende il valore un segnale più stretto della parola —
L4.1 copre meno (solo le cifre) e in cambio non sbaglia sul caso normale.

📌 E UN DATO CHE CONFERMA LA TESI DI ws5 («il giudice misura la COMPATIBILITÀ,
non l'implicazione»): gli inventati con numeri CAMBIATI (500 invece di 300) li
ferma **il moat** a g≈0.5, non L4.1. Cambiare un numero rende la frase
incompatibile e lì il moat funziona; **non dirlo affatto** la lascia compatibile
e lì è cieco. L4.1 copre quella metà precisa: l'assenza, non la contraddizione.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

FONTE = ("Verbale: il deposito di Prato ospita 300 bancali. La consegna e' "
         "stata effettuata il 12 marzo con 45 colli. Il contratto vale "
         "1200 euro.")


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


@pytest.mark.parametrize("claim", [
    "Il magazzino di Prato contiene 300 bancali.",
    "Sono stati spediti 45 colli.",
    "Il valore contrattuale ammonta a 1200 euro.",
    "A Prato ci sono 300 pallet stoccati.",
    "La spedizione comprendeva 45 colli.",
])
def test_un_VERO_RIFORMULATO_passa(mem, claim):
    """IL PRESIDIO CHE ws4 HA CHIESTO. Parole diverse dalla fonte — magazzino
    per deposito, pallet per bancali, spediti per consegnati — ma gli stessi
    numeri. È il caso NORMALE, e se L4.1 lo bloccasse sarebbe inutilizzabile."""
    r = mem.add(claim, topic="az/r", source=FONTE)
    assert r.get("status") != "quarantined", (
        f"riformulato VERO trattenuto: {claim} (g={r.get('grounding_score')})")


@pytest.mark.parametrize("claim", [
    "Il deposito di Prato ospita 500 bancali.",
    "La consegna comprendeva 60 colli.",
    "Il contratto vale 3000 euro.",
])
def test_un_numero_CAMBIATO_resta_fermato(mem, claim):
    """L'altra popolazione. ⚠️ Questi li ferma il MOAT (g≈0.5), non L4.1: un
    numero cambiato rende la frase INCOMPATIBILE con la fonte, e su
    l'incompatibilità il giudice funziona benissimo. Il test sta qui perché la
    cura non deve rompere ciò che già funzionava."""
    r = mem.add(claim, topic="az/i", source=FONTE)
    assert r.get("status") == "quarantined", claim


def test_la_differenza_fra_i_due_criteri_e_MISURABILE(mem):
    """CONTROLLO POSITIVO sul senso del file: se un riformulato e un inventato
    finissero nello stesso stato, questo banco non separerebbe niente e i test
    sopra sarebbero soddisfatti da un gate che dice sempre la stessa cosa."""
    riformulato = mem.add("A Prato ci sono 300 pallet stoccati.",
                          topic="az/a", source=FONTE)
    inventato = mem.add("A Prato ci sono 500 pallet stoccati.",
                        topic="az/b", source=FONTE)
    assert riformulato.get("status") != inventato.get("status"), (
        "il banco non separa: stesso esito per un vero e un falso")
