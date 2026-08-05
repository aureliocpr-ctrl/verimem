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

__all__ = ["retirement_log", "survivability_counts", "verdict_mismatches",
           "judged_true", "SERVABLE_WHERE"]

#: Sopra questo il moat ha detto «la fonte lo sostiene»: 90 è deliberatamente
#: prudente — a quel punteggio non si discute che il verdetto fosse positivo.
_VERDETTO_VERO = 90.0

#: LA CUT DI AMMISSIONE NON È UNA (misurato da ws4 il 2026-08-05): vale 40
#: (scala claude, il ripiego) oppure 70 (la calibrata del fine-tune), e quale
#: tocchi dipende da quale giudice era disponibile in quel momento — un 55
#: entra con la prima e viene trattenuto con la seconda. Qui si usa il taglio
#: BASSO di proposito: sotto 40 un fatto è respinto da QUALUNQUE cut, quindi
#: ogni riga elencata è certa e il totale è un limite inferiore, mai gonfiato.
_VERDETTO_FALSO = 40.0
#: Fra le due cut il destino non è un'incoerenza ma un'INCERTEZZA: non «il
#: prodotto ha sbagliato» bensì «l'esito dipendeva dal minuto». Categoria a
#: parte, perché fonderla con le altre due sarebbe una scelta travestita da
#: misura. Sul corpus reale: 23 fatti, tutti trattenuti, zero serviti.
_BANDA_CONTESA_ALTA = 70.0

#: The canonical "servable" predicate — the ONE definition of "alive".
#: Two implicit definitions of the same word cost ws3 three hours on
#: 2026-08-04; every counter this module exposes states its formula.
SERVABLE_WHERE = "superseded_by IS NULL AND status NOT IN ('quarantined')"


