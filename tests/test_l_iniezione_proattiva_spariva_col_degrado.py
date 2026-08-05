"""L'iniezione proattiva spariva quando l'encoder era lento.

SESTA SUPERFICIE con lo stesso difetto, e l'ultima della mappa che nessuna cura
del read path avesse mai raggiunto::

    TOTALE   via SDK 21 · via `a.semantic` DIRETTO 14
    proactive_step_injector.py:100   semantic.recall_hybrid(...)

`recall_hybrid` chiama `self.recall` internamente, quindi eredita il degrado:
quando l'encoder non risponde entro il budget lo score è ``0.0`` per
costruzione — «somiglianza NON MISURATA», non «nessuna somiglianza» — e il
filtro ``if float(score) < min_similarity: continue`` taglia tutto. Misurato::

    A CALDO      hits=5   (similarity ≈ 0.509)
    DEGRADATO    hits=0

⚠️ È LA PEGGIORE DELLE SEI, e non per il numero: questa superficie inietta
contesto **proattivamente**. Sulle altre chi legge ha almeno fatto una domanda
e può insospettirsi di una risposta strana; qui il contesto semplicemente non
arriva, e nessuno ha chiesto niente su cui dubitare.

Le altre cinque generazioni della stessa cura: `explain` (29/07) ·
`hippo_facts_recall` (02/08) · `Memory.search` col degrado · `hippo_facts_recall`
col degrado · `hippo_recall_history`.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

import verimem.semantic as sem
from verimem.client import Memory
from verimem.proactive_step_injector import StepInjector

PASSO = "controlla la superficie del magazzino K-77"


@pytest.fixture()
def injector():
    m = Memory(str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    for i in range(1, 6):
        m.add(f"Il magazzino K-{70 + i} di Rovigo ha {4000 + i * 100} "
              f"metri quadrati.", topic="az/mag")

    class _Ag:
        semantic = m.semantic
        memory = m
    return StepInjector(_Ag())


@pytest.fixture()
def degradato(monkeypatch):
    monkeypatch.setattr(sem, "_encode_prepared_within_budget",
                        lambda *a, **k: None)


def test_il_contesto_arriva_anche_col_ranking_degradato(injector, degradato):
    """IL CUORE: a caldo inietta cinque fatti, degradato zero — e la soglia
    stava tagliando uno score che non era una misura di somiglianza."""
    assert injector.inject(PASSO), "l'iniezione proattiva sparisce col degrado"


def test_il_degrado_si_dichiara(injector, degradato):
    """Chi riceve il contesto deve sapere che l'ordinamento non è per
    somiglianza: qui più che altrove, perché non ha fatto nessuna domanda."""
    hits = injector.inject(PASSO)
    assert hits
    assert all(h.get("ranking") == "keyword" for h in hits), hits[0]


def test_a_caldo_una_soglia_alta_taglia_ancora(injector):
    """IL PRESIDIO. La cura toglie il taglio SOLO sul ramo degradato: dove la
    somiglianza è stata misurata, una soglia alta continua a filtrare.

    ⚠️ UN INJECTOR PER ASSERZIONE, e la prima stesura ne usava uno solo:
    `StepInjector` tiene una CACHE dei fatti già emessi (`_emitted`) apposta
    per non ripetersi fra un passo e l'altro, quindi due chiamate di seguito
    sullo stesso oggetto non sono indipendenti. Il test falliva per il proprio
    stato condiviso, non per il codice."""
    assert injector.inject(PASSO, min_similarity=0.99) == []


def test_a_caldo_non_si_dichiara_nessun_degrado(injector):
    """L'altra metà del presidio: a caldo nessuno dichiara un degrado che non
    c'è.

    ⚠️ QUI NON SI PUÒ ASSERIRE «a caldo il contesto arriva», e la prima
    stesura ci provava: sotto pytest l'embedder è uno STUB su SHA-256 dei
    token (`conftest._stub_embedding_model`), quindi il coseno è finto e
    nessun fatto supera 0.30. Fuori da pytest lo stesso banco dà `hits=5` a
    similarity ≈0.509 — la misura sta nel docstring in cima, dove è stata
    fatta. Ogni misura che passa da un coseno va fatta FUORI da pytest."""
    assert all("ranking" not in h for h in injector.inject(PASSO))


def test_il_docstring_dichiara_TUTTI_i_default_che_il_codice_ha():
    """Il docstring prometteva `min_similarity=0.55` e la firma ne aveva 0.30.

    ⚠️ LA PRIMA STESURA DI QUESTO TEST GUARDAVA UN NUMERO SOLO, e uno sweep
    sull'intero pacchetto ha trovato che nella STESSA RIGA ce n'era un altro
    sbagliato: `top_k=3` con la firma a `10`. Avevo corretto il primo e
    lasciato quello accanto — «la cura c'era e mancava lo SWEEP», addosso a me
    stessa, dentro la stessa riga di docstring.

    Ora il presidio legge TUTTI i default numerici dalla firma via `inspect` e
    verifica che il docstring non ne dichiari uno diverso. Il numero non si
    ricopia mai: si legge dal codice, così i due non possono divergere.

    (Lo sweep sull'intero pacchetto: 2825 funzioni esaminate, 8 divergenze, 7
    delle quali erano casi limite spiegati nel testo — «per_day=0 makes the
    function a no-op» — e una sola era vera. Questa.)
    """
    import inspect
    import re

    import verimem.proactive_step_injector as psi

    doc = psi.__doc__ or ""
    for nome, par in inspect.signature(StepInjector.inject).parameters.items():
        reale = par.default
        if not isinstance(reale, (int, float)) or isinstance(reale, bool):
            continue
        for m in re.finditer(rf"\b{re.escape(nome)}\s*=\s*(-?\d+(?:\.\d+)?)",
                             doc):
            assert abs(float(m.group(1)) - float(reale)) < 1e-9, (
                f"il docstring dichiara {nome}={m.group(1)} "
                f"ma la firma ha {reale}")
