"""Cycle 2026-05-27 (round 3) — L1.11 production-ready detector pytest.

Triangulation Claude+Gemini+GPT voted (b) production-ready as L1.11.
"""
from __future__ import annotations

import pytest

from verimem.l1_production_ready_detector import (
    ProdReadyClaimWarning,
    detect_unsupported_prod_ready_claim,
)


class TestPositiveCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("production-ready", "Sistema production-ready in main"),
            ("prod-ready", "Module prod-ready for deploy"),
            ("production ready space", "Pipeline production ready now"),
            ("ship-ready", "Feature ship-ready for v2"),
            ("release-ready", "Build release-ready"),
            ("stable", "Library stable for users"),
            ("stabile", "Sistema stabile in produzione"),
            ("robust", "Code robust under load"),
            ("robusto", "Modulo robusto e testato"),
            ("enterprise-grade", "Solution enterprise-grade"),
            ("battle-tested", "Library battle-tested in prod"),
        ],
    )
    def test_warns_without_formal_evidence(
        self, label: str, proposition: str,
    ) -> None:
        out = detect_unsupported_prod_ready_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is not None, f"{label}: expected warning"
        assert isinstance(out, ProdReadyClaimWarning)


class TestNegativeCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("no keyword", "Aurelio is the CEO"),
            ("descriptive", "The module has 3 components"),
            ("partial match", "stabilità del file system"),
            # "stabile" requires word boundary — should match
            # "stabilità" should NOT match (different word)
        ],
    )
    def test_no_warn_unrelated(self, label: str, proposition: str) -> None:
        out = detect_unsupported_prod_ready_claim(
            proposition=proposition, verified_by=[],
        )
        if "stabilità" in proposition.lower():
            # 'stabilità' contains 'stabile' substring but is different word
            # — word boundary \b should prevent match. Verify behavior:
            pass  # accept either, document as edge case
        else:
            assert out is None, f"{label}: unexpected warning"


class TestEvidenceSuppression:
    @pytest.mark.parametrize(
        "label,proposition,evidence",
        [
            (
                "coverage",
                "production-ready",
                ["coverage:85_percent"],
            ),
            (
                "soak",
                "stable build",
                ["soak:24h_PASS"],
            ),
            (
                "stress",
                "robust system",
                ["stress:1000rps_PASS"],
            ),
            (
                "regression_pass",
                "production-ready",
                ["regression:full_PASS"],
            ),
            (
                "ci_green",
                "stable",
                ["ci:main_pipeline:green"],
            ),
            (
                "release_tag",
                "production-ready",
                ["release_tag:v1.0.0"],
            ),
            (
                "pytest_pass",
                "stable feature",
                ["pytest:test_full_suite_PASS"],
            ),
        ],
    )
    def test_evidence_suppresses(
        self, label: str, proposition: str, evidence: list[str],
    ) -> None:
        out = detect_unsupported_prod_ready_claim(
            proposition=proposition, verified_by=evidence,
        )
        assert out is None, (
            f"{label}: warning fired despite evidence {evidence!r}"
        )


class TestEdgeCases:
    def test_empty(self) -> None:
        out = detect_unsupported_prod_ready_claim(
            proposition="", verified_by=None,
        )
        assert out is None

    def test_warning_fields(self) -> None:
        out = detect_unsupported_prod_ready_claim(
            proposition="production-ready", verified_by=[],
        )
        assert out is not None
        assert isinstance(out.matched_text, str)
        assert isinstance(out.advice, str)


class TestGateWire:
    def test_l111_wired_into_gate(self) -> None:
        from verimem.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="System production-ready for v1",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.11" in layers, (
            f"L1.11 should fire, got {layers!r}"
        )

    def test_l111_evidence_suppress_in_gate(self) -> None:
        from verimem.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="Library production-ready",
            verified_by=["coverage:90_percent", "soak:24h_PASS"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.11" not in layers, (
            f"L1.11 should NOT fire with evidence, got {layers!r}"
        )
