"""La porta CLI del pavimento — e le due liste vuote che non sono la stessa.

Nata da un test che è caduto da solo: `test_ogni_modo_di_search_ha_la_sua_porta`
presidia che OGNI parametro pubblico di `Memory.search` abbia la sua opzione, e
appena `min_relevance` è entrato nell'SDK ha detto:

    modi di lettura senza una porta sulla riga di comando: ['min_relevance']
    opzioni dichiarate: ['--as-of', '--deep', '--include-beliefs', '--k',
                         '--with-history']

Due cose che il cricchetto non poteva chiedere e che contano quanto la porta:

① Il valore ha DUE forme — un numero, o `auto` che delega la misura allo store.
   Un'opzione tipizzata `float` avrebbe rifiutato proprio la forma che non
   chiede di indovinare una soglia, cioè quella giusta per chi non sa che
   taglio serve al suo corpus.

② «no facts found» e «nessuno sopra il pavimento» sono ESITI DIVERSI: il corpus
   non ha nulla, oppure ha qualcosa che il pavimento nasconde. Dirli con la
   stessa frase manda chi legge a concludere che il suo store sia vuoto.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from verimem import cli as cli_mod


class _Mem:
    """Registra il pavimento ricevuto e simula il taglio."""

    def __init__(self):
        self.visto = "MAI CHIAMATA"

    def search(self, query, **kw):
        self.visto = kw.get("min_relevance")
        if self.visto:
            return []
        return [{"id": "f1", "text": "La prova gratuita dura 14 giorni.",
                 "score": 0.7375, "status": "model_claim",
                 "grounding_score": None, "topic": "listino"}]

    def _auto_relevance_floor(self):
        return 0.884


@pytest.fixture()
def mem(monkeypatch):
    m = _Mem()
    monkeypatch.setattr(cli_mod, "_open_memory", lambda *a, **k: m)
    return m


def _recall(*args):
    res = CliRunner().invoke(cli_mod.app, ["recall", "una domanda", *args])
    return res.output, res.exit_code


def test_un_numero_arriva_come_numero(mem):
    _recall("--min-relevance", "0.9")
    assert mem.visto == 0.9, mem.visto


def test_auto_arriva_come_auto(mem):
    """La forma che NON chiede di indovinare una soglia deve passare."""
    _recall("--min-relevance", "auto")
    assert mem.visto == "auto", mem.visto


def test_senza_l_opzione_non_si_impone_niente(mem):
    """Il default resta il comportamento di prima: la decisione la prende
    l'SDK leggendo l'ambiente, non questa porta."""
    _recall()
    assert mem.visto is None, mem.visto


def test_un_valore_illeggibile_si_ferma(mem):
    out, code = _recall("--min-relevance", "molto")
    assert code == 2, out
    assert "auto" in out, "il messaggio deve dire anche la forma che accetta"


def test_vuoto_per_il_pavimento_non_e_vuoto_per_il_corpus(mem):
    out, _ = _recall("--min-relevance", "0.9")
    basso = out.lower()
    assert "floor" in basso, out
    assert "no facts found" not in basso, (
        "«nessuno sopra il pavimento» detto come «non ho trovato niente»: "
        f"chi legge conclude che il suo store sia vuoto\n{out}")


def test_vuoto_senza_pavimento_resta_la_frase_di_sempre(mem, monkeypatch):
    monkeypatch.setattr(_Mem, "search", lambda self, q, **kw: [])
    out, _ = _recall()
    assert "no facts found" in out.lower(), out
