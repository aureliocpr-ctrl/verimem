"""Admission gate for the curated semantic corpus (verimem.admission_gate).

The write-time discipline that keeps the *curated* memory clean WITHOUT losing
anything (the "eternal but disciplined" principle): it ROUTES / FLAGS — it never
deletes.

Empirical motivation (2026-06-04, measured READ-ONLY on the live corpus, 10143
live facts): 59.6% would be flagged by cheap signals — 55.3% telemetry, 4.6%
exact duplicates, 3.5% ungrounded model-claims, 1.7% no-topic, 0.2% markup leak.
The curated corpus is only ~40% signal. This gate is the #1 quality lever AND
the structural defense against memory-poisoning (arXiv 2601.05504 / MemoryGraft
2512.16962 = the same weak-admission hole, exploited maliciously rather than
accidentally).

Decisions (none destructive):
  ACCEPT              -> into the curated corpus.
  ROUTE_TELEMETRY     -> belongs in an events/telemetry store, NOT curated facts.
  REJECT_DUPLICATE    -> identical proposition already present (keep the first).
  REJECT_POLLUTED     -> leaked tool-call markup (sanitize before admitting).
  FLAG_INJECTION      -> prompt-injection / poisoning payload (instruction-
                         override, role-hijack, chat-template smuggling,
                         exfiltration, invisible-unicode) — quarantined out of
                         curated recall, kept for audit, never deleted.
  FLAG_LOW_PROVENANCE -> admit but mark low-trust (model_claim + no grounding).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ._telemetry_prefixes import TELEMETRY_TOPIC_PREFIXES as _TELEMETRY_TOPIC_PREFIXES
from .prompt_injection import detect_injection

# SINGLE SOURCE OF TRUTH (verimem._telemetry_prefixes) shared with the recall-time
# denylist in verimem.semantic: the read side HIDES these, this gate keeps them out
# of the curated STORE in the first place. Built from the shared tuple so read and
# write can never drift (the 2026-06-13 live-recall leak WAS exactly that drift —
# semantic's denylist had cache/ market/ citations/ but this regex did not).
_TELEMETRY_TOPIC = re.compile(
    r"^(?:" + "|".join(re.escape(p) for p in _TELEMETRY_TOPIC_PREFIXES) + r")",
    re.IGNORECASE,
)
_MARKUP_LEAK = re.compile(
    r"</?(invoke|parameter|proposition)\b|<parameter name=", re.IGNORECASE
)

ACCEPT = "accept"
ROUTE_TELEMETRY = "route_telemetry"
REJECT_DUPLICATE = "reject_duplicate"
REJECT_POLLUTED = "reject_polluted"
FLAG_LOW_PROVENANCE = "flag_low_provenance"
FLAG_INJECTION = "flag_injection"

#: KNOWN non-model_claim statuses whose trust verdict lives IN the status (the
#: gate defers to it). An EXPLICIT allowlist, not `not in (model_claim, verified)`:
#: critic LOW-5 (2026-07-16) — the inverted allowlist admitted ANY unknown/
#: malformed status string (e.g. "user_belief " with a space) with a reason
#: falsely asserting a trust verdict it never checked. An unknown status now
#: falls through to the generic path instead of getting the reassuring reason.
_TRUST_BEARING_STATUS: frozenset[str] = frozenset({
    "user_belief", "quarantined", "orphaned", "legacy_unverified", "provisional",
})


def gate_enabled() -> bool:
    """The admission gate is ON when EITHER is true (default OFF = neither):

      - env ``ENGRAM_ADMISSION_GATE`` in {1,on,true,strict}, OR
      - the flag file ``<data_dir>/ADMISSION_GATE_ON`` exists.

    The file-flag makes activation deterministic regardless of how the MCP
    server inherits its environment (env-var propagation to an MCP child is not
    guaranteed): a running server that has loaded this code picks the flag up on
    its next write. Read fresh on every call (cheap stat) so toggling needs no
    process restart once the code is loaded.
    """
    import os
    if os.environ.get("ENGRAM_ADMISSION_GATE", "").strip().lower() in (
        "1", "on", "true", "strict",
    ):
        return True
    try:
        from pathlib import Path

        from .config import CONFIG
        if (Path(CONFIG.data_dir) / "ADMISSION_GATE_ON").exists():
            return True
    except Exception:
        pass
    return False


@dataclass
class AdmissionVerdict:
    decision: str
    reason: str
    admit_to_curated: bool  # True only for ACCEPT and FLAG_LOW_PROVENANCE


def normalize_proposition(text: str | None) -> str:
    """Stable key for exact-duplicate detection (whitespace + case folded)."""
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def classify_admission(
    *,
    topic: str | None,
    proposition: str | None,
    status: str | None = "model_claim",
    writer_role: str | None = "agent_inference",
    source_episodes=None,
    seen_norms: set[str] | None = None,
) -> AdmissionVerdict:
    """Classify a candidate fact for admission to the CURATED corpus.

    Order: pollution -> telemetry-routing -> duplicate -> low-provenance -> accept.
    Never loses data: telemetry is routed elsewhere, a duplicate keeps the
    original, low-provenance is admitted-but-flagged (a memory must not silently
    forget — it must mark trust).
    """
    prop = proposition or ""
    topic = topic or ""

    if _MARKUP_LEAK.search(prop):
        return AdmissionVerdict(REJECT_POLLUTED, "leaked tool-call markup (sanitize first)", False)
    _inj = detect_injection(prop)
    if _inj.is_injection:
        return AdmissionVerdict(
            FLAG_INJECTION,
            "prompt-injection signals: " + ",".join(_inj.signals),
            False,
        )
    if _TELEMETRY_TOPIC.search(topic):
        ns = topic.split("/", 1)[0]
        return AdmissionVerdict(ROUTE_TELEMETRY, f"telemetry topic '{ns}/' belongs in events store", False)
    if seen_norms is not None:
        norm = normalize_proposition(prop)
        if norm and norm in seen_norms:
            return AdmissionVerdict(REJECT_DUPLICATE, "identical proposition already in corpus", False)
    se = source_episodes or []
    if isinstance(se, str):
        se = [s for s in se.split(",") if s.strip()]
    ungrounded = (status == "model_claim") and (not se) and (writer_role in (None, "agent_inference"))
    if ungrounded:
        return AdmissionVerdict(FLAG_LOW_PROVENANCE, "model_claim with no source_episodes / provenance", True)
    # AUDIT-LEDGER mod.1 #2 (2026-07-16): a status this gate does not evaluate
    # (user_belief, quarantined, legacy_unverified, ...) is admitted because the
    # trust verdict travels IN the status itself — the reason must say that,
    # not claim a verification that never happened here.
    if status in _TRUST_BEARING_STATUS:
        return AdmissionVerdict(
            ACCEPT, f"status '{status}' carries its own trust verdict", True)
    return AdmissionVerdict(ACCEPT, "grounded or verified", True)


def audit_corpus(db_path, *, limit: int | None = None) -> dict:
    """READ-ONLY: run the gate over a live semantic.db, return the breakdown.

    Opens the DB with mode=ro -> never writes. Decisions are mutually exclusive
    (telemetry counted as telemetry even if also duplicate). ``accept`` is the
    curated-clean count.
    """
    import sqlite3
    from collections import Counter

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    sql = (
        "SELECT topic, proposition, status, writer_role, source_episodes "
        "FROM facts WHERE superseded_by IS NULL"
    )
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = conn.execute(sql).fetchall()
    conn.close()

    counts: Counter = Counter()
    seen: set[str] = set()
    for r in rows:
        v = classify_admission(
            topic=r["topic"], proposition=r["proposition"], status=r["status"],
            writer_role=r["writer_role"], source_episodes=r["source_episodes"],
            seen_norms=seen,
        )
        counts[v.decision] += 1
        if v.admit_to_curated:
            n = normalize_proposition(r["proposition"])
            if n:
                seen.add(n)
    total = sum(counts.values()) or 1
    return {
        "total": total,
        "counts": dict(counts),
        "curated_clean": counts[ACCEPT],
        "curated_clean_pct": round(100 * counts[ACCEPT] / total, 1),
        "flagged_pct": round(100 * (total - counts[ACCEPT]) / total, 1),
    }


__all__ = [
    "classify_admission", "AdmissionVerdict", "normalize_proposition", "audit_corpus",
    "gate_enabled",
    "ACCEPT", "ROUTE_TELEMETRY", "REJECT_DUPLICATE", "REJECT_POLLUTED", "FLAG_LOW_PROVENANCE",
    "FLAG_INJECTION",
]
