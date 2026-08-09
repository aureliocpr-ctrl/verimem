"""Un tool si asteneva e l'altro rispondeva, stesso corpus e stesso istante.

MISURATO sul canale degli agenti, domanda fuori tema e pavimento attivo::

    domanda: «quale database usa il cluster di produzione»
    hippo_facts_recall    items=0   si astiene
    hippo_recall_history  n=3       «Il supporto risponde in 24 ore.»

Due tool della STESSA superficie, sullo STESSO corpus, nello STESSO istante:
uno si astiene e l'altro serve tre fatti scorrelati. E `hippo_recall_history`
non accettava nemmeno `min_relevance`: non c'era modo di attivarlo.

⚠️ È LA CLASSE «la cura nasce su una superficie e le altre restano indietro»,
stavolta DENTRO la stessa superficie. La cura del pavimento su MCP è del
2026-08-02 e si era fermata a `hippo_facts_recall`; il commento che la
accompagna raccontava già la generazione precedente («la stessa forma per cui
quella del 29/07 si era fermata a `explain`»). Questa è la quinta.

TROVATO CON UNA MAPPA, non per caso: censite le chiamate che leggono il corpus,
`via SDK 21 · via semantic DIRETTO 14`. Ogni chiamata diretta è un punto che
una cura scritta su `Memory.search` non raggiunge.

Il filtro sta in `recall_with_history` e non nell'handler perché quella
funzione restituisce righe già formattate: a valle lo score non esiste più.
Un solo recall, non due.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import tempfile

import pytest

from verimem import Memory

LISTINO = ["Il piano annuale costa 100 euro.",
           "La prova gratuita dura 14 giorni.",
           "Il supporto risponde in 24 ore."]
FUORI_TEMA = "quale database usa il cluster di produzione"


@pytest.fixture()
def mcp(monkeypatch):
    from verimem import mcp_server as srv

    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    for t in LISTINO:
        m.add(t, topic="listino")

    class _Ag:
        semantic = m.semantic
        memory = m
    monkeypatch.setattr(srv, "_ag", lambda: _Ag())

    def _call(tool: str, args: dict) -> dict:
        return json.loads(asyncio.run(srv.call_tool(tool, args))[0].text)
    return _call


def test_i_due_tool_si_comportano_allo_stesso_modo(mcp):
    """IL CUORE: la stessa domanda fuori tema, lo stesso pavimento, la stessa
    risposta — cioè nessuna."""
    a = mcp("hippo_facts_recall",
            {"query": FUORI_TEMA, "k": 3, "min_relevance": 0.99})
    b = mcp("hippo_recall_history",
            {"query": FUORI_TEMA, "k": 3, "min_relevance": 0.99})
    assert not (a.get("items") or []), a
    assert not (b.get("context") or []), (
        f"un tool si astiene e l'altro risponde: {b}")


def test_il_pavimento_si_puo_passare_a_recall_history(mcp):
    """Prima non c'era modo di attivarlo su questo tool: il parametro non
    esisteva, quindi la garanzia era irraggiungibile anche volendo."""
    b = mcp("hippo_recall_history", {"query": FUORI_TEMA, "k": 3,
                                     "min_relevance": 0.99})
    assert b.get("n", len(b.get("context") or [])) == 0


def test_senza_pavimento_risponde_come_prima(mcp):
    """IL PRESIDIO: chi non chiede un pavimento riceve quello che riceveva
    prima. La cura non stringe di sua iniziativa."""
    b = mcp("hippo_recall_history", {"query": FUORI_TEMA, "k": 3})
    assert (b.get("context") or []), "senza pavimento non si deve astenere"


def test_una_domanda_in_tema_passa_il_pavimento(mcp):
    """L'ALTRO PRESIDIO, e senza questo il test sopra sarebbe soddisfatto da
    un tool che non risponde mai: con un pavimento ragionevole e una domanda
    PERTINENTE la risposta arriva."""
    b = mcp("hippo_recall_history", {"query": "quanto dura la prova gratuita",
                                     "k": 3, "min_relevance": 0.5})
    assert (b.get("context") or []), b
