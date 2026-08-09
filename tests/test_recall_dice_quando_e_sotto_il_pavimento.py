"""`recall` serviva un fatto scorrelato senza avvisare.

Censimento fatto sul prodotto — store con tre fatti di listino, domanda
«quale database usa il cluster di produzione», che il corpus non può
rispondere:

    search()    -> 2 hit, best 0.7375 — «La prova gratuita dura 14 giorni.»
    ask()       -> 2 risultati
    ignorance() -> no_evidence          <- l'unica che si astiene

Il README apre con «when the evidence isn't there the system abstains instead
of guessing». Chi legge quella riga e usa `verimem recall` riceve una frase
scorrelata, con il suo punteggio e il suo stato, e niente che lo avverta.

IL PAVIMENTO C'È GIÀ ED È MISURATO: `_auto_relevance_floor`, lo stesso che
`ignorance` usa per classificare `no_evidence`. Non serviva inventarne uno —
ed è bene non farlo: alzare una soglia sul recall è l'errore pagato il 30/07
con `max(floor, noise_floor)`, scritta, misurata e ritirata perché rendeva
muta la mappa dell'ignoranza.

Quindi la riserva DICE e basta: non filtra, non cambia il verdetto, non toglie
un hit. È la stessa forma della cura su `search-docs` e di quella sul caveat
di `ignorance`: il prodotto risponde, e dichiara in che fascia si trova.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from verimem import cli as cli_mod


class _Mem:
    def __init__(self, best: float, floor: float):
        self._best, self._floor = best, floor

    def search(self, query, **kw):
        return [{"id": "f1", "text": "La prova gratuita dura 14 giorni.",
                 "score": self._best, "status": "model_claim",
                 "grounding_score": None, "topic": "listino"}]

    def _auto_relevance_floor(self):
        return self._floor


@pytest.fixture()
def con_recall(monkeypatch):
    def _con(best: float, floor: float):
        monkeypatch.setattr(cli_mod, "_open_memory",
                            lambda *a, **k: _Mem(best, floor))
    return _con


def _recall(q="quale database usa il cluster di produzione") -> str:
    return CliRunner().invoke(cli_mod.app, ["recall", q]).output


def test_sotto_il_pavimento_lo_dice(con_recall):
    con_recall(best=0.7375, floor=0.884)
    out = _recall()
    assert "pavimento" in out.lower() or "0.884" in out, (
        f"nessuna riserva su un hit sotto il pavimento misurato:\n{out}")


def test_ma_serve_comunque_il_fatto(con_recall):
    """La riserva non filtra: alzare una soglia sul recall è la cura già
    scritta, misurata e ritirata il 30/07."""
    con_recall(best=0.7375, floor=0.884)
    out = _recall()
    assert "prova gratuita" in out, out


def test_sopra_il_pavimento_non_avvisa(con_recall):
    """Un avviso su tutto è un avviso su niente."""
    con_recall(best=0.93, floor=0.884)
    out = _recall()
    assert "pavimento" not in out.lower(), out


def test_un_pavimento_non_calcolabile_non_rompe_la_lettura(con_recall,
                                                           monkeypatch):
    """Una riserva è telemetria: non deve far cadere un comando di lettura."""
    class _Rotta(_Mem):
        def _auto_relevance_floor(self):
            raise RuntimeError("niente sonde")
    monkeypatch.setattr(cli_mod, "_open_memory",
                        lambda *a, **k: _Rotta(0.7, 0.9))
    out = _recall()
    assert "prova gratuita" in out, out
