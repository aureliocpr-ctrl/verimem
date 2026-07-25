"""Le regex degli indici non devono degradare col quadrato dell'input.

Perche' questo file esiste. CodeQL, girato su una PR il 25/07, ha segnalato
py/polynomial-redos su ``quantity_match``; misurato, aveva ragione. Le due
regex contenevano ``\\s*#?\\s*`` — due quantificatori di spazio separati da un
opzionale — quindi su una corsa di spazi che non finisce con una cifra il
motore prova ogni divisione degli spazi fra i due ``\\s*``. Su "issue" + N
spazi + "x" il tempo cresceva x4 a ogni raddoppio di N: 16.6 / 65.6 / 249 /
1041 / 4031 ms per N da 1000 a 16000.

Non e' un difetto teorico: ``quantity_match`` legge il testo dei FATTI, cioe'
input scritto dall'utente, quindi un solo fatto con una lunga corsa di spazi
blocca il gate di scrittura. La cura toglie l'ambiguita' — ``\\s*(?:#\\s*)?``,
dove gli spazi dopo il cancelletto esistono solo se il cancelletto c'e' — e
riporta la crescita a lineare (1.39 ms a N=16000) senza cambiare cosa viene
riconosciuto.
"""
from __future__ import annotations

import time

import pytest

from verimem.quantity_match import (
    _EVENT_INDEX_RE,
    _GENERIC_INDEX_RE,
    event_indices,
)

#: Con la crescita quadratica questo input costava ~6 s; con quella lineare
#: costa ~2 ms. La soglia sta in mezzo con tre ordini di grandezza di margine
#: da entrambe le parti, quindi non e' un test di velocita' della macchina.
_N = 20_000
_SOGLIA_S = 2.0


@pytest.mark.parametrize("rx", [_GENERIC_INDEX_RE, _EVENT_INDEX_RE],
                         ids=["generic", "event"])
def test_a_long_run_of_spaces_does_not_explode(rx):
    """Il caso patologico: un prefisso che aggancia, una corsa di spazi
    ambigua, e nessuna cifra a chiudere — cosi' il motore deve tentare tutte
    le divisioni prima di arrendersi."""
    testo = "issue" + " " * _N + "x"
    t0 = time.perf_counter()
    list(rx.finditer(testo))
    dt = time.perf_counter() - t0
    assert dt < _SOGLIA_S, (
        f"{dt:.2f}s su {_N} spazi: la regex degrada col quadrato dell'input e "
        f"un fatto scritto dall'utente puo' bloccare il gate")


def test_the_public_entry_point_is_bounded_too():
    """La proprieta' che conta per il prodotto, non quella della singola regex:
    l'estrattore pubblico, quello che il gate chiama su ogni scrittura, resta
    limitato sullo stesso input."""
    testo = "issue" + " " * _N + "x"
    t0 = time.perf_counter()
    event_indices(testo)
    dt = time.perf_counter() - t0
    assert dt < _SOGLIA_S, f"{dt:.2f}s: event_indices degrada sullo stesso input"


@pytest.mark.parametrize(("testo", "atteso"), [
    ("issue 42", ("issue", 42)),
    ("issue #42", ("issue", 42)),
    ("issue # 42", ("issue", 42)),
    ("issue  #  42", ("issue", 42)),
    ("porta 8080", ("porta", 8080)),
    ("message 0", ("message", 0)),
    ("riga 12", ("riga", 12)),
])
def test_what_is_recognised_is_unchanged(testo, atteso):
    """La cura deve essere a costo zero sul significato: le stesse forme —
    con e senza cancelletto, con e senza spazi attorno — continuano a essere
    riconosciute come indici. Se questo cade, la cura ha cambiato il gate."""
    assert atteso in event_indices(testo), (
        f"{testo!r} non e' piu' riconosciuto come indice: {event_indices(testo)}")
