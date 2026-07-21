"""Cycle 2026-05-27 — wire L1.9 performance detector into anti_confab_gate.

L1.9 ships as composable side-by-side module
(``verimem.l1_performance_detector``) and is wired into
``run_validation_gate`` so performance claims without bench evidence are
surfaced alongside L1, L1.5, L1.7, L1.8 warnings.

Contract
--------
* In tier ``fast`` and ``full``, a performance-claim proposition
  (e.g. "12s->1s game changer", "10x faster") without a bench/measure
  evidence ref produces a warning of shape::

      {"layer": "L1.9", "reason": "...", "advice": "...",
       "pattern_kind": "...", "matched_text": "..."}

* The warning drives the standard ``downgrade`` action path.
* In tier ``off``, no L1.9 check is run.
* ``force_persist=True`` keeps action=``persist`` but warning surfaced.

Closes M12 PTY hallucination gap (fact fbaa77df3860). Triangulated
Claude+Gemini+GPT in cycle 2026-05-27 → 10 patterns.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import run_validation_gate


@pytest.fixture(autouse=True)
def _l1_strict(monkeypatch):
    # STRICT keyword-detector escalation is opt-in since the 2026-07-21 default
    # flip (keyword-only advisory by default); this file tests the strict path.
    monkeypatch.setenv("ENGRAM_L1_STRICT", "1")


class TestL19WiredIntoGate:
    def test_arrow_latency_no_evidence_triggers_l19(self) -> None:
        result = run_validation_gate(
            proposition="M12 PTY 12s->1s game changer",
            verified_by=["bash:unrelated_call"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.9" in layers, (
            f"expected L1.9 in warnings, got layers={layers!r}"
        )

    def test_arrow_latency_no_evidence_downgrades(self) -> None:
        result = run_validation_gate(
            proposition="10x faster baseline",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        assert result.action == "downgrade"

    def test_bench_evidence_suppresses_l19(self) -> None:
        result = run_validation_gate(
            proposition="M12 12s->1s game changer",
            verified_by=["bench:claude_pty_3runs:avg_22.7s"],
            topic=None,
            agent=None,
            validate="fast",
        )
        layers = [w["layer"] for w in result.warnings]
        assert "L1.9" not in layers, (
            f"L1.9 should NOT fire with bench evidence, got {layers!r}"
        )

    def test_off_tier_skips_l19(self) -> None:
        result = run_validation_gate(
            proposition="12s->1s game changer",
            verified_by=[],
            topic=None,
            agent=None,
            validate="off",
        )
        assert result.action == "persist"
        assert result.warnings == []

    def test_force_persist_keeps_action_but_surfaces_warning(self) -> None:
        result = run_validation_gate(
            proposition="halves the latency",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
            force_persist=True,
        )
        assert result.action == "persist"
        layers = [w["layer"] for w in result.warnings]
        assert "L1.9" in layers, (
            f"force_persist should still surface L1.9, got {layers!r}"
        )

    def test_warning_has_pattern_kind_and_matched_text(self) -> None:
        result = run_validation_gate(
            proposition="Order of magnitude faster on hot path",
            verified_by=[],
            topic=None,
            agent=None,
            validate="fast",
        )
        l19_warnings = [w for w in result.warnings if w["layer"] == "L1.9"]
        assert l19_warnings, "expected at least one L1.9 warning"
        w = l19_warnings[0]
        assert "pattern_kind" in w
        assert "matched_text" in w
        assert w["pattern_kind"] == "order_of_magnitude"
