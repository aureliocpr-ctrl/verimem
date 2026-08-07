"""`recall` dice `text`, `explain` dice `proposition`. Stessa cosa, due nomi.

FINDING DI ws5, e il costo l'ha misurato addosso a sé::

    «mi ha fatto quasi consegnare *explain sbaglia 10 su 10*» — su una
     funzione che è corretta.

Verificato, e i nomi doppi sono DUE, non uno::

    il TESTO      recall: `text`   ·  explain: `proposition`
    il PUNTEGGIO  recall: `score`  ·  explain: `relevance`

Chi impara una superficie e passa all'altra cerca la chiave che conosce, non la
trova, e conclude che la risposta sia vuota. È successo a un utente esperto in
mezz'ora, con il prodotto sotto gli occhi.

⚠️ SI AGGIUNGONO ALIAS, NON SI RINOMINA. Rinominare romperebbe chi già legge
`proposition` e `relevance` — e i due nomi hanno anche una ragione storica:
`proposition` è il nome della colonna nel DB, `relevance` è ciò che il dossier
misura. La cura non decide quale sia giusto: fa in modo che chi cerca l'altro
lo trovi.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

DOMANDA = "Quanti metri quadrati ha il magazzino?"


@pytest.fixture()
def mem(tmp_path):
    m = Memory(str(tmp_path / "s.db"))
    m.add("Il magazzino centrale ha 4200 metri quadrati.", topic="az/mag")
    return m


def test_il_dossier_porta_anche_i_nomi_di_recall(mem):
    """IL CUORE: chi conosce `recall` cerca `text` e `score` nel dossier."""
    fatti = mem.explain(DOMANDA, k=3, min_relevance=0.0).get("facts") or []
    assert fatti, "il banco non produce fatti: rivedilo prima di leggere oltre"
    f = fatti[0]
    assert f.get("text") == f.get("proposition")
    assert f.get("score") == f.get("relevance")


def test_i_nomi_STORICI_restano(mem):
    """IL PRESIDIO: chi già legge `proposition` e `relevance` non si accorge
    di nulla. Un alias aggiunge, non sposta."""
    fatti = mem.explain(DOMANDA, k=3, min_relevance=0.0).get("facts") or []
    f = fatti[0]
    assert "proposition" in f and "relevance" in f
    assert "4200" in str(f["proposition"])


def test_recall_non_cambia(mem):
    """L'altra metà: la superficie che già usava `text`/`score` resta
    identica — la cura è a senso unico, verso il dossier."""
    h = mem.recall(DOMANDA, k=1)[0]
    assert "text" in h and "score" in h
    assert "4200" in str(h["text"])


def test_CONTROLLO_POSITIVO_le_due_superfici_parlano_dello_stesso_fatto(mem):
    """Se questo cade è rotto il banco: stiamo confrontando due risposte che
    non riguardano lo stesso fatto, e i nomi delle chiavi non c'entrano."""
    h = mem.recall(DOMANDA, k=1)[0]
    f = (mem.explain(DOMANDA, k=1, min_relevance=0.0).get("facts") or [{}])[0]
    assert h.get("id") == f.get("id"), (h.get("id"), f.get("id"))
