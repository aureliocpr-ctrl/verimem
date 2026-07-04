"""Cycle 2026-05-27 (round 7) — L1.15 tested detector pytest."""
from __future__ import annotations

import pytest

from engram.l1_tested_detector import (
    VerificationClaimWarning,
    detect_unsupported_tested_claim,
)


class TestPositiveCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("tested", "Tutto tested last sprint"),
            ("well-tested", "Module well-tested in main"),
            ("verified", "Behavior verified empirically"),
            ("validated", "Output validated against spec"),
            ("testato", "Codice testato manualmente"),
            ("verificato", "Risultato verificato"),
            ("validato", "Algoritmo validato"),
        ],
    )
    def test_warns(self, label: str, proposition: str) -> None:
        out = detect_unsupported_tested_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is not None


class TestNegativeCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("no keyword", "Aurelio is CEO"),
            ("unrelated", "Database has rows"),
        ],
    )
    def test_no_warn(self, label: str, proposition: str) -> None:
        out = detect_unsupported_tested_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is None


class TestEvidenceSuppression:
    @pytest.mark.parametrize(
        "label,proposition,evidence",
        [
            ("pytest", "tested module", ["pytest:test_main_PASS"]),
            ("coverage", "verified", ["test_coverage:85_percent"]),
            ("ci_green", "validated", ["ci:main:green"]),
            ("review", "tested", ["review:approved"]),
            ("qa", "verified", ["qa:scenario_42_PASS"]),
        ],
    )
    def test_evidence_suppresses(
        self, label: str, proposition: str, evidence: list[str],
    ) -> None:
        out = detect_unsupported_tested_claim(
            proposition=proposition, verified_by=evidence,
        )
        assert out is None


class TestGateWire:
    def test_l115_wired(self) -> None:
        from engram.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="Code well-tested",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.15" in layers

    def test_l115_evidence_suppress(self) -> None:
        from engram.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="Module validated",
            verified_by=["pytest:test_module_PASS", "ci:main:green"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.15" not in layers
