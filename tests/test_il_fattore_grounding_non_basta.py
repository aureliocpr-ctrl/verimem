"""Accendere `use_grounding` NON collega il moat alla fiducia in lettura.

`_grounding_factor` dichiara di connettere il moat del write-path alla fiducia
del read-path. E' opt-in e nessun percorso lo accende — built-never-wired — e
la tentazione ovvia era accenderlo e dichiarare il collegamento fatto.

Misurato prima, sul corpus vivo del 2026-07-30 (4755 fatti vivi, 35 giudicati),
ricalcolando l'intera classifica con e senza il fattore:

    fatti che cambiano posizione     362 su 4755
    posizione mediana dei giudicati  4418  ->  4411
    giudicati nella top-20             0  ->     0

Sette posizioni su quattromilasettecento. Il fattore non e' solo spento: alla
calibrazione attuale e' troppo debole per contrastare la confidenza, che i
fatti giudicati hanno a 0.5 (il default di `verimem save`, che non se la
inventa) mentre le inferenze di modello arrivano a 0.9-1.0 auto-assegnate.

Accenderlo avrebbe dato l'ILLUSIONE del collegamento senza il collegamento: un
interruttore acceso, una promessa dichiarata mantenuta, e i fatti verificati
ancora in fondo alla classifica. Rifarlo davvero significa ripensare come si
compone la fiducia, che e' un cambiamento di prodotto da misurare con un A/B —
non un flag da girare.

Questo file tiene il risultato attaccato al codice: se un giorno la
calibrazione cambia, questi numeri devono cambiare con lei.
"""
from __future__ import annotations

import types

from verimem.trust_score import compute_trust_score


def _f(conf: float, gs: float | None):
    return types.SimpleNamespace(id="x", proposition="p", confidence=conf,
                                 created_at=0.0, grounding_score=gs)


def test_il_boost_massimo_non_recupera_la_confidenza():
    """Un fatto giudicato 100 con la confidenza che il write-path gli da'
    (0.5) resta sotto un'inferenza mai verificata che si e' data 0.9."""
    giudicato = compute_trust_score(_f(0.5, 100.0), now=0.0,
                                    use_grounding=True)["trust"]
    inventato = compute_trust_score(_f(0.9, None), now=0.0,
                                    use_grounding=True)["trust"]
    assert giudicato < inventato, (
        f"la calibrazione e' cambiata: giudicato={giudicato} "
        f"inventato={inventato} — rimisura l'effetto sul corpus e aggiorna "
        f"il docstring di _grounding_factor")


def test_il_punto_di_pareggio_e_alto():
    """Sotto ~83 di grounding, aver passato una fonte penalizza rispetto al
    non averla passata affatto (fattore < 1.0). Non e' un difetto — chi ha
    guardato e ha visto che la fonte non regge sa piu' di chi non ha guardato —
    ma e' una soglia da conoscere prima di accendere il fattore."""
    sotto = compute_trust_score(_f(0.8, 50.0), now=0.0,
                                use_grounding=True)["trust"]
    mai = compute_trust_score(_f(0.8, None), now=0.0,
                              use_grounding=True)["trust"]
    assert sotto < mai


def test_resta_spento_di_default():
    """Finche' la calibrazione non regge la misura, il default non si tocca:
    accenderlo sarebbe dichiarare collegato cio' che non lo e'."""
    con = compute_trust_score(_f(0.5, 100.0), now=0.0)["trust"]
    senza = compute_trust_score(_f(0.5, None), now=0.0)["trust"]
    assert con == senza, "il fattore e' stato acceso di default senza una misura"
