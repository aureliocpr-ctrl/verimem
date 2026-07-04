"""Cycle 181 (2026-05-23) — L2 reconciler stub: detect_l1_orphan_candidates.

Read-only detector. Returns fact_ids that are candidates for
``status='orphaned'`` flip by a future write-mode reconciler.

Composes over the cycle-128 ``anti_confabulation.SHIPPED_KEYWORDS``
detection rule but applies it at REST (post-write) instead of write-time.
The L1 gate already downgrades suspect claims to ``provisional`` /
``model_claim`` at write-time; this detector finds the ones that have
sat in that state past a grace period (default 7 days) without ever
accumulating a commit-tracking ref.

Closes gap §5 of ``docs/sota/L0-L3-anti-confab-layers.md`` (cycle 180).
The write-mode reconciler is deferred — A6 lentezza, scope chiuso.

Defensive: missing DB or SQL error → empty list, never raises.
Subscription-only contract: no LLM, no external service, pure SQLite.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from engram.anti_confabulation import SHIPPED_KEYWORDS

#: Prefixes in ``verified_by`` entries that count as commit-tracking
#: refs. If any of these is present we trust the fact a bit more and
#: do NOT mark it as an L1 orphan candidate.
_COMMIT_REF_PREFIXES = ("commit:", "pr:", "file:", "git:")


def _has_commit_ref(verified_by: str | None) -> bool:
    """Return True iff the ``verified_by`` blob contains any prefix in
    ``_COMMIT_REF_PREFIXES``.

    The corpus stores ``verified_by`` as a JSON-encoded list, but we
    only need substring matching for the prefix check, so we treat it
    as a lowercased string and look for ``"prefix:"`` occurrences.
    This is robust to JSON quoting variations + future format drift.
    """
    if not verified_by:
        return False
    vb_lower = verified_by.lower()
    return any(p in vb_lower for p in _COMMIT_REF_PREFIXES)


def detect_l1_orphan_candidates(
    db_path: Path | str,
    *,
    min_age_days: float = 7.0,
    max_n: int = 50,
    now: float | None = None,
) -> list[str]:
    """Return fact_ids that are L1-orphan candidates.

    Filter (all conjunctive):
      * ``status`` IN (``'provisional'``, ``'model_claim'``)
      * ``superseded_by`` IS NULL
      * ``created_at`` < ``now - min_age_days * 86400``
      * ``UPPER(proposition)`` contains an entry from ``SHIPPED_KEYWORDS``
      * ``verified_by`` has NO commit-tracking ref

    Args:
        db_path: path to ``semantic.db``.
        min_age_days: grace period -- facts younger than this are spared.
        max_n: cap on returned list length.
        now: epoch seconds reference clock. When None, uses
            ``time.time()`` (production default). Tests inject a fixed
            timestamp for determinism.

    Returns:
        Up to ``max_n`` fact_ids ordered oldest first (``created_at`` ASC).
        Empty list on missing DB / SQL error / no candidates.
    """
    p = Path(db_path)
    if not p.exists():
        return []
    real_now = float(now) if now is not None else time.time()
    cutoff = real_now - float(min_age_days) * 86400.0

    try:
        conn = sqlite3.connect(str(p))
        try:
            # Build a parameterised LIKE clause per keyword. We
            # over-fetch by 2× so post-filter on _has_commit_ref still
            # gives at least max_n if available.
            kw_placeholders = " OR ".join(
                ["UPPER(proposition) LIKE ?" for _ in SHIPPED_KEYWORDS]
            )
            sql = (
                "SELECT id, verified_by "
                "FROM facts "
                "WHERE status IN ('provisional', 'model_claim') "
                "  AND superseded_by IS NULL "
                "  AND created_at < ? "
                f"  AND ({kw_placeholders}) "
                "ORDER BY created_at ASC "
                "LIMIT ?"
            )
            params: list[float | str | int] = [cutoff]
            for kw in SHIPPED_KEYWORDS:
                params.append(f"%{kw}%")
            params.append(int(max_n) * 2)
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []

    out: list[str] = []
    for fact_id, verified_by in rows:
        if _has_commit_ref(verified_by):
            continue
        out.append(str(fact_id))
        if len(out) >= int(max_n):
            break
    return out


__all__ = ["detect_l1_orphan_candidates"]
