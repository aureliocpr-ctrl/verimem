"""Cycle 2026-05-27 — L1.10 works/confirmed detector pytest formal.

Closes A2 ANTI-HALL gap ("niente FUNZIONA senza pytest/Bash/tool live").
Triangulation Claude+Gemini+GPT 2026-05-27: all 3 voted L1.10 = works.
"""
from __future__ import annotations

import pytest

from engram.l1_works_detector import (
    WorksClaimWarning,
    detect_unsupported_works_claim,
)


class TestPositiveCases:
    """Works/confirmed claims WITHOUT runtime evidence → WARN."""

    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("funziona it", "Il sistema funziona correttamente"),
            ("confermato it", "Bug confermato risolto"),
            ("risolto it", "Issue risolto in produzione"),
            ("works en", "The pipeline works in main"),
            ("confirmed en", "Feature confirmed in staging"),
            ("succeeded en", "Build succeeded on first try"),
            ("passing en", "All tests passing now"),
            ("test ok ctx", "Il test e ok dopo refactor"),
            ("build ok ctx", "Build ok after CI run"),
        ],
    )
    def test_warns_without_runtime_evidence(
        self, label: str, proposition: str,
    ) -> None:
        out = detect_unsupported_works_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is not None, f"{label}: expected warning"
        assert isinstance(out, WorksClaimWarning)


class TestNegativeCases:
    """Patterns that do NOT match works/confirmed → no warn."""

    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("no keyword", "Aurelio is the CEO"),
            ("descriptive only", "The system has 3 components"),
            ("unrelated", "Database has 1000 rows"),
        ],
    )
    def test_no_warn_on_unrelated(
        self, label: str, proposition: str,
    ) -> None:
        out = detect_unsupported_works_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is None, (
            f"{label}: unexpected warning matched={out.matched_text!r}"
        )


class TestEvidenceSuppression:
    """Works claim WITH runtime evidence → no warn."""

    @pytest.mark.parametrize(
        "label,proposition,evidence",
        [
            (
                "pytest_pass",
                "Funziona correttamente",
                ["pytest:test_main_PASS"],
            ),
            (
                "bash_exit0",
                "Works as expected",
                ["bash:python_run:exit0:5"],
            ),
            (
                "cmd_exit0",
                "Confirmed deployment",
                ["cmd:deploy_status:exit0"],
            ),
            (
                "smoke_test",
                "Build ok",
                ["smoke_test:full_pipeline:PASS"],
            ),
            (
                "runtime_observation",
                "Tutto risolto",
                ["runtime:observed_5_iterations"],
            ),
            (
                "file_marker",
                "Sistema funziona",
                ["file:/tmp/proof_marker.txt"],
            ),
        ],
    )
    def test_runtime_evidence_suppresses_warning(
        self, label: str, proposition: str, evidence: list[str],
    ) -> None:
        out = detect_unsupported_works_claim(
            proposition=proposition, verified_by=evidence,
        )
        assert out is None, (
            f"{label}: warning fired despite evidence {evidence!r}"
        )


class TestEdgeCases:
    def test_empty_proposition(self) -> None:
        out = detect_unsupported_works_claim(
            proposition="", verified_by=None,
        )
        assert out is None

    def test_none_evidence(self) -> None:
        out = detect_unsupported_works_claim(
            proposition="works in production", verified_by=None,
        )
        assert out is not None

    def test_warning_fields(self) -> None:
        out = detect_unsupported_works_claim(
            proposition="funziona perfettamente", verified_by=[],
        )
        assert out is not None
        assert isinstance(out.matched_text, str)
        assert isinstance(out.advice, str)
        assert len(out.advice) > 0
