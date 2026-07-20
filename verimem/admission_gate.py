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
import threading as _threading
from dataclasses import dataclass

from ._telemetry_prefixes import TELEMETRY_TOPIC_PREFIXES as _TELEMETRY_TOPIC_PREFIXES
from .prompt_injection import detect_injection

def telemetry_route_prefixes() -> tuple[str, ...]:
    """Topic prefixes that ROUTE a write to the telemetry table — EMPTY
    unless the operator declared them (external bench 2026-07-20: on two
    foreign-domain corpora our builtin list produced ~10% knowledge false
    positives with telemetry recall 0.0 — for anyone who is not us it can
    only hurt, so a name is never a verdict unless declared).

    ``ENGRAM_TELEMETRY_PREFIXES``: comma-separated literal prefixes,
    matched case-insensitively with ``startswith`` exactly as written
    (end a namespace with ``/`` — ``mqtt`` would also match ``mqtt-notes``).
    The keyword ``builtin`` expands to our own stack's list
    (``verimem._telemetry_prefixes``) and COMPOSES: ``builtin,mqtt/`` is
    the union. Unset or empty → no routing.
    """
    import os
    raw = os.environ.get("ENGRAM_TELEMETRY_PREFIXES", "").strip()
    if not raw:
        return ()
    out: list[str] = []
    for part in raw.split(","):
        p = part.strip().lower()
        if not p:
            continue
        if p == "builtin":
            out.extend(x.lower() for x in _TELEMETRY_TOPIC_PREFIXES)
        else:
            out.append(p)
    return tuple(dict.fromkeys(out))
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
    """The admission gate is ON by default since 0.7.0.

    An EXPLICIT operator choice always wins:
      - env ``ENGRAM_ADMISSION_GATE`` in {0,off,false,no}  -> OFF (legacy:
        telemetry-topic writes admitted into the curated corpus)
      - env in {1,on,true,strict}                          -> ON
      - unset / unrecognized                               -> ON (the default)

    Rationale (2026-07-20 decision record, adversarial review GLM-5.2 +
    Kimi-K3): the measured pre-gate corpus trajectory was 75% quarantined,
    94% of it machine exhaust — a "verified memory" that admits machine
    exhaust as curated facts out of the box is a false claim. The flip is
    not silent: the first routed write in a process with NO explicit env
    choice emits a one-time migration warning (see
    ``warn_first_route_once``).

    The pre-0.7.0 ``<data_dir>/ADMISSION_GATE_ON`` flag file is obsolete:
    it could only force ON, which the default now is. It is ignored — an
    explicit env OFF must win over a forgotten file.
    """
    import os
    raw = os.environ.get("ENGRAM_ADMISSION_GATE", "").strip().lower()
    if raw in ("0", "off", "false", "no"):
        return False
    return True


#: One-time-per-process latch for the first-route warning, plus its lock
#: (review round 2, GLM #3: check-then-set alone is a TOCTOU under threads
#: and the contract is "exactly one").
_ROUTE_WARNED = False
_ROUTE_WARN_LOCK = _threading.Lock()

_RECOGNIZED_OFF: tuple[str, ...] = ("0", "off", "false", "no")
_RECOGNIZED_ON: tuple[str, ...] = ("1", "on", "true", "strict")


def warn_first_route_once(*, table: str = "telemetry") -> None:
    """Tell the operator, once per process, that a write was ROUTED.

    Called by the write path AFTER a route succeeded — the message states a
    fact ("was routed"), so it must never run ahead of it (round-2 review,
    Kimi). ``table`` names where THIS route stored the payload (facts →
    ``telemetry``, episodes → ``episode_telemetry``) so the query hint in
    the message is never wrong (round-2 review, GLM). Since routing only
    happens on a DECLARED signal (a prefix in ENGRAM_TELEMETRY_PREFIXES or
    purpose="telemetry"), this is first-use observability, not a nag.

    Extra case (both reviewers, round 2): a non-empty unrecognized
    ENGRAM_ADMISSION_GATE value ("disabled", "maybe") means the operator
    THINKS they configured the gate — the one-time message then says the
    value is unrecognized and treated as ON.

    Best-effort BY DESIGN: the warn is wrapped — under ``python -W error``
    a warning becomes an exception, and a courtesy must never break (or
    degrade) the write it narrates. The latch is set only after a
    DELIVERED warn, so a transient error-filter (e.g. a library's
    catch_warnings block) does not poison it: the next route retries.
    """
    global _ROUTE_WARNED
    if _ROUTE_WARNED:
        return
    import os
    gate_raw = os.environ.get("ENGRAM_ADMISSION_GATE", "").strip()
    with _ROUTE_WARN_LOCK:
        if _ROUTE_WARNED:
            return
        if gate_raw and gate_raw.lower() not in (
                _RECOGNIZED_OFF + _RECOGNIZED_ON):
            msg = (
                f"verimem: ENGRAM_ADMISSION_GATE={gate_raw!r} is not a "
                "recognized value (use 0/off/false/no to disable, "
                "1/on/true/strict to enable) — treating it as ON. Also: "
                f"this write was routed to the '{table}' table (non-lossy)."
            )
        else:
            msg = (
                "verimem: this write matched a declared telemetry signal "
                "(ENGRAM_TELEMETRY_PREFIXES or purpose=\"telemetry\") and "
                f"was routed to the '{table}' table instead of the curated "
                f"facts corpus (non-lossy; query it with: SELECT * FROM "
                f"{table})."
            )
        try:
            import warnings
            warnings.warn(msg, UserWarning, stacklevel=3)
            _ROUTE_WARNED = True
        except Exception:
            pass


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
    _route_pfx = telemetry_route_prefixes()
    if _route_pfx and topic.lower().startswith(_route_pfx):
        ns = topic.split("/", 1)[0]
        return AdmissionVerdict(
            ROUTE_TELEMETRY,
            f"topic '{ns}/' matches a DECLARED telemetry prefix "
            "(ENGRAM_TELEMETRY_PREFIXES)", False)
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
