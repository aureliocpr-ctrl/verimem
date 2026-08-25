"""G4 dice «every README number regenerable». Il cancello non lo controllava.

Misurato il 2026-08-25 su origin/main f48a45b9, `repro_all --verify`:

    ok   lme-recall
    8/8 claims backed by artifacts
    EXIT=0

...mentre `benchmark/lme_retrieval_bench.py` NON esiste nel repository. Il
numero pubblicato (README:22, recall@5 0.87) e' VERO — il suo artefatto
`lme_s_fusionON_n500_clean.json` c'e' e dice 0.8745 su 500 domande — ma la
RICETTA che lo rigenera non c'e'. Sono due proprieta' diverse:

    artefatto presente  -> il numero ha una PROVA
    comando eseguibile  -> il numero e' RIGENERABILE

`cmd_verify` misurava solo la prima e stampava «8/8 backed», e il presidio
`test_repro_registry_g4.py` chiedeva solo che `e["command"]` fosse una
stringa NON VUOTA: un criterio sintattico su una proprieta' sostanziale.
"""
from __future__ import annotations

import importlib.util

import pytest

from benchmark import repro_all
from benchmark.repro_all import REGISTRY, cmd_verify, command_module


def test_ogni_ricetta_del_registro_e_un_modulo_che_esiste() -> None:
    """Il presidio del DIFETTO: nasce rosso finche' una ricetta manca."""
    assenti = []
    for k, e in REGISTRY.items():
        mod = command_module(e["command"])
        if mod is None:
            continue  # comando non nella forma «python -m X»: non lo giudico
        if importlib.util.find_spec(mod) is None:
            assenti.append(f"{k} -> {mod}")
    assert not assenti, (
        "il numero e' pubblicato ma il comando che lo rigenera NON ESISTE.\n"
        "G4 (RELEASE_GATE.md) promette «every README number regenerable»:\n  "
        + "\n  ".join(assenti)
    )


def test_il_cancello_grida_quando_la_ricetta_manca(monkeypatch) -> None:
    """Il presidio della CURA, con controllo positivo E negativo.

    Stesso artefatto, stesso valore: cambia SOLO il modulo del comando.
    Se il criterio fosse inerte i due casi darebbero lo stesso esito.
    """
    vera = next(
        (k, e) for k, e in REGISTRY.items()
        if importlib.util.find_spec(command_module(e["command"]) or "x") is not None
    )[1]

    # CONTROLLO POSITIVO — ricetta che esiste: il cancello deve tacere.
    monkeypatch.setattr(repro_all, "REGISTRY", {"buona": dict(vera)})
    assert cmd_verify() == 0, "una voce SANA viene segnalata: il criterio e' un falso allarme"

    # CONTROLLO NEGATIVO — stessa voce, modulo inesistente.
    rotta = dict(vera, command="python -m benchmark.questo_modulo_non_esiste --out x")
    monkeypatch.setattr(repro_all, "REGISTRY", {"rotta": rotta})
    assert cmd_verify() != 0, (
        "il cancello ha detto OK su un numero la cui ricetta non esiste"
    )


@pytest.mark.parametrize(
    "cmd, atteso",
    [
        ("python -m benchmark.foo --out x", "benchmark.foo"),
        ("python -m benchmark.foo", "benchmark.foo"),
        ("claude -p 'giudica'", None),   # non e' un «python -m»: non giudicabile
        ("", None),
    ],
)
def test_estrarre_il_modulo_non_inventa_verdetti(cmd, atteso) -> None:
    """Su un comando che non e' «python -m X» il criterio si ASTIENE.

    Un criterio sintattico sbaglia in entrambe le direzioni: qui l'astensione
    e' esplicita e visibile, non un verdetto silenzioso.
    """
    assert command_module(cmd) == atteso
