"""Cycle 2026-05-27 (round 5) — L1.13 completion detector pytest.

Claude architectural choice post Gemini-GPT divergence: (e) complete/
done/finished claim sin closing criteria.
"""
from __future__ import annotations

import pytest

from engram.l1_completion_detector import (
    CompletionClaimWarning,
    detect_unsupported_completion_claim,
)


class TestPositiveCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("complete", "Feature complete in branch main"),
            ("completed", "Refactor completed yesterday"),
            ("done", "Task done after morning"),
            ("finished", "Migration finished on prod"),
            ("closed", "Issue closed in last sprint"),
            ("wrapped-up", "Sprint wrapped-up this Friday"),
            ("task-done", "Task-done flag set automatically"),
            ("all-done", "All-done after final review"),
            ("italian completo", "Modulo completo e pronto"),
            ("italian completato", "Lavoro completato in tempo"),
            ("italian finito", "Bug finito di fixare"),
            ("italian fatto", "Tutto fatto entro deadline"),
            ("italian chiuso", "Ticket chiuso questo turno"),
            ("italian concluso", "Sprint concluso bene"),
        ],
    )
    def test_warns_without_closing_evidence(
        self, label: str, proposition: str,
    ) -> None:
        out = detect_unsupported_completion_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is not None, f"{label}: expected warning"
        assert isinstance(out, CompletionClaimWarning)


class TestNegativeCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("no keyword", "Aurelio is CEO"),
            ("descriptive", "Database has 1000 rows"),
            ("unrelated", "The sun is hot"),
        ],
    )
    def test_no_warn_unrelated(self, label: str, proposition: str) -> None:
        out = detect_unsupported_completion_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is None, f"{label}: unexpected warning"


class TestEvidenceSuppression:
    @pytest.mark.parametrize(
        "label,proposition,evidence",
        [
            (
                "task_closed",
                "Feature done",
                ["task:JIRA-123_closed"],
            ),
            (
                "jira",
                "All done",
                ["jira:PROJ-456_resolved"],
            ),
            (
                "acceptance_test",
                "Module complete",
                ["acceptance_test:scenario_42_PASS"],
            ),
            (
                "dod",
                "Task completed",
                ["definition_of_done:checklist_met"],
            ),
            (
                "review_approved",
                "PR finished",
                ["review:senior_dev_approved"],
            ),
            (
                "pr_merged",
                "Feature done",
                ["pr:1234_merged"],
            ),
            (
                "pytest_pass",
                "Test complete",
                ["pytest:test_suite_PASS"],
            ),
            (
                "bash_exit0",
                "Build finished",
                ["bash:make_release:exit0:0"],
            ),
        ],
    )
    def test_evidence_suppresses(
        self, label: str, proposition: str, evidence: list[str],
    ) -> None:
        out = detect_unsupported_completion_claim(
            proposition=proposition, verified_by=evidence,
        )
        assert out is None, (
            f"{label}: warning fired despite evidence {evidence!r}"
        )


class TestEdgeCases:
    def test_empty(self) -> None:
        out = detect_unsupported_completion_claim(
            proposition="", verified_by=None,
        )
        assert out is None

    def test_warning_fields(self) -> None:
        out = detect_unsupported_completion_claim(
            proposition="task done", verified_by=[],
        )
        assert out is not None
        assert isinstance(out.matched_text, str)
        assert isinstance(out.advice, str)


class TestGateWire:
    def test_l113_wired(self) -> None:
        from engram.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="Feature complete and ready",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.13" in layers, f"L1.13 should fire, got {layers!r}"

    def test_l113_evidence_suppress(self) -> None:
        from engram.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="Task done on JIRA-42",
            verified_by=["task:JIRA-42_closed", "pr:567_merged"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.13" not in layers
