"""Cycle 2026-05-27 (round 8) — L1.16 approval detector pytest."""
from __future__ import annotations

import pytest

from engram.l1_approval_detector import (
    ApprovalClaimWarning,
    detect_unsupported_approval_claim,
)


class TestPositiveCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("approved", "Change approved last meeting"),
            ("sign-off", "Got sign-off from team"),
            ("signed-off", "Doc signed-off by management"),
            ("authorized", "Action authorized by CEO"),
            ("blessed", "Plan blessed by stakeholders"),
            ("ratified", "Decision ratified yesterday"),
            ("approvato", "Cambiamento approvato dal team"),
            ("autorizzato", "Spesa autorizzata"),
            ("ratificato", "Piano ratificato"),
            ("firmato", "Contratto firmato"),
        ],
    )
    def test_warns(self, label: str, proposition: str) -> None:
        out = detect_unsupported_approval_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is not None


class TestNegativeCases:
    def test_no_warn_no_keyword(self) -> None:
        out = detect_unsupported_approval_claim(
            proposition="Aurelio is CEO", verified_by=[],
        )
        assert out is None


class TestEvidenceSuppression:
    @pytest.mark.parametrize(
        "label,proposition,evidence",
        [
            ("approval", "approved", ["approval:doc_123_signed"]),
            ("approver", "approved", ["approver:aurelio_signed"]),
            ("review", "approved", ["review:senior_dev_approved"]),
            ("pr", "approved", ["pr:1234_approved"]),
            ("ticket", "authorized", ["ticket:JIRA-42_approved"]),
            ("email", "approved", ["email:manager_approval"]),
            ("chat", "blessed", ["chat:slack_channel_approved"]),
        ],
    )
    def test_evidence_suppresses(
        self, label: str, proposition: str, evidence: list[str],
    ) -> None:
        out = detect_unsupported_approval_claim(
            proposition=proposition, verified_by=evidence,
        )
        assert out is None


class TestGateWire:
    def test_l116_wired(self) -> None:
        from engram.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="Decision approved by management",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.16" in layers

    def test_l116_evidence_suppress(self) -> None:
        from engram.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="Plan approved",
            verified_by=["approval:plan_v1_signed", "pr:42_approved"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.16" not in layers