def judged_true(score: Any) -> bool:
    """Whether the moat's verdict on this fact counts as «the source
    supports it». The ONE definition — the live feed asks it about a
    single write, :func:`verdict_mismatches` asks it of the whole corpus,
    and a threshold written twice diverges (three times in two days on
    this product). ``None`` is never judged, so never true: absence of a
    verdict is not a verdict."""
    if score is None:
        return False
    try:
        return float(score) >= _VERDETTO_VERO
    except (TypeError, ValueError):
        return False


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
        ORDER BY f.superseded_at DESC, f.created_at DESC
        LIMIT ?
    """
    # ORDER BY sulla COLONNA, non su COALESCE(colonna, 0): un'espressione non
    # può usare un indice, e SQLite scansionava tutta la tabella ordinando in
    # memoria per restituire cinquanta righe (200k righe: 63.6ms contro 0.1ms
    # con idx_facts_superseded_at — 600x). L'ordine non cambia: in SQLite NULL
    # è minore di tutto, quindi in DESC finisce in fondo esattamente dove lo
    # metteva lo zero (verificato), e sul corpus reale i ritiri senza data
    # sono 0 su 1794.
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


def verdict_mismatches(sm, *, limit: int = 50,
                       topic: str | None = None) -> dict[str, Any]:
    """Where the moat's verdict and the fact's fate disagree, both ways.

    Measured on the real corpus 2026-08-05: 11 quarantined facts carry a
    verdict >= 90 (ten of them >= 99), and 10 served facts carry one below
    the admission cut — down to 0.22. Two opposite anomalies, and no view
    named either:

    - ``judged_true_but_withheld`` — the moat spent ~42 seconds to say "the
      source supports this" and the fact is kept out anyway. Work paid for
      and data lost; ws5 traced these to reports that DOCUMENT a defect,
      blocked because they contain the defect's own words.
    - ``judged_false_but_served`` — the moat said the source does not
      support it and the memory returns it as its own. The graver one for
      whoever reads: a product that serves what its own judge rejected.

    It decides nothing: it lists, like the retirement log lists pairs. The
    thresholds travel in the result because "true" and "false" here are two
    cuts, and a number without its definition is the defect this branch cures.
    """
    where_t = "AND topic LIKE ?" if topic else ""
    par: list[Any] = [topic + "%"] if topic else []
    q_true = f"""
        SELECT id AS fact_id, topic, status, grounding_score, created_at
        FROM facts
        WHERE superseded_by IS NULL AND status IN ('quarantined')
          AND grounding_score IS NOT NULL AND grounding_score >= ?
          {where_t}
        ORDER BY grounding_score DESC LIMIT ?
    """
    q_false = f"""
        SELECT id AS fact_id, topic, status, grounding_score, created_at
        FROM facts
        WHERE {SERVABLE_WHERE}
          AND grounding_score IS NOT NULL AND grounding_score < ?
          {where_t}
        ORDER BY grounding_score ASC LIMIT ?
    """
    q_banda = f"""
        SELECT id AS fact_id, topic, status, grounding_score, created_at
        FROM facts
        WHERE superseded_by IS NULL
          AND grounding_score >= ? AND grounding_score < ?
          {where_t}
        ORDER BY grounding_score ASC LIMIT ?
    """
    with sm._connect() as conn:
        veri = [dict(r) for r in conn.execute(
            q_true, (_VERDETTO_VERO, *par, int(limit)))]
        falsi = [dict(r) for r in conn.execute(
            q_false, (_VERDETTO_FALSO, *par, int(limit)))]
        banda = [dict(r) for r in conn.execute(
            q_banda, (_VERDETTO_FALSO, _BANDA_CONTESA_ALTA, *par, int(limit)))]
    return {
        "judged_true_but_withheld": veri,
        "judged_false_but_served": falsi,
        "contested_band": banda,
        "topic": topic,
        "thresholds": (
            f"judged_true = grounding_score >= {_VERDETTO_VERO:.0f} AND "
            f"quarantined · judged_false = grounding_score < "
            f"{_VERDETTO_FALSO:.0f} AND servable (LOWER BOUND: below "
            f"{_VERDETTO_FALSO:.0f} any cut rejects) · contested_band = "
            f"{_VERDETTO_FALSO:.0f}–{_BANDA_CONTESA_ALTA:.0f}, where the "
            f"outcome depended on which judge was up, not on the text"),
    }


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
        SELECT COUNT(*)                                          AS written,
               SUM(CASE WHEN {SERVABLE_WHERE} THEN 1 ELSE 0 END) AS servable,
               SUM(CASE WHEN superseded_by IS NOT NULL
                        THEN 1 ELSE 0 END)                       AS retired,
               SUM(CASE WHEN superseded_by IS NULL
                         AND status IN ('quarantined')
                        THEN 1 ELSE 0 END)                       AS quarantined,
               -- how many of the SERVED ones the moat ever judged: the
               -- question this product is sold on, and the quartet did not
               -- answer it. On the real corpus 2026-08-05: 1360 of 5631
               -- servable (24.2%) — i.e. 4271 facts served without a verdict.
               -- Counted on the servable ones only: a retired or quarantined
               -- fact is served to nobody, and including it would pad the
               -- denominator in exactly the flattering direction.
               SUM(CASE WHEN {SERVABLE_WHERE}
                         AND grounding_score IS NOT NULL
                        THEN 1 ELSE 0 END)                       AS judged
        FROM facts {where}
    """
    with sm._connect() as conn:
        row = conn.execute(sql, params).fetchone()
    # English keys: this dict travels over every port of an international
    # product (monolingual surfaces are a measured defect class here).
    return {
        "written": int(row["written"] or 0),
        "servable": int(row["servable"] or 0),
        "retired": int(row["retired"] or 0),
        "quarantined": int(row["quarantined"] or 0),
        "judged": int(row["judged"] or 0),
        "topic": topic,
        "formula": (f"servable = {SERVABLE_WHERE} · "
                    f"judged = servable AND grounding_score IS NOT NULL "
                    f"(NULL means never judged, not judged and failed)"),
    }
