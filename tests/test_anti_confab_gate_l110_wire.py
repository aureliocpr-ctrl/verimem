"""Cycle 2026-05-27 — wire L1.10 works detector into anti_confab_gate.

Triangulation Claude+Gemini+GPT all voted L1.10 = FUNZIONA/works/confirmed.
"""
from __future__ import annotations

from verimem.anti_confab_gate import run_validation_gate


class TestL110WiredIntoGate:
    def test_works_no_evidence_triggers_l110(self) -> None:
        result = run_validation_gate(
            proposition="Il sistema funziona perfettamente",
            verified_by=["bash:unrelated_call"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.10" in layers, (
            f"expected L1.10 in warnings, got layers={layers!r}"
        )

    def test_works_no_evidence_downgrades(self) -> None:
        result = run_validation_gate(
            proposition="confirmed deployment in production",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        assert result.action == "downgrade"

    def test_pytest_evidence_suppresses_l110(self) -> None:
        result = run_validation_gate(
            proposition="The feature works correctly",
            verified_by=["pytest:test_feature_PASS"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.10" not in layers, (
            f"L1.10 should NOT fire with pytest evidence, got {layers!r}"
        )

    def test_off_tier_skips_l110(self) -> None:
        result = run_validation_gate(
            proposition="tutto funziona",
            verified_by=[],
            topic=None,
            agent=None,
            validate="off",
        )
        assert result.action == "persist"

    def test_warning_has_matched_text(self) -> None:
        result = run_validation_gate(
            proposition="risolto issue in last commit",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        l110 = [w for w in result.warnings if w["layer"] == "L1.10"]
        assert l110
        assert "matched_text" in l110[0]
