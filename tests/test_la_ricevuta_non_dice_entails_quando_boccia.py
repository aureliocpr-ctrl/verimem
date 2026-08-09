"""La ricevuta diceva «the source entails this checkpoint» anche bocciando.

Trovato usando il prodotto, salvando il lavoro sul prodotto. Due `verimem
save` di fila, uno ammesso e uno quarantinato, e la riga sotto il verdetto e'
LA STESSA:

    admitted    id=bf78cad8a964 ... narrative
      grounded 99.8 — the source entails this checkpoint
    quarantined id=522e7c3bf744 ...
      grounded 3.8 — the source entails this checkpoint

Il secondo fatto e' stato quarantinato PERCHE' la source non lo implicava, e
la riga che glielo doveva dire affermava il contrario. Chi cerca di capire
perche' la sua scrittura non e' passata legge una frase che lo manda dalla
parte opposta — su un comando la cui unica ragione di esistere e' distinguere
cio' che e' verificato da cio' che e' dichiarato.

E' l'OTTAVA della classe che `test_ogni_superficie_porta_il_verdetto` chiude,
in una variante nuova: li' il numero non arrivava alla superficie, qui arriva
— 99.8 e 3.8 escono entrambi — ed e' la FRASE che lo interpreta a essere
cablata. Il commento sopra quella riga racconta che la ricevuta era gia' stata
curata perche' «looked identical either way»: quella cura distingueva
GIUDICATO da NON GIUDICATO, e ha lasciato intatto PASSATO da BOCCIATO.

Il verdetto porta gia' tutto il necessario e non c'e' niente da inventare:

    adjudication: {'disposition': 'admitted', 'score': 99.83…,
                   'threshold': 40.0, 'margin': 59.8378, …}
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from verimem import cli as cli_mod
from verimem import continuity as continuity_mod


@pytest.fixture()
def runner():
    return CliRunner()


def _esito(score: float, soglia: float = 40.0) -> dict:
    return {
        "id": "abc123",
        "stored": True,
        "status": "model_claim" if score >= soglia else "quarantined",
        "grounding_score": score,
        "warnings": [],
        "adjudication": {
            "disposition": "admitted" if score >= soglia else "quarantined",
            "score": score, "threshold": soglia,
            "margin": round(score - soglia, 4),
            "evidence_class": "cross_encoder",
        },
    }


@pytest.fixture()
def salva(monkeypatch):
    """Sostituisce solo il verdetto: la formattazione resta quella vera."""
    def _con(score: float, soglia: float = 40.0):
        # l'import e' locale alla funzione della CLI (cli.py:3654), quindi
        # si sostituisce il nome nel modulo di ORIGINE, non nel chiamante.
        monkeypatch.setattr(continuity_mod, "save_checkpoint",
                            lambda *a, **k: _esito(score, soglia))
        monkeypatch.setattr(cli_mod, "_continuity_memory", lambda *a, **k: object())
    return _con


def _stampa(runner, testo="un checkpoint qualunque"):
    res = runner.invoke(cli_mod.app, ["save", testo, "--topic", "t",
                                      "--source", "una fonte"])
    return res.output


def test_un_fatto_BOCCIATO_non_si_sente_dire_che_la_source_lo_implica(
        runner, salva):
    salva(3.8)
    out = _stampa(runner)
    assert "3.8" in out, out
    assert "the source entails this checkpoint" not in out, (
        "la ricevuta afferma l'implicazione proprio mentre la nega col "
        f"punteggio:\n{out}")


def test_un_fatto_BOCCIATO_dice_perche_e_contro_quale_soglia(runner, salva):
    """Un rifiuto senza il taglio non e' azionabile: 3.8 da solo non dice se
    manca poco o tanto, e la soglia e' gia' nel verdetto."""
    salva(3.8, soglia=40.0)
    out = _stampa(runner)
    assert "40" in out, f"la soglia non compare:\n{out}"


def test_un_fatto_AMMESSO_continua_a_dirlo(runner, salva):
    salva(99.8)
    out = _stampa(runner)
    assert "99.8" in out, out
    assert "entails" in out, (
        f"il caso che funzionava non deve smettere di funzionare:\n{out}")


def test_senza_source_il_moat_non_gira_e_la_ricevuta_lo_dice(runner, monkeypatch):
    """Il contratto che la cura precedente aveva introdotto resta: un fatto
    non giudicato non si confonde con uno giudicato e bocciato — sono due
    cose diverse e la ricevuta deve continuare a distinguerle."""
    monkeypatch.setattr(continuity_mod, "save_checkpoint", lambda *a, **k: {
        "id": "x", "stored": True, "status": "model_claim",
        "grounding_score": None, "warnings": [], "adjudication": {}})
    monkeypatch.setattr(cli_mod, "_continuity_memory", lambda *a, **k: object())
    res = runner.invoke(cli_mod.app, ["save", "senza fonte", "--topic", "t"])
    assert "not verified" in res.output, res.output
