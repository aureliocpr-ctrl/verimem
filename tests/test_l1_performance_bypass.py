"""RED→GREEN (sorella-4, 2026-06-03) — L1.9 performance detector hardening.

BUCO: ``_has_perf_evidence`` (engram/l1_performance_detector.py:183) accetta
QUALSIASI ref col prefisso ``bench:``/``measure:``/``perf:``/``timing:``/
``latency:``/``timeit:``/``bench_run:`` come prova, anche NUDO senza alcuna
misura (``bench:slowpass``, ``latency:improved``, ``perf:better``). Così un
claim di performance confabulato ("10x faster", "12s -> 1s") passa senza una
metrica numerica verificabile — esattamente la M12-PTY-hallucination che L1.9
doveva impedire.

FIX atteso: il prefisso perf esige una METRICA = numero adiacente a un'unità
(es. ``avg_22.7s``, ``ms=120``, ``elapsed_s=0.5``). Il ref nudo NON basta.

Test al livello detector (puro, niente gate/DB/semantic). NON tocca
anti_confab_gate.py né semantic.py (altre sorelle).
"""
from __future__ import annotations

import pytest

from verimem.l1_performance_detector import (
    PerformanceClaimWarning,
    detect_unsupported_performance_claim,
)

# Claim di perf reali (scattano il detector) + evidenza-spazzatura SENZA misura.
_NUDE_BYPASS = [
    ("nx_speedup", "10x faster than baseline", ["bench:slowpass"]),
    ("arrow_latency", "Bench mostra da 12s a 1s di miglioramento", ["latency:improved"]),
    ("percent_perf", "50% speedup nel hot path", ["perf:better"]),
    ("nx_speedup", "10x faster than baseline", ["measure:much_better"]),
]

# Stesso claim + misura numerica+unità VERA: deve restare soppresso (no over-block).
_VALID_MEASURE = [
    ("bench+unit", "10x faster than baseline", ["bench:claude_pty_3runs:avg_22.7s"]),
    ("measure ms", "10x faster than baseline", ["measure:wall_clock_ms=120"]),
    ("perf elapsed_s", "10x faster than baseline", ["perf:elapsed_s=0.5"]),
]


class TestNudePerfEvidenceMustWarn:
    @pytest.mark.parametrize("label,proposition,evidence", _NUDE_BYPASS)
    def test_nude_perf_prefix_is_not_evidence(
        self, label: str, proposition: str, evidence: list[str],
    ) -> None:
        """RED: oggi il ref-spazzatura sopprime il warning → bypass."""
        out = detect_unsupported_performance_claim(
            proposition=proposition, verified_by=evidence,
        )
        assert out is not None, (
            f"{label}: BYPASS L1.9 — '{evidence[0]}' (nessuna metrica "
            f"numerica+unità) accettato come prova bench per claim "
            f"{proposition!r}; serve numero+unità verificabile"
        )
        assert isinstance(out, PerformanceClaimWarning)


class TestRealMeasurementStillSuppresses:
    @pytest.mark.parametrize("label,proposition,evidence", _VALID_MEASURE)
    def test_numeric_unit_measurement_suppresses_warning(
        self, label: str, proposition: str, evidence: list[str],
    ) -> None:
        """Non over-block: una misura numero+unità vera resta valida."""
        out = detect_unsupported_performance_claim(
            proposition=proposition, verified_by=evidence,
        )
        assert out is None, (
            f"{label}: regressione — misura valida '{evidence[0]}' "
            f"erroneamente rifiutata"
        )
