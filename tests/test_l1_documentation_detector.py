"""Cycle 2026-05-27 (round 6) — L1.14 documentation detector pytest."""
from __future__ import annotations

import pytest

from verimem.l1_documentation_detector import (
    DocClaimWarning,
    detect_unsupported_doc_claim,
)


class TestPositiveCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("documented", "Module documented in latest commit"),
            ("well-documented", "API well-documented for users"),
            ("explained", "Pattern explained in comments"),
            ("described", "Behavior described in docs"),
            ("italian documentato", "Codice documentato in IT"),
            ("italian spiegato", "Algoritmo spiegato bene"),
            ("italian descritto", "Comportamento descritto"),
        ],
    )
    def test_warns_no_docs(self, label: str, proposition: str) -> None:
        out = detect_unsupported_doc_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is not None, f"{label}: expected warning"


class TestNegativeCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("no keyword", "Aurelio is CEO"),
            ("unrelated", "Database has rows"),
        ],
    )
    def test_no_warn(self, label: str, proposition: str) -> None:
        out = detect_unsupported_doc_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is None


class TestEvidenceSuppression:
    @pytest.mark.parametrize(
        "label,proposition,evidence",
        [
            ("docs", "Module documented", ["docs:/path/to/file"]),
            ("md", "API explained", ["md:/README.md"]),
            ("readme", "Behavior described", ["readme:user_guide"]),
            (
                "changelog",
                "Pattern documented",
                ["changelog:v1.0.0_added"],
            ),
            (
                "comment",
                "Code documentato",
                ["comment:src/main.py:42_added"],
            ),
            (
                "file_md",
                "Well-documented",
                ["file:docs/architecture.md"],
            ),
            (
                "file_readme",
                "Documentato",
                ["file:project/README.md"],
            ),
        ],
    )
    def test_evidence_suppresses(
        self, label: str, proposition: str, evidence: list[str],
    ) -> None:
        out = detect_unsupported_doc_claim(
            proposition=proposition, verified_by=evidence,
        )
        assert out is None


class TestGateWire:
    def test_l114_wired(self) -> None:
        from verimem.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="Module documented for users",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.14" in layers

    def test_l114_evidence_suppress(self) -> None:
        from verimem.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="API documented in main",
            verified_by=["docs:/api.md", "readme:full_guide"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.14" not in layers
