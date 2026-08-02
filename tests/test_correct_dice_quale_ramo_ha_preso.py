"""`facts correct` stampava «admitted» proprio mentre diceva «NON ammessa».

Quando la correzione non passa, il comando NON ritira il vecchio fatto — e
quella è l'invariante che conta, verificata dall'altra istanza falsificandola
di proposito su entrambi i rami: `superseded_by` resta `None` sia con la
quarantena sia con l'ammissione graduata.

Il messaggio però si contraddiceva. L'etichetta era `disp`, la disposizione
del gate, che vale `admitted` anche quando il fatto è finito in quarantena o è
entrato in via graduata:

    admitted id=… — la correzione NON e' stata ammessa

Due affermazioni opposte nella stessa riga, e la STESSA riga per due rami
diversi: chi legge non sa se il gate ha respinto la claim o l'ha accettata a
bassa confidenza, che sono due cose da correggere in modo diverso.

È la terza volta oggi che un'etichetta di sintesi non riflette il ramo che ha
girato — dopo `44b85a2f` (il campo `moat` diceva «entails» sui respinti) e
`842816a5` (la card di `trust`).

E il `reason` del gate stampava `grounding {gscore:.0f}`: su un valore di
0.3651 si legge «grounding 0», che è il numero con cui questo prodotto dice
«nessun punteggio». Un giudizio bassissimo e un giudizio assente sono
esattamente la distinzione che tutto il resto difende.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from verimem import cli as cli_mod


class _Sm:
    """`correct` prende lo store da `m.semantic` e ci chiama `get` e
    `supersede`: il doppio espone quello che il comando usa davvero, non
    quello che sembrava servire."""

    def __init__(self):
        self.superseduti = []

    def get(self, _id):
        return _Vecchio()

    def supersede(self, old, new, **kw):
        self.superseduti.append((old, new))
        return {}


class _Vecchio:
    id = "vecchio1"
    topic = "prezzi"
    proposition = "Il piano annuale costa 100 euro."


def _esito(*, status: str, disp: str, graded: bool = False) -> dict:
    warn = [{"layer": "L4-grounding-graded", "reason": "graded admission"}] \
        if graded else []
    return {"id": "nuovo1", "stored": True, "status": status,
            "warnings": warn, "adjudication": {"disposition": disp}}


@pytest.fixture()
def cli(monkeypatch):
    sm = _Sm()

    class _M:
        semantic = sm
        def add(self, *a, **k):
            return _M.esito
    monkeypatch.setattr(cli_mod, "_open_memory", lambda *a, **k: _M())
    return _M, sm


def _correggi(cli_fx) -> str:
    res = CliRunner().invoke(
        cli_mod.app,
        ["correct", "vecchio1", "Il piano annuale costa 200 euro."])
    if res.exception and not isinstance(res.exception, SystemExit):
        raise res.exception
    return res.output


def test_una_correzione_QUARANTINATA_non_si_dice_admitted(cli):
    _M, sm = cli
    _M.esito = _esito(status="quarantined", disp="admitted")
    out = _correggi(cli)
    assert "NON e' stata ammessa" in out, out
    assert "admitted" not in out.split("—")[0], (
        f"l'etichetta dice il contrario della frase accanto:\n{out}")
    assert "quarantined" in out, out
    assert not sm.superseduti, "l'invariante: il vecchio non va ritirato"


def test_una_correzione_GRADED_si_distingue_dalla_quarantena(cli):
    """Due rami, due etichette: il gate che respinge e il gate che accetta a
    bassa confidenza si correggono in modo diverso."""
    _M, sm = cli
    _M.esito = _esito(status="model_claim", disp="admitted", graded=True)
    out = _correggi(cli)
    assert "graded" in out, out
    assert "quarantined" not in out, out
    assert not sm.superseduti


def test_una_correzione_ammessa_ritira_il_vecchio(cli):
    """Controprova: il caso che funzionava non si muove."""
    _M, sm = cli
    _M.esito = _esito(status="model_claim", disp="admitted")
    out = _correggi(cli)
    assert "superseded" in out, out
    assert sm.superseduti == [("vecchio1", "nuovo1")], sm.superseduti
