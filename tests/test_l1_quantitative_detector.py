"""Cycle 2026-05-27 (round 11) — L1.19 quantitative detector pytest.

Closes Gemini-identified gap (final): absolute numeric metric claims
sin measurement source. Distinct da L1.9 comparative perf.
"""
from __future__ import annotations

import pytest

from engram.l1_quantitative_detector import (
    QuantitativeClaimWarning,
    detect_unsupported_quant_claim,
)


class TestPositiveCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("latency_ms", "Latenza is 50ms in production"),
            ("latency_en", "Response time of 200ms average"),
            ("coverage_pct", "Coverage al 95% verified"),
            ("uptime_pct", "Uptime is 99.99% last month"),
            ("scale_M_records", "Processato 1.2M records ieri"),
            ("scale_K_users", "Active 500K users last month"),
            ("scale_B_requests", "Handled 10B requests last year"),
            ("memory_MB", "Memory uses 200MB at peak"),
            ("memory_GB", "Storage 1.5GB allocated"),
        ],
    )
    def test_warns_no_measurement(
        self, label: str, proposition: str,
    ) -> None:
        out = detect_unsupported_quant_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is not None, f"{label}: expected warning"
        assert isinstance(out, QuantitativeClaimWarning)


class TestNegativeCases:
    @pytest.mark.parametrize(
        "label,proposition",
        [
            ("no metric", "Aurelio is CEO"),
            ("text only", "The system processes data"),
            ("version number", "Released v1.5.0 in march"),
        ],
    )
    def test_no_warn(self, label: str, proposition: str) -> None:
        out = detect_unsupported_quant_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is None


class TestEvidenceSuppression:
    @pytest.mark.parametrize(
        "label,proposition,evidence",
        [
            (
                "bench",
                "Latency 50ms achieved",
                ["bench:wrk_test:50ms"],
            ),
            (
                "coverage",
                "Coverage al 95%",
                ["coverage:report_2026-05-27:95"],
            ),
            (
                "query",
                "Processed 1.2M records",
                ["query:db_count:1200000"],
            ),
            (
                "profiler",
                "Memory uses 200MB",
                ["profiler:py-spy:peak_200mb"],
            ),
            (
                "report",
                "Uptime 99.99%",
                ["report:sla_q4:uptime_99.99"],
            ),
        ],
    )
    def test_evidence_suppresses(
        self, label: str, proposition: str, evidence: list[str],
    ) -> None:
        out = detect_unsupported_quant_claim(
            proposition=proposition, verified_by=evidence,
        )
        assert out is None


class TestGateWire:
    def test_l119_wired(self) -> None:
        from engram.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="Coverage al 95% verified",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.19" in layers

    def test_l119_evidence_suppress(self) -> None:
        from engram.anti_confab_gate import run_validation_gate
        result = run_validation_gate(
            proposition="Latency 50ms measured",
            verified_by=["bench:wrk_load_test:50ms"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.19" not in layers
