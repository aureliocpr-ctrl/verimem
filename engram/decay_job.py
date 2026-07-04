"""Cycle #110.C (2026-05-16) — Confidence decay job.

Aurelio audit 2026-05-16: "fact con outcome positivo non aumentano
peso, fact stagionati non perdono peso. Sistema inerte."

This module decays the ``confidence`` of each fact in the semantic
corpus as a function of its age::

    new = max(floor, original * exp(-age / tau))

with ``age = now - fact.created_at`` (clamped at zero — see below)
and ``tau`` the time constant (default 30 days, so half-life ~21
days). A configurable floor (default 0.05) keeps a fact reachable
even after years of disuse.

Defensive choices
-----------------
* Negative age (clock skew, future timestamps) is clamped to zero so
  the formula never BOOSTS confidence. ``exp(-(-x)) > 1`` would be
  wrong here.
* The persist path uses a direct ``UPDATE`` (no re-embedding). The
  embedding is unchanged because the proposition didn't change —
  only the confidence prior.
* Idempotency: facts already at the floor are skipped from the
  ``facts_updated`` count when the recomputed value would round to
  the same floor (no spurious activity).

V1 limits (out of scope, future work)
-------------------------------------
* No ``last_reinforced_at`` column: every fact decays from its
  ``created_at``. A retrieval-based reinforcement signal will land
  in V2 as a separate column.
* tau is global (no per-topic tuning).
"""
from __future__ import annotations

import math
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .semantic import SemanticMemory

SEC_PER_DAY = 86400.0
DEFAULT_TAU_SECONDS = 30 * SEC_PER_DAY
DEFAULT_FLOOR = 0.05


# ---------------------------------------------------------------------------
# Pure decision function — no IO, fully exhaustively testable.
# ---------------------------------------------------------------------------


def compute_decayed_confidence(
    *,
    original: float,
    age_seconds: float,
    tau_seconds: float = DEFAULT_TAU_SECONDS,
    floor: float = DEFAULT_FLOOR,
) -> float:
    """Return ``max(floor, original * exp(-age / tau))``.

    Args:
        original: current confidence (0..1, but no hard cap).
        age_seconds: how long since ``created_at`` (clamped at 0).
        tau_seconds: decay time-constant. Half-life = ``tau * ln(2)``.
        floor: minimum confidence (kept reachable).

    Returns:
        Float in ``[floor, original]``. Returns ``original`` exactly
        when ``age_seconds <= 0``.
    """
    if age_seconds <= 0.0:
        return float(original)
    if tau_seconds <= 0.0:
        return max(float(floor), float(original))
    decayed = float(original) * math.exp(-float(age_seconds) / float(tau_seconds))
    return max(float(floor), decayed)


# ---------------------------------------------------------------------------
# Orchestrator — walk the corpus, apply formula, persist updates.
# ---------------------------------------------------------------------------


@contextmanager
def _connect(db_path: Any) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=60000;")
    except sqlite3.OperationalError:
        pass
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _changed(old: float, new: float, *, eps: float = 1e-6) -> bool:
    """Whether the decay produced a meaningful confidence delta."""
    return abs(old - new) > eps


def _ensure_last_decay_column(conn: sqlite3.Connection) -> None:
    """Additive, idempotent migration: ``facts.last_decay_at`` (REAL, nullable).

    Records when each fact was last decayed so a pass decays from the time
    SINCE the previous pass (NULL -> fall back to ``created_at``). Without it,
    every pass recomputes from ``created_at`` using the already-decayed
    confidence, compounding ``exp(-age_total/tau)`` and collapsing the corpus
    to the floor in O(number-of-runs) instead of real elapsed time.
    """
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN last_decay_at REAL")
    except sqlite3.OperationalError:
        pass  # column already present — additive migration is idempotent


def run_decay_pass(
    sm: SemanticMemory,
    *,
    tau_seconds: float = DEFAULT_TAU_SECONDS,
    floor: float = DEFAULT_FLOOR,
    now: float | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Walk every fact, apply the decay formula, persist updates.

    Args:
        sm: SemanticMemory whose ``facts`` table is updated in place.
        tau_seconds: decay time-constant (default 30 days).
        floor: minimum confidence (default 0.05).
        now: override the current time (used by tests for determinism).
        dry_run: count facts that WOULD change but don't write.

    Returns a summary dict::

        {
            "facts_seen": N,
            "facts_updated": K,  # rows where |new - old| > 1e-6
            "avg_confidence_before": float,
            "avg_confidence_after": float,
            "tau_seconds": ...,
            "floor": ...,
            "dry_run": bool,
            "elapsed_s": float,
        }
    """
    started_at = time.time()
    now_ts = float(now if now is not None else time.time())

    # Read all rows: id + confidence + created_at. We don't need the
    # embedding bytes or the proposition for decay.
    with _connect(sm.db_path) as conn:
        _ensure_last_decay_column(conn)
        rows = conn.execute(
            "SELECT id, confidence, created_at, last_decay_at FROM facts",
        ).fetchall()

        facts_seen = len(rows)
        total_before = 0.0
        total_after = 0.0
        updates: list[tuple[float, float, str]] = []

        for r in rows:
            old = float(r["confidence"])
            created = float(r["created_at"])
            # Decay from the LAST pass, not from created_at every time. exp is
            # multiplicative, so per-pass deltas compose into one continuous
            # decay over real elapsed time; decaying from created_at each pass
            # re-applied exp(-age_total/tau) on the already-decayed value and
            # collapsed the corpus to the floor in O(#runs).
            last_decay = r["last_decay_at"]
            base_ts = float(last_decay) if last_decay is not None else created
            age = now_ts - base_ts
            new = compute_decayed_confidence(
                original=old, age_seconds=age,
                tau_seconds=tau_seconds, floor=floor,
            )
            total_before += old
            total_after += new
            if _changed(old, new):
                updates.append((new, now_ts, r["id"]))

        if not dry_run and updates:
            conn.executemany(
                "UPDATE facts SET confidence = ?, last_decay_at = ? WHERE id = ?",
                updates,
            )

    avg_before = (total_before / facts_seen) if facts_seen else 0.0
    avg_after = (total_after / facts_seen) if facts_seen else 0.0

    return {
        "facts_seen": facts_seen,
        "facts_updated": len(updates),
        "avg_confidence_before": round(avg_before, 6),
        "avg_confidence_after": round(avg_after, 6),
        "tau_seconds": tau_seconds,
        "floor": floor,
        "dry_run": dry_run,
        "elapsed_s": round(time.time() - started_at, 3),
    }


__all__ = [
    "DEFAULT_FLOOR",
    "DEFAULT_TAU_SECONDS",
    "SEC_PER_DAY",
    "compute_decayed_confidence",
    "run_decay_pass",
]
