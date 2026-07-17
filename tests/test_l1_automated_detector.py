"""Cycle 2026-05-27 (round 10) — L1.18 automated detector pytest."""
from __future__ import annotations

import pytest

from verimem.l1_automated_detector import (
    AutomationClaimWarning,
    detect_unsupported_automated_claim,
)


class TestPositiveCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("automated", "Process automated nightly"),
            ("automatic", "Backup automatic daily"),
            ("automatically", "Cleanup runs automatically"),
            ("scheduled", "Job scheduled on Mondays"),
            ("periodic", "Report periodic every week"),
            ("recurring", "Task recurring monthly"),
            ("automatizzato", "Backup automatizzato"),
            ("programmato", "Job programmato"),
            ("schedulato", "Task schedulato"),
            ("periodico", "Report periodico"),
        ],
    )
    def test_warns(self, label: str, proposition: str) -> None:
        out = detect_unsupported_automated_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is not None


class TestNegativeCases:
    def test_no_warn_no_keyword(self) -> None:
        out = detect_unsupported_automated_claim(
            proposition="Aurelio is CEO", verified_by=[],
        )
        assert out is None


class TestEvidenceSuppression:
    @pytest.mark.parametrize(
        "label,proposition,evidence",
        [
            ("cron", "automated", ["cron:0_2_*_*_*"]),
            ("schedule", "scheduled", ["schedule:nightly_active"]),
            ("scheduler", "automated", ["scheduler:job_42"]),
            ("workflow", "recurring", ["workflow:weekly_backup"]),
            ("systemd", "scheduled", ["systemd:cleanup.timer"]),
            ("airflow", "periodic", ["airflow:dag_etl_daily"]),
            ("ci", "automated", ["ci:nightly:active"]),
        ],
    )
    def test_evidence_suppresses(
        self, label: str, proposition: str, evidence: list[str],
    ) -> None:
        out = detect_unsupported_automated_claim(
            proposition=proposition, verified_by=evidence,
        )
        assert out is None


class TestGateWire:
    def test_l118_wired(self) -> None:
        from verimem.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="Backup automated every day",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.18" in layers

    def test_l118_evidence_suppress(self) -> None:
        from verimem.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="System scheduled nightly",
            verified_by=["cron:0_3_*_*_*", "workflow:nightly_run"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.18" not in layers
