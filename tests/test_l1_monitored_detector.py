"""Cycle 2026-05-27 (round 9) — L1.17 monitored detector pytest."""
from __future__ import annotations

import pytest

from verimem.l1_monitored_detector import (
    MonitoredClaimWarning,
    detect_unsupported_monitored_claim,
)


class TestPositiveCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("monitored", "Service monitored 24/7"),
            ("observed", "Behavior observed in prod"),
            ("tracked", "Errors tracked via tool"),
            ("watched", "Endpoints watched continuously"),
            ("alerted", "Team alerted on incidents"),
            ("monitorato", "Sistema monitorato in produzione"),
            ("osservato", "Pattern osservato in live"),
            ("tracciato", "Flusso tracciato"),
        ],
    )
    def test_warns(self, label: str, proposition: str) -> None:
        out = detect_unsupported_monitored_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is not None


class TestNegativeCases:
    def test_no_warn_no_keyword(self) -> None:
        out = detect_unsupported_monitored_claim(
            proposition="Aurelio is CEO", verified_by=[],
        )
        assert out is None


class TestEvidenceSuppression:
    @pytest.mark.parametrize(
        "label,proposition,evidence",
        [
            ("dashboard", "monitored", ["dashboard:/grafana/board"]),
            ("grafana", "tracked", ["grafana:api_latency"]),
            ("alert", "alerted", ["alert:disk_full_configured"]),
            (
                "prometheus",
                "monitored",
                ["prometheus:rule_45_active"],
            ),
            ("metric", "tracked", ["metric:requests_per_second"]),
            ("sentry", "tracked", ["sentry:project_42_active"]),
            ("log", "monitored", ["log:/var/log/app.log"]),
        ],
    )
    def test_evidence_suppresses(
        self, label: str, proposition: str, evidence: list[str],
    ) -> None:
        out = detect_unsupported_monitored_claim(
            proposition=proposition, verified_by=evidence,
        )
        assert out is None


class TestGateWire:
    def test_l117_wired(self) -> None:
        from verimem.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="Service monitored 24/7",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.17" in layers

    def test_l117_evidence_suppress(self) -> None:
        from verimem.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="System tracked",
            verified_by=["dashboard:/grafana", "prometheus:rule_1"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.17" not in layers
