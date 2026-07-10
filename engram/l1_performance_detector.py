"""Cycle 2026-05-27 — L1.9 performance claim detector.

Aurelio direttiva 2026-05-27: prevent future M12-PTY-style hallucinations
where "X->Y latency reduction" or "N% speedup" claims are made without bench
evidence.

Empirical motivation: M12 PTY "12s->1s game changer" claim shipped without
empirical bench. Verification post hoc revealed 2-3% saving reale (cold
spawn 0.5s su 22s LLM call), making the claim unsupported by 30-40x order
of magnitude.

Composable side-by-side module: does NOT touch
``engram/anti_confab_gate.py`` directly. The detector returns a
``PerformanceClaimWarning`` instance with same shape as cycle-184 FIX
detector, so ``_l1_warnings()`` can splice it into the warnings list.

Closes gap M12-lesson of 2026-05-27 audit cycle (fact fbaa77df3860).
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# Performance claim patterns (compiled once)
# Cycle 2026-05-27 v2 — post Gemini 2.5 Pro cross-check feedback:
# - arrow_latency: REQUIRE time unit on at least ONE side (fixes FP on
#   "task ID 12 → task ID 13" and timestamps "2024-01-10 → 2024-01-11")
# - Added qualitative patterns (halve/double/order of magnitude/italian)
_PERF_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # "Xs -> Ys" / "Xms -> Yms" — UNIT REQUIRED on at least one side
    # to avoid FP on ID ranges and timestamps
    (
        "arrow_latency",
        re.compile(
            r"\b\d+(?:\.\d+)?\s*(ms|s|sec|seconds?|min|minutes?|h|hours?)\s*"
            r"(?:->|→)\s*\d+(?:\.\d+)?\s*"
            r"(?:ms|s|sec|seconds?|min|minutes?|h|hours?)?"
            r"|"
            r"\b\d+(?:\.\d+)?\s*(?:ms|s|sec|seconds?|min|minutes?|h|hours?)?\s*"
            r"(?:->|→)\s*\d+(?:\.\d+)?\s*"
            r"(ms|s|sec|seconds?|min|minutes?|h|hours?)\b",
            re.IGNORECASE,
        ),
    ),
    # NEW 2026-07-10 (red-team): absolute achieved perf value — a perf noun
    # + achievement verb + magnitude+unit ("latency dropped to 12ms",
    # "responds in 8ms"). The perf noun is REQUIRED so a wall-clock time
    # ("meeting at 3pm") never trips it.
    (
        "absolute_latency",
        re.compile(
            # NB: 'to' is deliberately NOT an achievement verb here — it would
            # swallow the "from Xs to Ys" reduction case that from_to_latency
            # owns. "dropped to 12ms" still matches via "dropped".
            r"\b(?:latency|response\s+time|p50|p95|p99|ttfb)\b"
            r"(?:\s+\w+){0,4}?\s*"
            r"(?:drop(?:ped|s)?|fell|reduced?|down|now|reach(?:ed|es)?|"
            r"hits?|is|was|at|under|below)\s+"
            r"(?:\w+\s+){0,2}?"
            r"\d+(?:\.\d+)?\s*(?:ms|µs|us|ns|s|sec|seconds?)\b"
            r"|"
            r"\b(?:responds?|replies|returns?)\s+in\s+"
            r"\d+(?:\.\d+)?\s*(?:ms|µs|us|ns|s|sec|seconds?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "absolute_throughput",
        re.compile(
            r"\b(?:throughput|qps|rps)\b"
            r"(?:\s+\w+){0,4}?\s*"
            r"(?:reach(?:ed|es)?|hit|hits|now|is|was|of|at|up\s+to)\s+"
            r"(?:\w+\s+){0,2}?\d+(?:[.,]\d+)?\s*[kKmM]?\b"
            r"|"
            r"\b\d+(?:[.,]\d+)?\s*[kKmM]?\s*"
            r"(?:qps|rps|requests?\s+per\s+second|ops/s)\b",
            re.IGNORECASE,
        ),
    ),
    # "Nx faster/slower/speedup"
    (
        "nx_speedup",
        re.compile(
            r"\b\d+(?:\.\d+)?\s*[xX]\s+"
            r"(?:faster|slower|speedup|speed.up)",
            re.IGNORECASE,
        ),
    ),
    # "N% saving/reduction/improvement/speedup"
    (
        "percent_perf",
        re.compile(
            r"\b\d+(?:\.\d+)?\s*%\s+"
            r"(?:saving|reduction|improvement|speedup|"
            r"latency|faster|slower)",
            re.IGNORECASE,
        ),
    ),
    # "game changer" marketing keyword
    (
        "game_changer",
        re.compile(r"\bgame[- ]changer\b", re.IGNORECASE),
    ),
    # NEW v2: qualitative magnitude claims (Gemini cross-check feedback)
    (
        "halves_doubles",
        re.compile(
            r"\b(?:halves?|doubles?|triples?|quadruples?)\s+"
            r"(?:the\s+)?(?:latency|throughput|speed|time|"
            r"duration|performance)",
            re.IGNORECASE,
        ),
    ),
    (
        "order_of_magnitude",
        re.compile(
            r"\border[s]?\s+of\s+magnitude\s+"
            r"(?:faster|slower|reduction|speedup|less|more)",
            re.IGNORECASE,
        ),
    ),
    # Italian qualitative — v3 require performance noun nearby
    # to avoid FP on "raddoppia la verifica" / "dimezza il rischio"
    (
        "italian_qualitative",
        re.compile(
            r"\b(?:dimezza|raddoppia|triplica|quadruplica)\s+"
            r"(?:la\s+|il\s+|i\s+|le\s+)?"
            r"(?:latenza|throughput|velocità|velocita|tempo|"
            r"performance|prestazioni)"
            r"|"
            r"\b(?:tagliato|ridotto)\s+di\s+un\s+"
            r"(?:terzo|quarto|metà|meta)\s+"
            r"(?:la\s+|il\s+)?(?:latenza|tempo|durata)?"
            r"|"
            r"\b(?:due|tre|dieci|cento)\s+volte\s+"
            r"(?:più|piu|meno)\s+(?:veloce|lento|rapido)",
            re.IGNORECASE,
        ),
    ),
    # NEW v3: "da X a Y" / "from X to Y" with time unit (GPT feedback)
    (
        "from_to_latency",
        re.compile(
            r"\b(?:da|from)\s+\d+(?:\.\d+)?\s*"
            r"(?:ms|s|sec|seconds?|min|h|hours?)\s+"
            r"(?:a|to)\s+\d+(?:\.\d+)?\s*"
            r"(?:ms|s|sec|seconds?|min|h|hours?)?",
            re.IGNORECASE,
        ),
    ),
    # NEW v3: absolute qualitative perf claims (GPT feedback)
    (
        "absolute_qualitative",
        re.compile(
            r"\b(?:instantaneous|instantaneo|istantaneo|"
            r"zero[- ]cost|zero[- ]overhead|no[- ]overhead|"
            r"production[- ]ready|production[- ]grade|"
            r"real[- ]time|realtime|real time)\b",
            re.IGNORECASE,
        ),
    ),
    # NEW v3: vague benchmark claims (GPT feedback)
    (
        "vague_benchmark",
        re.compile(
            r"\b(?:molto|drasticamente|enormemente|"
            r"significativamente|notably|drastically|significantly)"
            r"\s+(?:più|piu|more|meno|less)?\s*"
            r"(?:veloce|lento|rapido|faster|slower|"
            r"better|migliore|speedup|improvement|"
            r"miglioramento)"
            r"|"
            r"\b(?:enorme|huge|massive|substantial)\s+"
            r"(?:miglioramento|improvement|speedup|"
            r"reduction|riduzione)",
            re.IGNORECASE,
        ),
    ),
]

# Evidence prefixes that count as "bench/measure" proof
# 2026-06-14: added "stress:"/"test:" — a stress-test or perf-test ref is
# legitimate evidence. The _MEASUREMENT_RE guard below still applies, so a naked
# "stress:faster" (no number+unit) is rejected exactly like a naked "bench:".
_PERF_EVIDENCE_PREFIXES: tuple[str, ...] = (
    "bench:", "bench_run:", "measure:", "timeit:",
    "perf:", "timing:", "latency:", "stress:", "test:",
)

# FIX 2026-06-03 (sorella red-team, buco L1.9-nude-claim): un prefisso perf
# NUDO ("bench:slowpass", "latency:improved", "perf:better") veniva accettato
# come prova → un claim di performance confabulato passava senza UNA misura
# (la M12-PTY hallucination che L1.9 doveva impedire). Ora il prefisso esige
# una METRICA = numero adiacente a un'unità. Due forme: numero->unità
# ("22.7s") oppure unità=:numero ("ms=120", "elapsed_s=0.5"). Le unità di una
# sola lettera (s/h) esigono un confine non-alfabetico a sinistra, così
# "status=5" NON conta (la 's' di 'status' non è un'unità).
_PERF_UNIT = (
    r"ms|µs|us|ns|secs?|seconds?|mins?|minutes?|hrs?|hours?"
    r"|rps|qps|ops|fps|hz|kb|mb|gb|kib|mib|gib"
)
_MEASUREMENT_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:" + _PERF_UNIT + r"|s|h|%)(?![a-z])"
    r"|(?<![a-z])(?:" + _PERF_UNIT + r")\s*[=:]\s*\d+(?:\.\d+)?"
    r"|(?<![a-z])[sh]\s*[=:]\s*\d+(?:\.\d+)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PerformanceClaimWarning:
    """Warning emitted when a performance claim lacks evidence."""

    pattern_kind: str  # which pattern matched (e.g. "arrow_latency")
    matched_text: str  # exact substring that triggered
    advice: str        # human-readable suggestion


def _has_perf_evidence(verified_by: Iterable[str] | None) -> bool:
    """Return True iff ``verified_by`` contains at least one bench/measure
    evidence ref.

    Accepted shapes (case-insensitive on the prefix):
      * ``bench:`` / ``bench_run:`` / ``measure:`` / ``timeit:`` /
        ``perf:`` / ``timing:`` / ``latency:``  — explicit perf evidence
      * ``bash:<cmd>:<timing>`` with ``_ms``, ``_s_``, or ``elapsed`` in
        the body  — timing-aware shell evidence
      * ``pytest:<test>`` with ``bench`` or ``perf`` in the name  —
        benchmark test ref
    """
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        # Prefisso perf esplicito: vale SOLO se porta una metrica numero+unità.
        if any(lower.startswith(p) for p in _PERF_EVIDENCE_PREFIXES):
            if _MEASUREMENT_RE.search(lower):
                return True
            continue  # prefisso perf nudo (no misura) → non è prova
        if lower.startswith("bash:") and (
            "_ms" in lower or "_s_" in lower
            or "elapsed" in lower or "avg_" in lower
        ):
            return True
        if lower.startswith("pytest:") and (
            "bench" in lower or "perf" in lower
        ):
            return True
    return False


def detect_unsupported_performance_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> PerformanceClaimWarning | None:
    """Return a Warning if proposition contains a performance claim
    pattern AND ``verified_by`` lacks bench/measure evidence. Else None.

    Args:
        proposition: free-text proposition of the fact about to be
            persisted.
        verified_by: list-of-strings (or None) of evidence refs.

    Returns:
        ``PerformanceClaimWarning`` with kind + matched text + advice when
        the claim is unsupported; ``None`` otherwise.
    """
    if not proposition:
        return None
    matched_kind: str | None = None
    matched_text: str | None = None
    for kind, pat in _PERF_PATTERNS:
        m = pat.search(proposition)
        if m:
            matched_kind = kind
            matched_text = m.group(0)
            break
    if matched_kind is None or matched_text is None:
        return None
    if _has_perf_evidence(verified_by):
        return None
    return PerformanceClaimWarning(
        pattern_kind=matched_kind,
        matched_text=matched_text,
        advice=(
            f"Proposition contains performance claim "
            f"({matched_kind}: {matched_text!r}) but no bench/measure "
            f"evidence found in verified_by. Add at least one of: "
            f"bench:<bench_run_id>, measure:<wall_clock_ms>, "
            f"perf:<elapsed_s>, or bash:<cmd>:<timing_with_ms_or_elapsed>."
        ),
    )


__all__ = [
    "PerformanceClaimWarning",
    "detect_unsupported_performance_claim",
]
