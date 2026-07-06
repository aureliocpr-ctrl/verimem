"""Answer-with-history — recall context that tells the TRANSITION story.

The gem capability (iter 42): competitors serve the latest value; we KEEP the
supersession chain (who replaced what, when, why — ``superseded_by`` +
``superseded_at`` + reason) and the unresolved-conflict ledger. This module turns
both into recall context, so an answer can say:

  * "changed from X to Y on <date>"  — the transition, not just the endpoint
    (HaluMem Memory-Conflict golds narrate transitions; a reconciled store that
    serves only the current value forfeits them — measured failure mode);
  * "conflicting records: A vs B (unresolved)" — an honest memory DECLARES what
    it is not sure about instead of silently picking a side.

Pure read-side, no LLM, no schema change: it composes ``SemanticMemory.recall``
+ ``direct_predecessors`` + ``ContradictionStore.list_unresolved_for_fact``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

__all__ = ["fact_history", "history_line", "recall_with_history", "recall_as_of"]


def _iso(ts: Any) -> str:
    """Epoch → ISO date (UTC); empty string on anything unparseable."""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime(
            "%Y-%m-%d")
    except (TypeError, ValueError, OSError, OverflowError):
        return ""


def _event_ts(fact) -> Any:
    """The fact's EVENT time (v13 ``asserted_at``, when it was said/true) with a
    ``created_at`` fallback — history dates must tell the story's time, not the
    ingest batch's wall clock."""
    ts = getattr(fact, "asserted_at", None)
    return ts if ts is not None else getattr(fact, "created_at", None)


def fact_history(sm, fact_id: str, *, max_hops: int = 5) -> list:
    """Predecessors of a live fact, most recent first — the main line of the
    story. At each hop the most recently retired direct predecessor is followed
    (N-to-1 merges keep only the main line; bounded, cycle-safe). Empty for a
    root fact or an unknown id."""
    out: list = []
    seen: set[str] = {fact_id}
    cursor = fact_id
    for _ in range(max(0, int(max_hops))):
        preds = [p for p in sm.direct_predecessors(cursor)
                 if p.id not in seen]
        if not preds:
            break
        head = preds[0]
        out.append(head)
        seen.add(head.id)
        cursor = head.id
    return out


def history_line(fact, history: list, *, disputes: list[str] | None = None) -> str:
    """Render one recall-context line: current value (+since date), then the
    transition story, then any DECLARED unresolved disputes."""
    prop = (getattr(fact, "proposition", "") or "").strip()
    since = _iso(_event_ts(fact))
    line = f"{prop} [current, since {since}]" if since else prop
    for p in history:
        p_prop = (getattr(p, "proposition", "") or "").strip()
        asserted = _iso(_event_ts(p))
        until = _iso(getattr(p, "superseded_at", None))
        span = ", ".join(x for x in (f"asserted {asserted}" if asserted else "",
                                     f"until {until}" if until else "") if x)
        line += f" | PREVIOUSLY: '{p_prop}'" + (f" ({span})" if span else "")
    for d in disputes or []:
        d = (d or "").strip()
        if d:
            line += f" | DISPUTED: conflicting record '{d}' (unresolved)"
    return line


def recall_as_of(sm, query: str, *, when: float, k: int = 5) -> list[tuple]:
    """Time-travel recall over the bi-temporal store: the facts that were
    CURRENT at ``when`` — asserted on/before it (event time, ``asserted_at``
    with ``created_at`` fallback) and not yet superseded by then
    (``superseded_at`` after ``when`` counts as still-current at ``when``).

    "What did we know in March?" — point-in-time reconstruction for lawyers
    (state of knowledge at signature date), researchers (literature as of a
    date), real estate (the price back then). Composes deep recall (age hiding
    lifted — the past is old by definition) over the FULL archive including
    superseded rows, oversampled so the as-of filter doesn't starve top-k.
    Returns the same ``(Fact, score, ...)`` tuples recall returns."""
    when = float(when)
    hits = sm.recall(query or "", k=max(k * 6, k), deep=True,
                     include_superseded=True)
    out: list[tuple] = []
    for hit in hits:
        f = hit[0]
        born = getattr(f, "asserted_at", None)
        born = float(born) if born is not None else float(
            getattr(f, "created_at", 0.0) or 0.0)
        if born > when:
            continue                      # not yet asserted at `when`
        died = _died_event_ts(sm, f)
        if died is not None and died <= when:
            continue                      # already superseded by `when`
        out.append(hit)
        if len(out) >= k:
            break
    return out


def _died_event_ts(sm, fact) -> float | None:
    """EVENT time a fact stopped being current: its successor's asserted_at —
    NOT ``superseded_at``, which is transaction time (a batch ingest today of a
    2024 history supersedes everything today, making every version look
    still-current at any past ``when`` — review 5-lenti C2). Fallback to
    ``superseded_at`` when the successor is unreadable (dangling link) or
    carries no event time. None = still current."""
    succ_id = getattr(fact, "superseded_by", None)
    tx = getattr(fact, "superseded_at", None)
    if not succ_id and tx is None:
        return None
    if succ_id:
        try:
            succ = sm.get(succ_id)
        except Exception:  # noqa: BLE001 — read enrichment, degrade to tx time
            succ = None
        if succ is not None:
            ev = _event_ts(succ)
            if ev is not None:
                return float(ev)
    return float(tx) if tx is not None else None


def recall_with_history(sm, query: str, *, k: int = 5, max_hops: int = 3,
                        with_disputes: bool = True) -> list[str]:
    """Live top-k recall, each hit enriched with its transition story and its
    declared unresolved conflicts. Best-effort: a history/dispute lookup error
    degrades that hit to its plain proposition — recall itself never breaks."""
    hits = sm.recall(query or "", k=k)
    cs = None
    if with_disputes:
        try:
            from engram.contradiction import ContradictionStore
            cs = ContradictionStore(sm.db_path)
        except Exception:  # noqa: BLE001 — disputes are an enrichment, never fatal
            cs = None
    lines: list[str] = []
    for f, *_ in hits:
        try:
            hist = fact_history(sm, f.id, max_hops=max_hops)
            disputes: list[str] = []
            if cs is not None:
                for c in cs.list_unresolved_for_fact(f.id):
                    other_id = (c.fact_b_id if c.fact_a_id == f.id
                                else c.fact_a_id)
                    other = sm.get(other_id)
                    if other is not None and not getattr(
                            other, "superseded_by", None):
                        disputes.append(getattr(other, "proposition", ""))
            lines.append(history_line(f, hist, disputes=disputes))
        except Exception:  # noqa: BLE001 — enrichment must never break recall
            lines.append(getattr(f, "proposition", ""))
    return lines
