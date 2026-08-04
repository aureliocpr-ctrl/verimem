"""retirement_log — the window on retirements no API ever showed.

Measured 2026-08-04 (ws5, verimem-coord): after a supersession, SEVEN read
surfaces say nothing — count/get_all/quarantine_log/epistemic_health/history/
recall/search. The columns have existed since schema v2 (superseded_by/at/
reason + idx_facts_superseded_by, cycle #78); what was missing is the exposed
QUERY — the ``quarantine_log`` equivalent for retirements. On Aurelio's real
corpus that silence hid 1756 retired→killer pairs, including 30 lost handoff
reports in the very topic the instances used to report the defect.

Two functions, both read-only:

- :func:`retirement_log` — the pairs (loser, winner) newest first, each with
  topics, reason, timestamp and — since the helm (ws6 control-room) — the
  ``undo_op_id`` handle that makes the row actionable, not just visible.
  LEFT JOIN on the winner: a winner that was itself retired (the ping-pong
  produces exactly such chains) must not hide the row. Metadata by default;
  ``with_text=True`` adds propositions for the local governance queue, where
  a human judges the pair (ws5: "un operatore capisce in due secondi").

- :func:`survivability_counts` — the canonical quartet written/servable/
  retired/quarantined, together. A fact disappears in TWO ways (ws3's
  retraction, 2026-08-04 22:32: counting only ``superseded_by IS NULL``
  made a cure look done while it moved the loss from one name to the other).
  SERVABLE is the canonical metric:
  ``superseded_by IS NULL AND status NOT IN ('quarantined')``.
"""
from __future__ import annotations

from typing import Any

__all__ = ["retirement_log", "survivability_counts", "SERVABLE_WHERE"]

#: The canonical "servable" predicate — the ONE definition of "alive".
#: Two implicit definitions of the same word cost ws3 three hours on
#: 2026-08-04; every counter this module exposes states its formula.
SERVABLE_WHERE = "superseded_by IS NULL AND status NOT IN ('quarantined')"


def retirement_log(
    sm,
    *,
    limit: int = 50,
    since: float | None = None,
    topic: str | None = None,
    reason: str | None = None,
    with_text: bool = False,
) -> list[dict[str, Any]]:
    """The retirements, newest first, as (loser, winner) PAIRS.

    Args:
        sm: a :class:`~verimem.semantic.SemanticMemory`.
        limit: max rows (newest first by ``superseded_at``).
        since: epoch seconds — only retirements at/after this instant.
        topic: prefix filter on the LOSER's topic (``LIKE topic%``).
        reason: exact match on ``superseded_reason``.
        with_text: include ``loser_text``/``winner_text``. Default False —
            the network/UI feed carries metadata, never content; the
            governance queue opts in locally where judging needs the words.

    Returns:
        list of dicts: loser_id/topic/status/created_at, winner_id/topic/
        status/created_at, reason, superseded_at, reversible, undo_op_id.
        ``reversible`` is True iff a not-yet-undone, not-expired
        ``facts_undo_log`` row of op_type='supersede' exists for the loser —
        rows retired BEFORE the helm existed report False honestly.
    """
    where = ["f.superseded_by IS NOT NULL"]
    params: list[Any] = []
    if since is not None:
        where.append("f.superseded_at >= ?")
        params.append(float(since))
    if topic is not None:
        where.append("f.topic LIKE ?")
        params.append(topic + "%")
    if reason is not None:
        where.append("f.superseded_reason = ?")
        params.append(reason)
    text_cols = (",\n               f.proposition AS loser_text,"
                 "\n               w.proposition AS winner_text"
                 if with_text else "")
    sql = f"""
        SELECT f.id            AS loser_id,
               f.topic         AS loser_topic,
               f.status        AS loser_status,
               f.created_at    AS loser_created_at,
               f.superseded_by AS winner_id,
               f.superseded_at AS superseded_at,
               f.superseded_reason AS reason,
               w.topic         AS winner_topic,
               w.status        AS winner_status,
               w.created_at    AS winner_created_at,
               u.op_id         AS undo_op_id{text_cols}
        FROM facts f
        LEFT JOIN facts w ON w.id = f.superseded_by
        LEFT JOIN facts_undo_log u
               ON u.fact_id = f.id AND u.op_type = 'supersede'
              AND u.undone_at IS NULL AND u.ttl_expires_at > ?
        WHERE {" AND ".join(where)}
        ORDER BY COALESCE(f.superseded_at, 0) DESC, f.created_at DESC
        LIMIT ?
    """
    import time as _time
    with sm._connect() as conn:
        # facts_undo_log may not exist on very old stores — create it the
        # same lazy way semantic.py does, so the JOIN never crashes.
        from .undo_log import ensure_undo_table
        ensure_undo_table(conn)
        rows = conn.execute(sql, (_time.time(), *params, int(limit))).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = {k: r[k] for k in r.keys()}
        d["reversible"] = d.get("undo_op_id") is not None
        out.append(d)
    return out


def survivability_counts(sm, *, topic: str | None = None) -> dict[str, Any]:
    """The canonical quartet, together: written / servable / retired /
    quarantined(-not-retired). ``written = servable + retired + quarantined``
    by construction — the three ways a write can end, none hidden behind
    another. ``formula`` states the servable predicate so no dashboard can
    show the number without its definition (two implicit definitions of
    'alive' is exactly the defect class measured on 2026-08-04)."""
    where = ""
    params: list[Any] = []
    if topic is not None:
        where = "WHERE topic LIKE ?"
        params.append(topic + "%")
    sql = f"""
        SELECT COUNT(*)                                          AS scritti,
               SUM(CASE WHEN {SERVABLE_WHERE} THEN 1 ELSE 0 END) AS servibili,
               SUM(CASE WHEN superseded_by IS NOT NULL
                        THEN 1 ELSE 0 END)                       AS ritirati,
               SUM(CASE WHEN superseded_by IS NULL
                         AND status IN ('quarantined')
                        THEN 1 ELSE 0 END)                       AS quarantinati
        FROM facts {where}
    """
    with sm._connect() as conn:
        row = conn.execute(sql, params).fetchone()
    return {
        "scritti": int(row["scritti"] or 0),
        "servibili": int(row["servibili"] or 0),
        "ritirati": int(row["ritirati"] or 0),
        "quarantinati": int(row["quarantinati"] or 0),
        "topic": topic,
        "formula": f"servibili = {SERVABLE_WHERE}",
    }
