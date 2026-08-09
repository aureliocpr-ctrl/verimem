"""`ask` taceva dove `recall` avvisava — stesso store, stessa domanda.

Misurato su tre artefatti (repo 7bf3b6ac, wheel 00581a4f, wheel 51438109 che si
pubblica): sulla stessa domanda senza risposta e con gli stessi punteggi,

    verimem recall  -> «⚠ il migliore di questi (0.786) sta sotto il pavimento
                        che lo store ha misurato su se stesso (0.874)…»
    verimem ask     -> `intento: find` e i fatti, e basta

Le due porte rispondono alla stessa domanda: quale delle due l'utente digita
non dovrebbe decidere se riceve o no l'avviso. `ask` mostrava GIÀ il punteggio
`[0.78]` — l'informazione c'era, mancava il confronto col pavimento.

Il blocco viveva dentro `recall_cmd`: copiarlo sarebbe stata la classe «una
copia invece della superficie unica», che su questo prodotto è già costata.
È stato ESTRATTO in `_avviso_pavimento` e chiamato da entrambe.

⚠️ Solo il ramo FIND: il ramo `count` esce prima e non ha punteggi da
confrontare con un pavimento.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from verimem import cli as cli_mod


class _Mem:
    """Store finto: decide il punteggio del migliore e il pavimento."""

    def __init__(self, best: float, floor: float, intent: str = "find"):
        self._best, self._floor, self._intent = best, floor, intent

    def ask(self, query, **kw):
        if self._intent == "count":
            return {"intent": "count", "count": 47, "terms": "pavimento"}
        return {"intent": "find",
                "results": [{"id": "f1", "text": "La prova gratuita dura 14 giorni.",
                             "score": self._best, "status": "model_claim",
                             "grounding_score": None, "topic": "listino"}]}

    def _auto_relevance_floor(self):
        return self._floor


@pytest.fixture()
def con_ask(monkeypatch):
    def _con(best: float, floor: float, intent: str = "find"):
        monkeypatch.setattr(cli_mod, "_open_memory",
                            lambda *a, **k: _Mem(best, floor, intent))
    return _con


def _ask(q="quale database usa il cluster di produzione") -> str:
    return CliRunner().invoke(cli_mod.app, ["ask", q]).output


def test_sotto_il_pavimento_ask_lo_dice(con_ask):
    """Il test che deve diventare ROSSO se qualcuno spegne l'avviso di `ask`."""
    con_ask(best=0.7375, floor=0.884)
    out = _ask()
    assert "pavimento" in out.lower(), (
        "`ask` non avvisa che il migliore (0.7375) sta sotto il pavimento "
        "(0.884): è la porta che taceva mentre `recall` parlava.\n" + out)


def test_CONTROLLO_POSITIVO_sopra_il_pavimento_ask_non_avvisa(con_ask):
    """L'altra popolazione: un avviso che esce sempre non è un avviso."""
    con_ask(best=0.93, floor=0.884)
    out = _ask()
    assert "pavimento" not in out.lower(), (
        "falso allarme: il migliore (0.93) sta SOPRA il pavimento (0.884) "
        "e l'avviso è uscito lo stesso.\n" + out)


def test_il_fatto_arriva_comunque(con_ask):
    """L'avviso DICE e basta: non filtra, non toglie un risultato."""
    con_ask(best=0.7375, floor=0.884)
    assert "prova gratuita" in _ask(), "l'avviso ha mangiato il risultato"


def test_il_ramo_count_non_confronta_pavimenti(con_ask):
    """`count` esce prima: lì non ci sono punteggi, l'avviso non ha senso."""
    con_ask(best=0.0, floor=0.884, intent="count")
    out = _ask("quante volte ho parlato del pavimento?")
    assert "47" in out, out
    assert "sotto il pavimento" not in out.lower(), (
        "il ramo count non ha punteggi da confrontare: l'avviso non deve "
        "uscire.\n" + out)
