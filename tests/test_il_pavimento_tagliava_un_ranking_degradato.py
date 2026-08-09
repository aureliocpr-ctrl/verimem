"""Quando l'encoder è lento il prodotto si astiene, e non c'entra l'evidenza.

TROVATO USANDO IL PRODOTTO sul corpus vero: `verimem recall` stampava `[0.00]`
su ogni riga, e nel log c'era la ragione::

    encode exceeded 2.0s budget → degrading (recall falls back to keyword)

Sul ramo keyword `SemanticMemory.recall` assegna `score 0.0` a TUTTI i
risultati (``hits_2t = [(f, 0.0) for f in kw]``). Quello zero non significa
«nessuna somiglianza»: significa «somiglianza NON MISURATA». Ha la forma di
una misura e non lo è.

Misurato, stesso store, stessa domanda::

    a caldo      [0.8995] la risposta giusta · min_relevance=0.5 -> 1 risultato
    degradato    [0.0]    LA STESSA risposta · min_relevance=0.5 -> 0 risultati

⚠️ PER UN PRODOTTO LA CUI PROMESSA DI PUNTA È «abstention over hallucination»
questo è il modo peggiore di sbagliare: si astiene per un motivo che non ha
nulla a che vedere con l'evidenza — l'encoder era lento — e chi legge non ha
modo di distinguerlo da un'astensione vera. ws4 ha misurato 8 astensioni su 8
corrette fuori dominio: quella garanzia vale finché l'encoder risponde.

Il contatore `_recall_degraded_count` ESISTEVA GIÀ, ed è nato apposta perché
«il degrado cold-encode era invisibile al caller». Nessuno lo leggeva da qui:
undicesima istanza di «il meccanismo c'è, il chiamante non lo alimenta».
"""
from __future__ import annotations

import pytest

import verimem.semantic as sem
from verimem.client import Memory

DOMANDA = "Quanti metri quadrati ha il magazzino K-77?"


@pytest.fixture()
def registro(tmp_path):
    m = Memory(str(tmp_path / "reg.db"))
    for i in range(1, 8):
        m.add(f"Il magazzino K-{70 + i} di Rovigo ha {4000 + i * 100} "
              f"metri quadrati.", topic="az/mag")
    return m


@pytest.fixture()
def degradato(monkeypatch):
    """Forza il ramo keyword: è la stessa strada che il codice prende da solo
    quando il daemon di encode è freddo o contenduto."""
    monkeypatch.setattr(sem, "_encode_prepared_within_budget",
                        lambda *a, **k: None)


def test_il_pavimento_non_azzera_una_risposta_degradata(registro, degradato):
    """IL CUORE: la risposta giusta c'è, il fallback la trova, e il pavimento
    la buttava via per uno zero che non era una misura."""
    hits = registro.search(DOMANDA, k=3, min_relevance=0.5)
    assert hits, "il pavimento ha svuotato un recall degradato"
    assert "K-77" in str(hits[0].get("text"))


def test_il_degrado_si_dichiara(registro, degradato):
    """Non basta smettere di tagliare: chi legge deve sapere che quello `0.0`
    non è una somiglianza bassa, è una somiglianza non misurata."""
    hits = registro.search(DOMANDA, k=3)
    assert hits
    assert hits[0].get("ranking") == "keyword", sorted(hits[0])


def test_a_caldo_il_pavimento_taglia_ancora(registro):
    """IL PRESIDIO. La cura toglie il taglio SOLO sul ramo degradato: dove la
    somiglianza è stata misurata davvero, il pavimento fa il suo mestiere —
    ed è la garanzia che ws4 ha misurato 8 volte su 8 fuori dominio."""
    assert registro.search(DOMANDA, k=3, min_relevance=0.99) == []
    caldi = registro.search(DOMANDA, k=3)
    assert caldi and "ranking" not in caldi[0], (
        "a caldo non si dichiara nessun degrado")
