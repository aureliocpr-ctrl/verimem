"""GATE (a) del tag 0.7.5 — mandato di Aurelio, 20/08 19:48:

    «una scrittura senza source non puo' superseder un fatto groundato»

DIAGNOSI CHE LO PRECEDE (ws5, referti 07ce9cad5e2b42bf / 6ef7efb13930a114):
il floor anti-confab confronta gli STATUS (`_STATUS_RANK`), ma passare il moat
NON promuove a `verified` — quindi un claim mai giudicato (`grounding_score=None`,
`moat=not_run:no_source`) arriva al confronto con lo stesso rango del fatto che
il giudice ha sostenuto al 98, e `2 <= 2` lo lascia passare. Il presidio esiste
e non e' collegato a cio' che il giudice decide.

BANCO MINIMO = DUE SCRITTURE (nodo d2830eb27716): un fatto solo non puo'
mostrare una supersessione. E il CONTROLLO e' obbligatorio quanto il caso:
una guardia che blocca ANCHE l'aggiornamento legittimo non e' una cura, e'
il difetto gemello — memoria: «due danni opposti, nessuno e' quello descritto».

Path LESSICALE numerico: deterministico, nessun NLI, nessun embedder finto.
"""
from __future__ import annotations

import pytest

from verimem import Memory

TOPIC = "pricing/plan"
FONTE = ["source-doc:billing:1"]


def _mem(tmp_path):
    return Memory(path=tmp_path / "sem" / "sem.db")


def test_senza_source_NON_supersede_un_fatto_groundato(tmp_path, monkeypatch):
    """IL CASO. Scrittura 1 CON source (il moat gira e la sostiene), scrittura 2
    SENZA source che la contraddice sul numero. Il vecchio deve RESTARE VIVO."""
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    mem = _mem(tmp_path)

    testo = "The subscription costs 100 euros per month."
    r1 = mem.add(testo, topic=TOPIC, verified_by=FONTE, source=testo, validate="full")
    r2 = mem.add("The subscription costs 150 euros per month.",
                 topic=TOPIC, verified_by=FONTE, validate="full")   # <-- NIENTE source

    vecchio = mem.semantic.get(r1["id"])
    assert vecchio is not None, "il primo fatto deve esistere"
    assert vecchio.superseded_by is None, (
        "una scrittura SENZA source ha ritirato un fatto groundato: "
        f"superseded_by={vecchio.superseded_by!r} (nuovo={r2.get('id')!r}, "
        f"grounding del vecchio={getattr(vecchio, 'grounding_score', None)!r})")


def test_CONTROLLO_con_source_supersede_ancora(tmp_path, monkeypatch):
    """IL CONTROLLO. Stessa forma, ma la seconda scrittura HA la sua source:
    l'aggiornamento legittimo deve continuare a ritirare il vecchio. Se questo
    diventa rosso, la guardia ha spento la promessa centrale del prodotto."""
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    mem = _mem(tmp_path)

    t1 = "The subscription costs 100 euros per month."
    t2 = "The subscription costs 150 euros per month."
    r1 = mem.add(t1, topic=TOPIC, verified_by=FONTE, source=t1, validate="full")
    r2 = mem.add(t2, topic=TOPIC, verified_by=FONTE, source=t2, validate="full")

    assert r2.get("status") != "quarantined", "il nuovo CON source deve essere ammesso"
    assert mem.semantic.get(r1["id"]).superseded_by == r2["id"], (
        "l'aggiornamento legittimo (con source) non ritira piu' il vecchio: "
        "la guardia ha rotto l'evoluzione dei fatti")


def test_senza_source_su_un_vecchio_NON_groundato_resta_come_prima(tmp_path, monkeypatch):
    """IL PERIMETRO. La guardia protegge i fatti GROUNDATI. Se nemmeno il vecchio
    e' mai stato giudicato, non c'e' niente da proteggere e il comportamento
    NON deve cambiare — altrimenti la cura e' piu' larga del suo mandato."""
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    mem = _mem(tmp_path)

    r1 = mem.add("The subscription costs 100 euros per month.",
                 topic=TOPIC, verified_by=FONTE, validate="full")     # niente source
    r2 = mem.add("The subscription costs 150 euros per month.",
                 topic=TOPIC, verified_by=FONTE, validate="full")     # niente source

    vecchio = mem.semantic.get(r1["id"])
    assert getattr(vecchio, "grounding_score", None) is None, (
        "presupposto del banco: senza source il vecchio non ha grounding")
    assert vecchio.superseded_by == r2["id"], (
        "fra due scritture entrambe senza source la supersessione deve restare "
        "quella di prima: la guardia sta agendo fuori dal suo mandato")
