"""«The single switch … ON across every surface» ne accendeva una su quattro.

`env_floor` è documentata così, e la sua docstring racconta l'incidente che
l'aveva prodotta:

    nothing in the tree ever set the variable, so the product's headline
    behaviour was off for every SDK, console and gateway caller while the MCP
    surface abstained. One store, two answers.

La cura del 29/07 cambiò il default a `auto`. Ma `env_floor()` è chiamata in UN
SOLO punto del prodotto — `client.py:885`, dentro `explain`. Misurato dal vivo
con `ENGRAM_MIN_RELEVANCE=0.99`, un pavimento che nessun hit può superare, su
uno store di tre fatti di listino e una domanda che non gli appartiene:

    search   -> 3 hit  best=0.7548
    recall   -> 3 hit
    ask      -> intent=find  3 risultati
    explain  -> abstained=True  min_relevance=0.99

«One store, two answers» vale ancora, con l'MCP sostituito da `explain`: la
cura era stata applicata al PUNTO e non alla CLASSE. E la misura che la
docstring cita per giustificare il default — 8 invenzioni su 8 catturate —
riguarda `explain`; le tre superfici che CLI, MCP e gateway chiamano davvero
stanno a 0 su 8.

QUELLO CHE QUESTA CURA NON FA, e perché. Non porta il DEFAULT `auto` su
`search`: quella misura è stata fatta sul percorso di `explain`, che ha il CE
gate, e applicarla a `search` cambierebbe la risposta di ogni chiamante
esistente senza una misura su quel percorso — è la forma dell'errore pagato il
30/07 con `max(floor, noise_floor)`, scritto, misurato e ritirato perché
rendeva muta la mappa dell'ignoranza. Quindi: chi NON tocca la variabile ha
esattamente il prodotto di prima; chi la SCRIVE la vede valere su tutte e
quattro, che è ciò che c'era scritto.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory

LISTINO = ["Il piano annuale costa 100 euro.",
           "La prova gratuita dura 14 giorni.",
           "Il supporto risponde in 24 ore."]
FUORI_TEMA = "quale database usa il cluster di produzione"


@pytest.fixture()
def store():
    d = tempfile.mkdtemp()
    m = Memory(path=str(pathlib.Path(d) / "s.db"))
    for t in LISTINO:
        m.add(t, topic="listino")
    return m


def test_l_interruttore_vale_anche_su_search(store, monkeypatch):
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "0.99")
    assert store.search(FUORI_TEMA, k=3) == [], (
        "l'interruttore si dichiara valido su ogni superficie e `search` "
        "continuava a servire i tre fatti del listino")


def test_e_su_recall_che_e_la_stessa_funzione(store, monkeypatch):
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "0.99")
    assert store.recall(FUORI_TEMA, k=3) == []


def test_e_su_ask_che_delega_a_search(store, monkeypatch):
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "0.99")
    assert store.ask(FUORI_TEMA)["results"] == []


def test_spento_esplicitamente_serve_tutto(store, monkeypatch):
    """`off` resta la via per il comportamento permissivo, in entrambe le
    direzioni come la docstring promette."""
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "off")
    assert len(store.search(FUORI_TEMA, k=3)) == 3


def test_SENZA_la_variabile_niente_cambia(store, monkeypatch):
    """La parte che questa cura NON fa, e che il test presidia: il default
    `auto` resta su `explain`, misurato là. Portarlo su `search` cambierebbe
    la risposta di ogni chiamante senza una misura su quel percorso."""
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    assert len(store.search(FUORI_TEMA, k=3)) == 3


def test_un_pavimento_esplicito_batte_l_ambiente(store, monkeypatch):
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "off")
    assert store.search(FUORI_TEMA, k=3, min_relevance=0.99) == []


def test_il_taglio_non_tocca_una_domanda_che_il_corpus_sa(store, monkeypatch):
    """Controprova: un pavimento vero non deve mangiare le risposte vere."""
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "0.5")
    assert any("100 euro" in h["text"]
               for h in store.search("quanto costa il piano annuale", k=3))


def test_env_floor_if_set_distingue_non_impostata_da_auto(monkeypatch):
    """`env_floor()` non poteva servire qui: rende `auto` sia quando l'utente
    lo scrive sia quando non tocca niente, e sono due intenzioni diverse."""
    from verimem.relevance_floor import env_floor, env_floor_if_set
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    assert env_floor() == "auto" and env_floor_if_set() is None
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "auto")
    assert env_floor_if_set() == "auto"
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "off")
    assert env_floor_if_set() == 0.0
