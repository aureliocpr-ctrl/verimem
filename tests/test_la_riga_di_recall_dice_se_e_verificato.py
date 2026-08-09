"""La riga che l'agente legge dice se il fatto e' stato verificato.

`recall_with_history` non restituisce dict: restituisce RIGHE DI TESTO, ed e'
il canale con cui un modello legge la memoria e decide quanto fidarsi. Il
censimento del 2026-07-30 l'ha trovata fra le superfici che portano il
contenuto del fatto senza il verdetto — e il criterio a id non la vedeva
affatto, perche' questa vista stampa la proposizione e non l'identificativo.

Qui il contratto JSON non si applica, e copiarlo sarebbe un errore. Nel payload
il verdetto c'e' SEMPRE, anche null, perche' lo legge una macchina e la
distinzione fra «assente» e «mai giudicato» costa zero. In una riga di testo
ogni token e' contesto tolto a chi legge: sul corpus vivo i fatti con un
verdetto sono una minoranza, quindi marcare «non verificato» su quasi ogni riga
sommergerebbe il segnale invece di darlo.

Percio': si marca solo quando il verdetto c'e'. L'assenza resta muta.
"""
from __future__ import annotations

from verimem.semantic import Fact
from verimem.temporal_context import history_line


def test_un_fatto_verificato_lo_dice():
    f = Fact(proposition="Il servizio ascolta sulla porta 8443.",
             grounding_score=99.9)
    riga = history_line(f, [])
    assert "99.9" in riga, f"la riga non porta il verdetto:\n{riga}"


def test_un_fatto_mai_giudicato_non_aggiunge_rumore():
    f = Fact(proposition="Il servizio ascolta sulla porta 8443.")
    riga = history_line(f, [])
    assert "verificat" not in riga.lower(), (
        f"marcare l'assenza su ogni riga e' rumore, non segnale:\n{riga}")
    assert riga.startswith("Il servizio ascolta")


def test_il_verdetto_non_scaccia_la_storia():
    """Il marcatore si affianca alla transizione, non la sostituisce."""
    vecchio = Fact(proposition="Ascoltava sulla 8080.")
    nuovo = Fact(proposition="Ora ascolta sulla 8443.", grounding_score=91.0)
    riga = history_line(nuovo, [vecchio], disputes=["Qualcuno dice 9000."])
    assert "91.0" in riga
    assert "PREVIOUSLY" in riga and "8080" in riga
    assert "DISPUTED" in riga


def test_un_punteggio_non_numerico_non_rompe_la_riga():
    """L'arricchimento non deve mai rompere il recall — vale anche qui."""
    class _Strano:
        proposition = "x"
        grounding_score = "non-un-numero"
    riga = history_line(_Strano(), [])
    assert riga.startswith("x")
