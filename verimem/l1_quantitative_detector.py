"""Cycle 2026-05-27 (round 11) — L1.19 quantitative metric claim detector.

Gemini cross-check final identificato gap critico: confabulazione di
metriche quantitative ASSOLUTE (non comparative come L1.9).

Esempi catched:
- "Latenza 50ms" sin measurement
- "Coverage al 95%" sin report
- "Processato 1.2M records" sin query/DB count
- "Memoria <200MB" sin profiling

Distinct da L1.9 (X→Y comparative + speedup) — L1.19 cattura claim su
SINGLE measurement absoluto sin proof source.

Patterns:
- Latency: "X ms/s/sec" assoluto (non con freccia → di L1.9)
- Coverage/percent: "N%" coverage/uptime/availability
- Counts: "N records/users/requests" con suffix scale (K/M/B)
- Memory: "<N MB/GB" o "uses N MB"

Evidence: bench:, measure:, coverage:, report:, query:, log:, profiler:
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

_QUANT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Absolute latency: "X ms" / "X seconds" but NOT preceded by → or "from X to"
    (
        "absolute_latency",
        re.compile(
            r"\b(?:latenza|latency|response\s*time|"
            r"durata|duration)\s*"
            r"(?:è|is|of|di|=|:)?\s*"
            r"\d+(?:\.\d+)?\s*(?:ms|s|sec|seconds?|min|h)\b",
            re.IGNORECASE,
        ),
    ),
    # Coverage/percentage assoluto: "coverage at 95%" / "95% coverage"
    (
        "percent_metric",
        re.compile(
            r"\b(?:coverage|uptime|availability|accuracy|precision|recall)\s*"
            r"(?:è|is|at|al|of|del)?\s*\d+(?:\.\d+)?\s*%"
            r"|"
            r"\b\d+(?:\.\d+)?\s*%\s+"
            r"(?:coverage|uptime|availability|accuracy|precision|recall)\b",
            re.IGNORECASE,
        ),
    ),
    # Counts with scale: "1.2M records" / "500K users" / "10B requests"
    (
        "scale_count",
        re.compile(
            r"\b\d+(?:\.\d+)?\s*[KMBT]\s+"
            r"(?:records?|users?|requests?|events?|"
            r"transactions?|operations?|rows?|messages?)\b",
            re.IGNORECASE,
        ),
    ),
    # Memory/resource: "uses 200MB" / "memoria <512MB"
    (
        "resource_usage",
        re.compile(
            r"\b(?:memoria|memory|RAM|CPU|disk|storage)\s*"
            r"(?:usage|utilizzo|consumo|uses?|utilizza|<|>|=)?\s*"
            r"<?\d+(?:\.\d+)?\s*(?:KB|MB|GB|TB|%)\b",
            re.IGNORECASE,
        ),
    ),
]

_QUANT_EVIDENCE_PREFIXES: tuple[str, ...] = (
    "bench:", "measure:", "coverage:", "report:",
    "query:", "log:", "profiler:", "metric:",
    "telemetry:", "stats:", "monitor:",
)


@dataclass(frozen=True)
class QuantitativeClaimWarning:
    pattern_kind: str
    matched_text: str
    advice: str


def _has_quant_evidence(verified_by: Iterable[str] | None) -> bool:
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        if any(lower.startswith(p) for p in _QUANT_EVIDENCE_PREFIXES):
            return True
    return False


def detect_unsupported_quant_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> QuantitativeClaimWarning | None:
    if not proposition:
        return None
    matched_kind = None
    matched_text = None
    for kind, pat in _QUANT_PATTERNS:
        m = pat.search(proposition)
        if m:
            matched_kind = kind
            matched_text = m.group(0)
            break
    if matched_kind is None or matched_text is None:
        return None
    if _has_quant_evidence(verified_by):
        return None
    return QuantitativeClaimWarning(
        pattern_kind=matched_kind,
        matched_text=matched_text,
        advice=(
            f"Proposition contains quantitative metric claim "
            f"({matched_kind}: {matched_text!r}) but no measurement "
            f"evidence in verified_by. Add at least one of: "
            f"bench:<bench_run>, measure:<value>, coverage:<report>, "
            f"report:<id>, query:<sql_result>, profiler:<output>, "
            f"metric:<source>."
        ),
    )


__all__ = ["QuantitativeClaimWarning", "detect_unsupported_quant_claim"]
