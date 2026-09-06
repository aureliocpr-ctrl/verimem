"""T17, cella RED: `L4.2` avvisa falsamente sui numeri in OUTPUT DI PROGRAMMA.

I casi sono quelli trovati usando il prodotto (Iris 3317d989549f3ac7, Nadia
03e4753b74ad65aa e 915e57208f6045f4), misurati il 06/09 alle 06:44 direttamente
su `valori_riusati_da_altro_contesto`, non dedotti dal testo dell'avviso.
Letto il modulo, le giunture sono quattro e nessuna e' «nel claim cerca dopo,
nella fonte prima» (`_intorno` guarda entrambi i lati in entrambi i testi):
  ① il confronto e' solo fra lati OMOLOGHI (dopo con dopo, prima con prima):
     «249 strumenti» e «STRUMENTI ESPOSTI A RUNTIME: 249» non si incontrano;
  ② un solo token per lato, senza fermarsi al fine riga: «…: 249 ⏎ primi 3»
     da' prima={runtime}, dopo={primi};
  ③ il numero composto viene spezzato: il lookbehind esclude cifre, punto e
     virgola ma non «:» — «03:27» diventa 27, e la fonte «2026-09-06 03:27
     test» da' dopo={test}, prima={bf} (la coda dell'hash);
  ④ un numero seguito dal punto finale («esce 2.») NON viene trovato nel claim
     (il lookahead esclude il punto): il claim risulta senza parole accanto e
     il criterio scatta a vuoto.
L'output di programma ha quasi sempre la forma ETICHETTA: valore — l'unita'
precede il numero — ed e' la forma di fonte che la regola O3 chiede. Un avviso
che scatta su quella forma smette di essere letto.

Cella RED (xfail strict): misura, non cura. Accanto i controlli che devono
restare verdi — i riusi VERI dei presidi continuano a scattare e la
riformulazione normale continua a tacere — cosi' una cura che li rompe si vede
qui prima di entrare.
"""
from __future__ import annotations

import pytest

from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto

FALSI_AVVISI = [
    pytest.param("Il comando esce 2 stampando Usage.", "EXIT=2\nUsage: verimem [OPTIONS]",
                 id="exit-etichetta-a-sinistra"),
    pytest.param("Il comando esce 2.", "EXIT=2", id="exit-punto-finale"),
    pytest.param("The command exits 2.", "EXIT=2", id="exit-inglese"),
    pytest.param("Il commit ebc2bf74 risulta delle 03:27 del 2026-09-06.",
                 "ebc2bf74 2026-09-06 03:27 test della promozione: la cella diventa un presidio",
                 id="orario-composto"),
    pytest.param("La funzione _list_tools_unfiltered restituisce 249 strumenti.",
                 "STRUMENTI ESPOSTI A RUNTIME: 249\nprimi 3: ['sandbox_exec', 'hippo_run_task']",
                 id="etichetta-valore-riga-successiva"),
]


@pytest.mark.xfail(
    strict=True,
    reason="T17 RED dichiarato 06/09: L4.2 avvisa sui numeri in output di programma "
           "(ETICHETTA: valore, composti, punto finale); cura su VIA, con la misura accanto",
)
@pytest.mark.parametrize("claim,fonte", FALSI_AVVISI)
def test_lo_stesso_numero_della_stessa_grandezza_non_e_un_riuso(claim: str, fonte: str) -> None:
    assert not valori_riusati_da_altro_contesto(claim, fonte)


def test_controllo_positivo_l_unita_a_destra_da_entrambe_le_parti_tace() -> None:
    """Il caso 5 di Iris: unita' DOPO il numero in entrambi i testi, e L4.2 tace gia' oggi."""
    assert not valori_riusati_da_altro_contesto("Il comando ha richiesto 2 s.", "elapsed 2 s")


@pytest.mark.parametrize("claim,fonte", [
    ("Ci sono 14 valvole.", "Relazione: sono stati assunti 14 operai nel trimestre."),
    ("Il magazzino ha 7 corsie.", "Relazione: sono stati formati 7 tecnici."),
])
def test_controllo_positivo_il_riuso_VERO_continua_a_scattare(claim: str, fonte: str) -> None:
    """I presidi di test_il_numero_c_e_ma_parla_d_altro: una cura che li spegne non entra."""
    assert valori_riusati_da_altro_contesto(claim, fonte)


def test_controllo_positivo_la_riformulazione_continua_a_tacere() -> None:
    assert not valori_riusati_da_altro_contesto(
        "Sono stati assunti 14 operai.", "Relazione: sono stati assunti 14 operai nel trimestre.")
