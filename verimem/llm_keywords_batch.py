"""Cycle 168.1 (2026-05-22) — batch caller for LLM-augmented trigger_keywords.

Composes over the cycle-168 pure function
``verimem.llm_keywords_augment.extract_keywords`` and adds the missing
piece: walk ``semantic.db`` rows with NULL / shallow
``trigger_keywords``, call the injected LLM, and persist the result
via ``UPDATE facts``. The LLM call itself remains injection-only
(subscription-only per CLAUDE.md O4 — no API key inside this module).

Empirical scope (corpus audit fact ``b0ac1291108f``, 2026-05-22):
  * 1665 facts total in ``~/.engram/semantic/semantic.db``
  * 277 (16.6%) ``trigger_keywords`` NULL -- primary batch target
  * 1388 (83.4%) shallow rule-based keywords from cycle-162
    (re-augmentable when their length is below ``min_length``)

Predicate semantics
-------------------
A row is selected when all conditions hold (conjunctive):

  * ``superseded_by IS NULL`` (alive)
  * ``status NOT IN ('orphaned', 'quarantined')`` (trusted)
  * ``trigger_keywords IS NULL OR length(trigger_keywords) < min_length``
    -- either missing or shallow, both targets

Rows are processed oldest-first (``ORDER BY created_at ASC``), capped
at ``limit`` (default 10 to keep one batch tiny + cost-controlled).

Failure-mode contract
---------------------
**No single-row failure aborts the loop.** Per-row outcomes are bucketed
in the returned summary:

  * ``selected``: rows matched by the SELECT
  * ``augmented``: rows where extract_keywords returned >= 1 keyword
    AND the UPDATE statement committed
  * ``skipped_empty_llm``: rows where extract_keywords returned []
    (LLM raised, malformed JSON, missing field, empty text)
  * ``errors``: rows where the UPDATE itself raised
    ``sqlite3.Error`` (lock contention, disk full, schema mismatch)

Missing DB → returns the empty-summary dict and never opens a
connection (cost-savings + cheap to call from a hook).
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from verimem.llm_keywords_augment import extract_keywords

_EMPTY_SUMMARY: dict[str, int] = {
    "selected": 0,
    "augmented": 0,
    "skipped_empty_llm": 0,
    "errors": 0,
}


def augment_keywords_batch(
    db_path: Path | str,
    *,
    llm_callable: Callable[[str], str],
    limit: int = 10,
    min_length: int = 20,
    n_min: int = 5,
    n_max: int = 10,
) -> dict[str, int]:
    """Walk + augment + persist. Returns a per-bucket summary dict.

    Args:
        db_path: path to ``semantic.db`` (the SQLite store used by
            ``verimem.semantic.SemanticMemory``).
        llm_callable: subscription-only LLM call ``(prompt) -> raw str``.
        limit: cap on rows processed in this batch (default 10).
        min_length: threshold below which an existing keyword string
            is considered "shallow" and re-augmentable. ``20`` matches
            the cycle-162 median length empirically.
        n_min: minimum hint passed through to ``extract_keywords``.
        n_max: hard cap on keywords per fact (default 10).

    Returns:
        Summary dict with keys ``selected``, ``augmented``,
        ``skipped_empty_llm``, ``errors``. All integer counts.
    """
    p = Path(db_path)
    if not p.exists():
        return dict(_EMPTY_SUMMARY)

    summary = dict(_EMPTY_SUMMARY)
    try:
        conn = sqlite3.connect(str(p))
    except sqlite3.Error:
        return dict(_EMPTY_SUMMARY)

    try:
        try:
            rows = conn.execute(
                """
                SELECT id, proposition
                FROM facts
                WHERE superseded_by IS NULL
                  AND (status IS NULL
                       OR status NOT IN ('orphaned', 'quarantined'))
                  AND (trigger_keywords IS NULL
                       OR length(trigger_keywords) < ?)
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (int(min_length), int(limit)),
            ).fetchall()
        except sqlite3.Error:
            return dict(_EMPTY_SUMMARY)

        summary["selected"] = len(rows)

        for fact_id, proposition in rows:
            kws = extract_keywords(
                proposition or "",
                llm_callable=llm_callable,
                n_min=int(n_min),
                n_max=int(n_max),
            )
            if not kws:
                summary["skipped_empty_llm"] += 1
                continue
            try:
                conn.execute(
                    "UPDATE facts SET trigger_keywords = ? WHERE id = ?",
                    (",".join(kws), fact_id),
                )
                summary["augmented"] += 1
            except sqlite3.Error:
                summary["errors"] += 1
        conn.commit()
    finally:
        conn.close()

    return summary


__all__ = ["augment_keywords_batch"]
