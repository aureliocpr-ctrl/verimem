"""RED test (sorella-4 loop, 2026-06-03) — L1.15 tested-detector
substring-evidence bypass via bare ``test:`` prefix.

ITEM (§8 RE-SCAN 2 P1 CORRECTNESS, ENGRAM-PRODUCTION-PLAN.md:218):
    "l1_tested_detector.py (L1.15) + L1.11 + L1.13 — substring-evidence
     ANCORA vulnerabile (la mia classe-fix era incompleta DI NUOVO)".

GUILTY CODE: engram/l1_tested_detector.py:35-56
    ``_TESTED_EVIDENCE_PREFIXES`` includes the bare prefix ``"test:"`` and
    ``_has_tested_evidence`` accepts ANY ref that ``startswith("test:")``
    with NO outcome marker (pass/green/exit0/PASS). So a confabulated
    "tutto testato" claim backed by junk evidence ``test:whatever`` is
    treated as having real test evidence → L1.15 does NOT fire → the
    anti-confab gate returns ``action="persist"`` instead of
    ``"downgrade"``. The fact lands recall-able as if verified.

The SIBLING detector l1_works_detector had this exact hole closed by
commit d138e67 (``test:`` now requires an outcome marker) + 2e8111e
(per-token match). That fix was NEVER propagated to l1_tested_detector
— "fixo l'istanza non la classe" recidiva, flagged in the plan.

This is hermetic: a real SemanticMemory is built on tmp_path
(``db_path=tmp_path / "s.db"``), NEVER the production DB ~/.verimem.
NOTE: do NOT fix the source here — only proves the hole is RED today.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.anti_confab_gate import run_validation_gate
from verimem.l1_tested_detector import detect_unsupported_tested_claim
from verimem.semantic import SemanticMemory


@pytest.fixture(autouse=True)
def _l1_strict(monkeypatch):
    # STRICT keyword-detector escalation is opt-in since the 2026-07-21 default
    # flip (keyword-only advisory by default); this file tests the strict path.
    monkeypatch.setenv("ENGRAM_L1_STRICT", "1")


class _FakeAgent:
    """Minimal agent wrapping a real hermetic SemanticMemory store."""

    def __init__(self, sm: SemanticMemory) -> None:
        self.semantic = sm


def test_bare_test_prefix_must_not_count_as_tested_evidence(
    tmp_path: Path,
) -> None:
    """A bare ``test:`` ref carries NO outcome → must NOT suppress L1.15.

    RED today: detector returns None (treats ``test:foo`` as evidence).
    """
    warning = detect_unsupported_tested_claim(
        proposition="Tutto testato e validato in produzione",
        verified_by=["test:foo"],  # no PASS/green/exit0 outcome marker
    )
    # The claim has NO real test evidence → detector MUST warn.
    assert warning is not None, (
        "L1.15 accepted bare 'test:foo' as test evidence — "
        "confabulated 'tested' claim bypasses the anti-confab detector"
    )


def test_gate_must_downgrade_tested_claim_with_junk_test_prefix(
    tmp_path: Path,
) -> None:
    """End-to-end via the gate on a hermetic SemanticMemory(tmp_path).

    Control: same claim with NO evidence downgrades (detector is wired).
    Bug (RED): same claim + bogus ``test:`` evidence PERSISTS instead of
    downgrading, so the anti-confab gate is bypassed.
    """
    sm = SemanticMemory(db_path=tmp_path / "s.db")  # hermetic, not ~/.engram
    agent = _FakeAgent(sm)

    # --- control: bare claim, no evidence → gate downgrades (sanity) ---
    control = run_validation_gate(
        proposition="Modulo testato e verificato",
        verified_by=[],
        topic="lessons/test",
        agent=agent,
        validate="fast",
    )
    assert control.action == "downgrade", (
        "precondition broken: L1.15 not wired into the gate"
    )

    # --- bug: junk 'test:' evidence must NOT suppress the downgrade ---
    result = run_validation_gate(
        proposition="Modulo testato e verificato",
        verified_by=["test:run_42"],  # no outcome marker → not real evidence
        topic="lessons/test",
        agent=agent,
        validate="fast",
    )
    layers = [w.get("layer") for w in result.warnings]
    assert result.action == "downgrade" and "L1.15" in layers, (
        "anti-confab BYPASS: a 'tested' claim backed by junk 'test:run_42' "
        f"was accepted (action={result.action!r}, layers={layers}); "
        "L1.15 must require an outcome marker like l1_works_detector (d138e67)"
    )
