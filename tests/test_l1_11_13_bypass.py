"""RED test (sorella-4, 2026-06-03) — substring-evidence bypass su L1.11 +
L1.13, stessa CLASSE del buco chiuso in l1_works/l1_tested ma NON propagato.

Lezione applicata: fix della CLASSE, non dell'istanza (cfr.
lessons/errors/fix-class-not-instance-2026-06-02). l1_works_detector (SCAN-68)
e l1_tested_detector (2026-06-03) confrontano l'esito PER-TOKEN; L1.11 e L1.13
ancora come SUBSTRING (``in lower``) → evidenza-spazzatura li bypassa.

Proposition ISOLATE (scattano SOLO il layer target, verificato): con evidenza
finta il gate va a ``action="persist"`` PIENO (warnings=[]) — il claim
confabulato viene accettato come verificato, non declassato. Questo è il buco.

GUILTY:
  L1.11 production_ready — engram/l1_production_ready_detector.py:81-82,89-90
      ``ci:`` accetta "green"/"pass" via ``in lower`` → ``ci:passenger``
      contiene "pass" come sottostringa accidentale.
  L1.13 completion — engram/l1_completion_detector.py:69-70,85-86
      ``task:`` accetta "done"/"closed"/"resolved" via ``in lower`` →
      ``task:undone_item`` contiene "done".

Hermetic: SOLO run_validation_gate (pura, agent=None, validate="fast" → niente
L3/DB). MAI il DB reale ~/.engram. NON fixa il sorgente (lo coordina il capo).
"""
from __future__ import annotations

from engram.anti_confab_gate import run_validation_gate


def _gate(proposition: str, verified_by: list[str]):
    return run_validation_gate(
        proposition=proposition,
        verified_by=verified_by,
        topic="lessons/test",
        agent=None,
        validate="fast",
    )


def test_l1_11_production_ready_junk_ci_evidence_must_downgrade() -> None:
    """L1.11: 'ci:passenger' non è una CI verde → deve restare declassato.

    Control: claim isolata senza evidenza → downgrade + L1.11 (detector wired).
    RED: 'ci:passenger' (solo substring 'pass') oggi sopprime L1.15 e il gate
    va a persist PIENO.
    """
    control = _gate("Il modulo è enterprise-grade", [])
    assert control.action == "downgrade" and "L1.11" in [
        w.get("layer") for w in control.warnings
    ], "precondizione rotta: L1.11 non wired/non scatta sulla proposition"

    result = _gate("Il modulo è enterprise-grade", ["ci:passenger"])
    layers = [w.get("layer") for w in result.warnings]
    assert result.action == "downgrade" and "L1.11" in layers, (
        "BYPASS L1.11: 'ci:passenger' (solo substring 'pass') accettato come "
        f"evidenza CI verde → gate={result.action!r}, layers={layers}; il claim "
        "production-ready confabulato passa. Serve match PER-TOKEN "
        "(l1_works_detector.py:85-86)"
    )


def test_l1_13_completion_junk_task_evidence_must_downgrade() -> None:
    """L1.13: 'task:undone_item' non è un task chiuso → deve restare declassato.

    Control: claim isolata senza evidenza → downgrade + L1.13 (detector wired).
    RED: 'task:undone_item' (solo substring 'done') oggi → persist PIENO.
    """
    control = _gate("The migration is complete", [])
    assert control.action == "downgrade" and "L1.13" in [
        w.get("layer") for w in control.warnings
    ], "precondizione rotta: L1.13 non wired/non scatta sulla proposition"

    result = _gate("The migration is complete", ["task:undone_item"])
    layers = [w.get("layer") for w in result.warnings]
    assert result.action == "downgrade" and "L1.13" in layers, (
        "BYPASS L1.13: 'task:undone_item' (solo substring 'done') accettato "
        f"come task chiuso → gate={result.action!r}, layers={layers}; il claim "
        "'completato' confabulato passa. Serve match PER-TOKEN "
        "(l1_works_detector.py:85-86)"
    )
