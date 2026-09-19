r"""T153 — «nessuna parola accanto» non è una parola DIVERSA: è l'assenza del
dato su cui `L4.2` decide.

IL CRITERIO DEL LAYER è «le parole di contenuto attorno al numero non si
sovrappongono fra claim e fonte». Se da un lato non c'è **nessuna** parola di
contenuto, non c'è niente da sovrapporre — e il layer accusa lo stesso.

TROVATO USANDO IL PRODOTTO, salvando un fatto vero dalla CLI:

    L4.2 — il claim riusa un numero della fonte riferendolo a un'altra
           grandezza: 1 qui e' «(nessuna parola accanto)», nella fonte
           «prima del numero: totali violazioni»; 6 qui e' «(nessuna parola
           accanto)», nella fonte «prima del numero: confronti famiglia file»

MISURA sullo store vero (sola lettura, 8787 fatti con uno span):

    L4.2 accusa                        1386
    ...e in questi UN LATO E' VUOTO     354      = 25,5% delle accuse

⚠️ LA GUARDIA C'ERA GIÀ, SU UN LATO SOLO. Il modulo salta i valori per cui la
FONTE non offre nessuna parola («valore assente: non è questo il criterio che
lo copre») e non fa lo stesso per il CLAIM. È la stessa domanda posta a due
lati e risposta una volta: la giuntura, non la logica.

⛔ E QUESTO NON RENDE `L4.2` PIÙ TIMIDO DOVE DECIDE DAVVERO: il caso in cui le
due UNITÀ nominano grandezze diverse (volume contro area) non passa dalle
parole, e la sua guardia — in arrivo con la richiesta di T105 — va messa
**PRIMA** di questa. Chi ribasa legga la nota nel modulo: se le grandezze sono
note e diverse, la differenza esiste anche senza parole accanto.
"""
from __future__ import annotations

from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto

VUOTO = "(nessuna parola accanto)"

#: Il caso vissuto: il numero chiude la frase, la fonte ha parole attorno.
CLAIM_NUDO = ("I confronti di famiglia che leggono un layer sono 6, e le "
              "violazioni totali che il presidio riporta sono 1.")
FONTE_NUDA = ("violazioni totali: 1\nconfronti di famiglia nel file: 6")


def test_il_claim_senza_parole_accanto_NON_viene_accusato():
    riusati = valori_riusati_da_altro_contesto(CLAIM_NUDO, FONTE_NUDA)
    vuoti = [r for r in riusati if r.nel_claim == VUOTO or r.nella_fonte == VUOTO]
    assert not vuoti, (
        "il layer accusa un riuso dove il suo criterio non ha dati: da un "
        f"lato non c'e' nessuna parola di contenuto.\n  {vuoti}")


def test_CONTROLLO_POSITIVO_il_riuso_VERO_continua_a_scattare():
    """Le frasi vengono dal banco che presidia `L4.2`, non dalla mia memoria:
    senza questa cella la cura potrebbe spegnere il layer e sembrare riuscita."""
    assert valori_riusati_da_altro_contesto(
        "Ci sono 14 valvole.",
        "Relazione: sono stati assunti 14 operai nel trimestre."), (
        "il caso storico di L4.2 non si accende piu': la cura ha spento il "
        "layer invece di togliergli le accuse senza dati")


def test_CONTROLLO_POSITIVO_la_riformulazione_continua_a_tacere():
    assert not valori_riusati_da_altro_contesto(
        "Sono stati assunti 14 operai.",
        "Relazione: sono stati assunti 14 operai nel trimestre.")


def test_la_guardia_e_SIMMETRICA_e_lo_dice():
    """L'altro lato della stessa domanda: quando è la FONTE a non avere parole
    accanto al numero, il modulo taceva già. Questa cella tiene le due metà
    insieme, così non si torna a rispondere una sola volta.
    """
    # fonte senza parole di contenuto attorno al valore
    assert not valori_riusati_da_altro_contesto(
        "Il magazzino contiene 300 bancali.", "300")
    # claim senza parole di contenuto attorno al valore
    assert not valori_riusati_da_altro_contesto(
        "300", "Il magazzino contiene 300 bancali.")
