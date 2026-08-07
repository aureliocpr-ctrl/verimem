"""«stato al 2026-08-05» non àncora niente; «as of 2026-08-05» sì.

IL DIFETTO, trovato usando il prodotto e non leggendo il codice::

    extract_as_of("what happened on 2026-08-05?")   ->  1785974399.0   ✅
    extract_as_of("stato al 2026-08-05")            ->  None           ❌
    extract_as_of("cosa e' successo il 5 agosto 2026?") -> None        ❌

🔑 **La stessa data ISO**: in inglese àncora, in italiano no. Quindi non è la
data che non viene riconosciuta — è la preposizione che la introduce.

L'ASIMMETRIA STA DENTRO LO STESSO MODULO, ed è la forma che questa casa paga
più spesso — *«la causa non è mai "manca X": quasi sempre X c'era, INCOMPLETO»*::

    _TEMPORAL_QUERY_RE   riga 40   gennaio|febbraio|marzo|…   commento: «EN+IT»
    _AS_OF_ANCHOR_RE     riga 71   as of|on|by|until|before   solo EN

Due regex temporali nello stesso file, scritte per lo stesso prodotto: una è
bilingue e l'altra no. Chi ha scritto la prima sapeva che il prodotto è usato in
italiano; la seconda è nata dopo (cantiere 2026-07-08, per un caso in inglese) e
non è mai tornata sulla gemella.

⚠️ COSA COSTA DAVVERO, perché non è un dettaglio di traduzione: `extract_as_of`
instrada il **time-travel** del recall. Senza àncora, una domanda retrospettiva
italiana riceve lo stato **corrente** invece di quello alla data chiesta — cioè
la risposta sbagliata, non un errore visibile. Il commento del modulo racconta
esattamente questo incidente al contrario: senza routing «l'answerer si asteneva
PUR AVENDO la risposta alla riga 2 del contesto».

📌 SCELTA DICHIARATA: si copre **EN+IT**, la stessa coppia della regex gemella,
e non si inventa una copertura più larga. Le liste monolingue sono la classe ③
di questa casa, ma una lista che cresce a caso è la stessa malattia con più
righe: si allinea alla superficie che esiste già, e le altre lingue restano un
buco **dichiarato** invece che scoperto per caso.
"""
from __future__ import annotations

import pytest

from verimem.temporal_context import extract_as_of


@pytest.mark.parametrize("query", [
    "stato al 2026-08-05",
    "com'era la situazione al 2026-08-05?",
    "cosa risultava entro il 2026-08-05?",
    "qual era lo stato prima del 2026-08-05?",
    "fino al 2026-08-05 cosa sapevamo?",
])
def test_una_domanda_retrospettiva_ITALIANA_ancora_la_data(query):
    """IL CUORE. La data è in ISO, identica a quella che l'inglese riconosce:
    a mancare è solo la preposizione italiana che la introduce."""
    assert extract_as_of(query) is not None, query


@pytest.mark.parametrize("query", [
    "cosa e' successo il 5 agosto 2026?",
    "qual era lo stato al 12 marzo 2026?",
])
def test_anche_col_MESE_scritto_in_italiano(query):
    """`_TEMPORAL_QUERY_RE` conosce i mesi italiani dalla riga 40; l'ancora no,
    e i due elenchi vivono a trenta righe di distanza."""
    assert extract_as_of(query) is not None, query


@pytest.mark.parametrize("query", [
    "what happened on 2026-08-05?",
    "the state as of 2026-08-05",
    "status by December 21, 2025",
    "what was true until 21 Dec 2025?",
])
def test_CONTROLLO_POSITIVO_l_inglese_continua_a_funzionare(query):
    """⚠️ IL PRESIDIO: l'inglese è la popolazione che già funzionava, ed è il
    solo modo di sapere che la cura ha aggiunto invece di sostituire."""
    assert extract_as_of(query) is not None, query


@pytest.mark.parametrize("query", [
    "dopo il 2026-08-05 cosa e' cambiato?",
    "what changed after 2026-08-05?",
])
def test_DOPO_non_ancora_niente_ne_in_IT_ne_in_EN(query):
    """L'esclusione deliberata del modulo, che la cura non deve erodere: *«after
    <data> apre un periodo SUCCESSIVO che il time-travel taglierebbe»*. Se
    l'italiano «dopo» entrasse, avrei importato in una lingua un difetto che
    nell'altra era stato evitato apposta."""
    assert extract_as_of(query) is None, query


@pytest.mark.parametrize("query", [
    "cosa sappiamo del fornitore Bianchi?",
    "quanti bancali ci sono a Prato?",
    "situazione di ieri",
])
def test_una_domanda_SENZA_data_non_inventa_un_ancoraggio(query):
    """L'altro presidio, e vale il doppio su una lista che si allarga: la
    funzione è dichiarata *«conservativa: nessuna àncora inventata»*. «ieri» è
    volutamente fuori — è relativo a quando si chiede, non a un punto fisso."""
    assert extract_as_of(query) is None, query
