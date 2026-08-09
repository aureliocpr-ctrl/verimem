"""La riga di comando diceva «0 fatti» e non diceva perché.

TROVATO USANDO IL PRODOTTO sul corpus vero, due ore dopo aver curato la stessa
cosa nell'SDK::

    verimem ask "quante volte ho parlato del pavimento?"
      -> 47 fatti su «pavimento»                          ✅
    verimem ask "quanti fatti parlano del degrado?"
      -> 0 fatti su «fatti parlano degrado»                ❌

Lo zero è l'AND su tutti i termini: nessun fatto contiene «parlano». `Memory.ask`
lo dichiara già — restituisce `per_term` con il conteggio di ogni singolo
termine — e **la CLI non lo stampava**.

⚠️ SETTIMA GENERAZIONE della classe «la cura nasce su una superficie e le altre
restano indietro», e stavolta la cura incompleta è MIA, di due ore prima. La
mappa che avevo costruito riguardava il READ path (`Memory.search` contro
`a.semantic`): questa è la stessa forma sull'asse SDK→CLI, che la mappa non
copriva.

Il codice della CLI aveva già la frase giusta, scritta per la storia dei fatti:
«passare il flag e stampare la stessa riga di prima sarebbe una porta che si
apre sul muro».
"""
from __future__ import annotations

from typer.testing import CliRunner

from verimem.cli import app


class _M:
    """Un doppio: `ask` è già testato altrove, qui conta cosa la CLI STAMPA."""

    def __init__(self, rep):
        self._rep = rep

    def ask(self, *a, **k):
        return self._rep


def _run(monkeypatch, rep, query="quanti fatti parlano del degrado?"):
    import verimem.cli as cli
    monkeypatch.setattr(cli, "_open_memory", lambda *a, **k: _M(rep))
    res = CliRunner().invoke(app, ["ask", query])
    assert res.exit_code == 0, res.output
    return res.output


def test_uno_zero_dice_quale_termine_lo_ha_azzerato(monkeypatch):
    """IL CUORE: «degrado: 12 · parlano: 0» si legge in un secondo, e la
    diagnosi la fa chi ha scritto la domanda."""
    out = _run(monkeypatch, {
        "intent": "count", "terms": "fatti parlano degrado", "count": 0,
        "per_term": {"fatti": 3, "parlano": 0, "degrado": 12},
    })
    assert "parlano" in out and "degrado" in out, out
    assert "12" in out and "0" in out, out


def test_un_conteggio_che_risponde_non_porta_la_diagnosi(monkeypatch):
    """IL PRESIDIO: la diagnosi compare solo dove serve. Un conteggio che
    risponde esce asciutto come prima."""
    out = _run(monkeypatch, {
        "intent": "count", "terms": "pavimento", "count": 47,
    }, query="quante volte ho parlato del pavimento?")
    assert "47" in out
    assert "·" not in out.replace("—", ""), out


def test_una_ricerca_normale_non_cambia(monkeypatch):
    """L'altra compatibilità: `ask` senza intento di conteggio esce identico."""
    out = _run(monkeypatch, {
        "intent": "find",
        "results": [{"text": "Il magazzino K-77 ha 4200 metri quadrati.",
                     "score": 0.9}],
    }, query="cosa dice il magazzino K-77?")
    assert "K-77" in out
