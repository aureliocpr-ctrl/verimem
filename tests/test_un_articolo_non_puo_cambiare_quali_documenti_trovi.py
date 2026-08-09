"""«del piano annuale» trovava un documento su tre, e uno DIVERSO.

`DocumentStore.search` è il tier lessicale grezzo — nessun embedding, AND di
tutti i termini, dichiarato così. L'intenzione è scritta nel docstring: «più
utile della frase contigua per query multi-parola». Ma i termini includono
articoli e preposizioni, e allora l'AND stringe su una parola che non fa parte
di ciò che si cerca.

Misurato su tre documenti che parlano tutti di piano annuale::

    'piano annuale'        -> 3 doc  [faq.md, listino.md, note.md]
    'il piano annuale'     -> 2 doc  [listino.md, note.md]
    'del piano annuale'    -> 1 doc  [faq.md]
    'rinnovo'              -> 2 doc  [faq.md, note.md]
    'sul rinnovo'          -> 1 doc  [faq.md]

Non è solo «meno»: è un insieme DIVERSO. «del piano annuale» restituisce
faq.md — l'unico che contiene «del» — e perde i due che rispondono meglio.
L'articolo non seleziona il contenuto, seleziona la grammatica.

Terza superficie con lo stesso schema, dopo `count` (`aa62e68b`) e il ramo di
esclusione (`7567a464`): un AND su tutti i token dove i token includono le
funzionali. Stessa cura, stessa lista richiamata e non ricopiata.

Il tier resta grezzo: nessun embedding, nessun punteggio, nessuna soglia. Si
toglie solo ciò che non è contenuto.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem.documents import DocumentStore

DOCS = {
    "listino.md": "Il piano annuale costa 100 euro. La prova gratuita dura "
                  "14 giorni.",
    "faq.md": "Piano annuale: sconto del 20 per cento sul rinnovo.",
    "note.md": "Rinnovo automatico attivo per piano annuale e mensile.",
}


@pytest.fixture()
def store():
    d = pathlib.Path(tempfile.mkdtemp())
    st = DocumentStore(db_path=str(d / "docs.db"))
    for nome, testo in DOCS.items():
        st.ingest(source_id=nome, content=testo)
    return st


def _ids(store, q):
    return sorted(h["source_id"] for h in store.search(q, limit=10))


@pytest.mark.parametrize("con_articolo", ["il piano annuale",
                                          "del piano annuale",
                                          "un piano annuale"])
def test_un_articolo_non_cambia_i_documenti(store, con_articolo):
    nudo = _ids(store, "piano annuale")
    got = _ids(store, con_articolo)
    assert got == nudo, (
        f"«{con_articolo}» trova {got} dove «piano annuale» trova {nudo}: "
        f"l'articolo seleziona la grammatica, non il contenuto")


def test_ne_una_preposizione(store):
    assert _ids(store, "sul rinnovo") == _ids(store, "rinnovo")


def test_le_parole_di_contenuto_restringono_eccome(store):
    """Il senso dell'AND resta: due termini veri selezionano meno di uno."""
    assert len(_ids(store, "piano sconto")) < len(_ids(store, "piano"))


def test_una_query_di_soli_articoli_non_rende_tutto(store):
    """Senza contenuto non c'è ricerca: zero, non l'intero corpus."""
    assert store.search("il la del", limit=10) == []


def test_lo_snippet_continua_a_puntare_al_termine_giusto(store):
    """Controprova: la cura non deve spostare lo snippet su un'altra parola."""
    hits = store.search("del piano annuale", limit=10)
    assert hits
    assert any("piano" in (h.get("snippet") or h.get("text") or "").lower()
               for h in hits), hits[0]
