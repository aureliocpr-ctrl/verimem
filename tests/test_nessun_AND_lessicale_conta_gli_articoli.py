"""IL CRICCHETTO della classe: un AND lessicale non può contare gli articoli.

Tre superfici curate il 2026-08-02 con lo stesso difetto e tre effetti diversi:

* `Memory.count` (`aa62e68b`) — «del moat» contava 134 dove «moat» conta 207,
  73 fatti persi su 5343, il 35%. Un conteggio che promette «the WHOLE
  matching set» ne vedeva due terzi.
* Il ramo EXCLUDE di `Memory.ask` (`7567a464`) — «tutto tranne IL moat»
  lasciava dentro 2 fatti invece di 1: qui restringere l'insieme escluso
  significa LASCIARE DENTRO ciò che l'utente ha chiesto di togliere.
* `DocumentStore.search` (`d17f6c92`) — «del piano annuale» rendeva 1
  documento su 3, e uno DIVERSO: l'unico che conteneva «del».

La forma è sempre la stessa: un AND su TUTTI i token di una query, dove i
token includono articoli e preposizioni. Cambia solo il segno del danno.

Questo test non ripete i tre presidi: presidia la CLASSE. Ogni superficie che
accetta una query dall'utente e ne fa un AND lessicale deve chiedere i token
informativi a `bm25_rank._tokens` — l'unico posto dove quella lista vive.

⚠️ NON vale per la RICERCA. `search_facts(require_all_tokens=True)` chiamata
per cercare una frase esatta deve continuare a stringere: chi cerca «il piano
annuale» come frase la vuole trovare così. Il criterio non è «mai le
funzionali», è «non nelle superfici che promettono un INSIEME».
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory
from verimem.documents import DocumentStore

#: (nome, funzione che prende una query e rende un insieme confrontabile)
#: Ogni voce è una superficie che promette un INSIEME, non un top-k.
CORPUS = [
    "Il moat giudica la fonte contro il fatto.",
    "Senza source il moat non gira.",
    "Moat e gate sono due nomi della stessa cosa.",
    "Il gate lessicale gira sempre.",
]


@pytest.fixture()
def superfici():
    d = pathlib.Path(tempfile.mkdtemp())
    m = Memory(path=str(d / "s.db"))
    for t in CORPUS:
        m.add(t, topic="note")
    st = DocumentStore(db_path=str(d / "docs.db"))
    for i, t in enumerate(CORPUS):
        st.ingest(source_id=f"doc{i}.md", content=t)

    return {
        "Memory.count": lambda q: m.count(query=q),
        "Memory.ask/exclude": lambda q: len(
            m.ask("tutto tranne " + q)["results"]),
        "DocumentStore.search": lambda q: len(st.search(q, limit=50)),
    }


#: Coppie (nuda, con la grammatica intorno). Se una superficie risponde in
#: modo diverso alle due, sta contando parole che non sono contenuto.
COPPIE = [("moat", "il moat"),
          ("moat", "del moat"),
          ("gate", "un gate"),
          ("gate", "sul gate")]


@pytest.mark.parametrize("nuda,vestita", COPPIE)
def test_ogni_superficie_a_insieme_ignora_la_grammatica(superfici, nuda,
                                                        vestita):
    divergenti = []
    for nome, f in superfici.items():
        a, b = f(nuda), f(vestita)
        if a != b:
            divergenti.append(
                f"{nome}: «{nuda}» -> {a}   «{vestita}» -> {b}")
    assert not divergenti, (
        "una superficie che promette un INSIEME risponde diversamente a due "
        "formulazioni della stessa domanda:\n  " + "\n  ".join(divergenti)
        + "\n\nI token informativi si chiedono a `bm25_rank._tokens`, che è "
        "l'unico posto dove quella lista vive.")


def test_la_RICERCA_continua_a_stringere(superfici):
    """Il perimetro, presidiato: `require_all_tokens` usato per cercare una
    FRASE deve restare com'è. Il criterio non è «mai le funzionali», è «non
    nelle superfici che promettono un insieme»."""
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s2.db"))
    for t in CORPUS:
        m.add(t, topic="note")
    sm = m.semantic
    con = sm.search_facts("il moat", limit=100, require_all_tokens=True)
    senza = sm.search_facts("moat", limit=100, require_all_tokens=True)
    assert len(con) < len(senza), (
        "la ricerca ha smesso di stringere: la cura ha invaso il percorso di "
        "precisione invece di restare nelle superfici a insieme")
