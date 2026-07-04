"""Cycle 2026-05-27 — L1.9 performance detector pytest formal coverage.

Closes M12 PTY hallucination lesson (fact fbaa77df3860) with engineering-
grade test coverage. 18 test cases parametrized: regression v1+v2 + GPT v3
feedback (FP version/loop/id + FN da-a/qualitative absolute/vague benchmark
+ FP fix italian metaphor).

Triangulation provenance: Claude v1 → Gemini v2 → GPT v3 → 10 patterns.
"""
from __future__ import annotations

import pytest

# RED marker: import must succeed only after L1.9 module ships
from engram.l1_performance_detector import (
    PerformanceClaimWarning,
    detect_unsupported_performance_claim,
)

# ============================================================
# Positive cases (must WARN)
# ============================================================


class TestPositiveCases:
    """Performance claims WITHOUT bench evidence → must return Warning."""

    @pytest.mark.parametrize(
        "label,proposition,expected_kind",
        [
            ("M12 original", "M12 PTY game changer 12s->1s speedup", "arrow_latency"),
            ("M12 unicode arrow", "12s→1s game changer", "arrow_latency"),
            ("nx_speedup", "10x faster than baseline", "nx_speedup"),
            ("percent_perf", "50% reduction in latency", "percent_perf"),
            ("game_changer alone", "This is a game changer", "game_changer"),
            ("halves", "Halves the latency dramatically", "halves_doubles"),
            ("doubles", "Doubles the throughput", "halves_doubles"),
            (
                "order_of_magnitude",
                "Order of magnitude faster than v1",
                "order_of_magnitude",
            ),
            (
                "italian_dimezza_perf",
                "Dimezza la latenza del sistema",
                "italian_qualitative",
            ),
            (
                "italian_due_volte",
                "Due volte piu veloce delle alternative",
                "italian_qualitative",
            ),
            (
                "from_to_en",
                "Reduced latency from 22s to 0.5s on hot path",
                "from_to_latency",
            ),
            (
                "from_to_it",
                "Bench mostra da 12s a 1s di miglioramento",
                "from_to_latency",
            ),
            (
                "absolute_instantaneo",
                "Sistema instantaneo zero-cost",
                "absolute_qualitative",
            ),
            (
                "absolute_production_ready",
                "Production-ready real-time pipeline",
                "absolute_qualitative",
            ),
            (
                "vague_molto_veloce",
                "Molto piu veloce delle alternative",
                "vague_benchmark",
            ),
            (
                "vague_drasticamente",
                "Drasticamente piu rapido",
                "vague_benchmark",
            ),
            (
                "vague_enorme",
                "Enorme miglioramento performance",
                "vague_benchmark",
            ),
            (
                "vague_significantly",
                "Significantly faster than baseline",
                "vague_benchmark",
            ),
        ],
    )
    def test_warns_without_evidence(
        self, label: str, proposition: str, expected_kind: str,
    ) -> None:
        """Each performance claim pattern must warn when verified_by is empty."""
        out = detect_unsupported_performance_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is not None, f"{label}: expected warning"
        assert isinstance(out, PerformanceClaimWarning)
        assert out.pattern_kind == expected_kind, (
            f"{label}: expected kind={expected_kind} got {out.pattern_kind}"
        )


# ============================================================
# Negative cases — FP guards (must NOT warn)
# ============================================================


class TestNegativeCases:
    """Patterns that LOOK like perf claims but must NOT warn (FP guards)."""

    @pytest.mark.parametrize(
        "label,proposition",
        [
            # GPT v3 FP guards
            ("FP id range", "Task ID 12 → task ID 13 progressed"),
            ("FP date range", "Date range 2024-01-10 → 2024-01-11"),
            ("FP version v0.53.1", "Bumped version to v0.53.1 in pyproject"),
            ("FP loop number", "Loop 516 completed successfully"),
            ("FP id number", "Item id=1000 processed correctly"),
            # GPT v3 italian metaphor FP guards (no perf noun)
            ("FP raddoppia metaphor", "Raddoppia la verifica del processo"),
            ("FP dimezza metaphor", "Dimezza il rischio operativo"),
            # No pattern at all
            ("no pattern", "Aurelio is the CEO of clp project"),
            ("no pattern factual", "Roma is the capital of Italy"),
        ],
    )
    def test_no_warn_on_non_perf_patterns(
        self, label: str, proposition: str,
    ) -> None:
        out = detect_unsupported_performance_claim(
            proposition=proposition, verified_by=[],
        )
        assert out is None, (
            f"{label}: unexpected warning kind={out.pattern_kind} "
            f"matched={out.matched_text!r}"
        )


# ============================================================
# Evidence suppression (perf claim + valid evidence → no warn)
# ============================================================


class TestEvidenceSuppression:
    """Performance claims WITH valid bench evidence must NOT warn."""

    @pytest.mark.parametrize(
        "label,proposition,evidence",
        [
            (
                "bench_prefix",
                "M12 12s→1s game changer",
                ["bench:claude_pty_3runs:avg_22.7s"],
            ),
            (
                "measure_prefix",
                "10x faster than baseline",
                ["measure:wall_clock_ms=120"],
            ),
            (
                "perf_prefix",
                "50% reduction in latency",
                ["perf:elapsed_s=0.5"],
            ),
            (
                "bash_with_elapsed",
                "Halves the latency",
                ["bash:python_bench:elapsed=1.2s"],
            ),
            (
                "bash_with_ms",
                "Doubles throughput",
                ["bash:bench_run:avg_25_ms"],
            ),
            (
                "pytest_bench",
                "Order of magnitude faster",
                ["pytest:test_bench_speedup_PASS"],
            ),
        ],
    )
    def test_evidence_suppresses_warning(
        self, label: str, proposition: str, evidence: list[str],
    ) -> None:
        out = detect_unsupported_performance_claim(
            proposition=proposition, verified_by=evidence,
        )
        assert out is None, (
            f"{label}: warning fired despite evidence {evidence!r}"
        )


# ============================================================
# Edge cases
# ============================================================


class TestEdgeCases:
    def test_empty_proposition_returns_none(self) -> None:
        out = detect_unsupported_performance_claim(
            proposition="", verified_by=None,
        )
        assert out is None

    def test_none_verified_by_treated_as_empty(self) -> None:
        out = detect_unsupported_performance_claim(
            proposition="game changer", verified_by=None,
        )
        assert out is not None  # no evidence → warn

    def test_warning_has_required_fields(self) -> None:
        out = detect_unsupported_performance_claim(
            proposition="game changer alert", verified_by=[],
        )
        assert out is not None
        assert isinstance(out.pattern_kind, str)
        assert isinstance(out.matched_text, str)
        assert isinstance(out.advice, str)
        assert len(out.advice) > 0
