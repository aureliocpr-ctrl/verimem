"""Le TRE porte devono dichiarare la stessa soglia di bassa confidenza.

IL DIFETTO, ed e' mio due volte. Il 02/09 `client.py` ha preso
`_pavimento_avviso()` — la soglia dell'avviso, separata da quella del taglio,
con `ENGRAM_AVVISO_MIN_RELEVANCE`. Il 03/09 ho portato quella soglia sulla porta
MCP, **e mi sono fermato li'**: `_avviso_pavimento` (cli.py) legge ancora
`m._auto_relevance_floor()` diretto.

    SDK   `_pavimento_avviso()`   legge la variabile     (02/09)
    MCP   `_pavimento_avviso()`   legge la variabile     (03/09, bef4ac50)
    CLI   `_auto_relevance_floor` NON legge la variabile  <- questo file

⇒ chi imposta la variabile la vede valere su due porte su tre. **E il presidio
l'avevo scritto io stamattina**: «quando aggiungi una variabile a una
superficie, `grep` le altre porte che ricostruiscono lo stesso campo». Ne ho
controllate due su tre.

🔁 E RITIRO una mia affermazione, ripetuta tre volte fra ieri e oggi: «la riga
di comando non mostra MAI l'avviso, `0` occorrenze di `sotto_il_pavimento` in
`cli.py`». **Il conteggio era giusto e la conclusione sbagliata**: la CLI non usa
quel CAMPO, ne costruisce uno proprio in `_avviso_pavimento`, e avvisa eccome —
verificato eseguendo `verimem recall` sul corpus vivo::

    ⚠ il migliore di questi (0.827) sta sotto il pavimento che lo store ha
      misurato su se stesso (0.880)

⚠️ `_avviso_pavimento` e' gia' la superficie UNICA di `recall` e `ask` (estratta
per non fare «una copia invece della superficie unica»): la cura sta in un punto
solo e vale per entrambi i comandi.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from verimem import cli as cli_mod  # noqa: E402

_CALIBRATO = 0.88
_BEST = 0.90          # sopra il calibrato, sotto una soglia esplicita di 0.95


class _Mem:
    """Store finto: decide il punteggio del migliore e il pavimento calibrato."""

    def __init__(self, best: float, floor: float):
        self._best, self._floor = best, floor

    def ask(self, query, **kw):        # noqa: ARG002 — firma della porta
        return {"intent": "find",
                "results": [{"id": "f1", "text": "La prova gratuita dura 14 giorni.",
                             "score": self._best, "status": "model_claim",
                             "grounding_score": None, "topic": "listino"}]}

    def _auto_relevance_floor(self):
        return self._floor


@pytest.fixture()
def con_store(monkeypatch):
    def _con(best: float = _BEST, floor: float = _CALIBRATO):
        monkeypatch.setattr(cli_mod, "_open_memory",
                            lambda *a, **k: _Mem(best, floor))
    return _con


def _uscita(q="quale database usa il cluster di produzione") -> str:
    return CliRunner().invoke(cli_mod.app, ["ask", q]).output


def test_la_variabile_vale_anche_sulla_porta_a_riga_di_comando(con_store, monkeypatch):
    """RED prima della cura: con la variabile impostata la CLI tace.

    Migliore 0.90 e calibrato 0.88: nessun avviso (0.90 non e' sotto 0.88). Con
    la soglia dell'avviso a 0.95 l'avviso DEVE uscire e dichiarare 0.950 — che
    e' quello che fanno gia' SDK e porta MCP.
    """
    monkeypatch.setenv("ENGRAM_AVVISO_MIN_RELEVANCE", "0.95")
    con_store()
    out = _uscita()
    assert "sotto il pavimento" in out, (
        "con la soglia dell'avviso a 0.95 e il migliore a 0.90 la CLI deve "
        "avvisare: oggi legge solo il pavimento calibrato e tace")
    assert "0.950" in out, f"la CLI deve dichiarare 0.950, ha stampato:\n{out}"


def test_senza_la_variabile_la_cli_non_cambia(con_store, monkeypatch):
    """🔑 CONTROLLO: senza variabile resta il calibrato, come sempre."""
    monkeypatch.delenv("ENGRAM_AVVISO_MIN_RELEVANCE", raising=False)
    con_store(best=0.50)          # sotto il calibrato -> avvisa col calibrato
    out = _uscita()
    assert "sotto il pavimento" in out
    assert "0.880" in out, f"senza variabile deve restare 0.880, ha stampato:\n{out}"


def test_su_un_negozio_non_calibrato_la_cli_tace(con_store, monkeypatch):
    """🔑 IL CONTROLLO CHE DEVE POTER FALLIRE.

    La guardia `if _pavimento` e' la stessa che hanno SDK e porta MCP: dove il
    negozio non si e' calibrato i punteggi stanno su un'altra scala, e
    confrontarli con una soglia misurata altrove accenderebbe l'avviso su tutto.
    La cura NON deve rimuoverla — senza questo test, farlo passerebbe con gli
    altri due verdi.
    """
    monkeypatch.setenv("ENGRAM_AVVISO_MIN_RELEVANCE", "0.95")
    con_store(best=0.10, floor=0.0)
    assert "sotto il pavimento" not in _uscita(), (
        "su un negozio non calibrato la CLI deve tacere, anche con la "
        "variabile impostata")
