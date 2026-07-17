"""Cycle 175 (2026-05-22) — Active Learning Design B: stuck-list cron.

Implements the empirically-motivated active-learning loop the
``docs/cycle174_active_learning_design.md`` proposed and Aurelio
greenlit on 2026-05-22.

Empirical motivation (fact ``d778cce2faa8``, verified on the live
``~/.engram/skills/skills_index.db``):
  - 326 total skills, 71% (233) never trialed
  - 3 candidates stuck at fitness 0.33-0.40
  - candidate→promoted conversion rate: 7/163 = 4.3 %

Design B (this module) is the *stuck-list cron*: a deterministic
``SELECT`` returns the next ids to retry. No bandit, no randomness.
Design A (warm-up bandit) and Design C (task-driven expansion) are
deferred to future cycles per the design doc.

Falsifiable hypothesis H1 (pre-registered in the design doc):
  Targeted retry over candidates in ``trials ∈ [3, 10]`` and
  ``fitness ∈ (0.3, 0.5)`` lifts the candidate→promoted conversion
  from 4.3 % to > 10 % within 20 Auto-Dream cycles.

This module is the *selection* primitive only. The decision to actually
emit a dream task from the selected ids is the caller's job (a thin
hook in ``verimem.auto_dream_trigger.maybe_trigger_dream`` — added in a
follow-up commit if H1 holds in pilot).

Pure-function contract
----------------------
``select_stuck_candidates`` opens the skills_index.db read-only, runs
one SQL query, returns ids ordered oldest-``updated_at`` first (cron
fairness — every cycle the longest-untouched stuck skill gets a turn).
No state, no side effects, never raises (missing DB → []).

Why SQL not ORM
---------------
Bayesian smoothed fitness ``(s+1)/(t+2)`` is cheap in SQL via a
CAST(...) AS REAL division. Doing the math in Python would require
loading every candidate skill — wasteful on a corpus of hundreds.
The SQL prior matches ``Skill.fitness_mean`` *only when* the
``CONFIG.fitness_prior_alpha = CONFIG.fitness_prior_beta = 1`` (the
default). If a user customised the prior, this function's filter
will diverge slightly from ``Skill.fitness_mean``; see the
``BETA_PRIOR_NOTE`` constant below.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

#: Pinned to the default Beta(1, 1) (uniform) prior used by
#: ``verimem.skill.Skill.fitness_mean`` when ``CONFIG.fitness_prior_*``
#: stays at the package defaults. The SQL filter uses this prior to
#: keep the band semantics consistent with the dataclass property.
#: A user who customised the prior should call ``Skill.fitness_mean``
#: per-row instead of using this fast SQL path.
BETA_PRIOR_NOTE = "Beta(1,1) — pinned to CONFIG default"


def select_stuck_candidates(
    skill_db: Path | str,
    *,
    min_trials: int = 3,
    max_trials: int = 10,
    fitness_band: tuple[float, float] = (0.3, 0.5),
    max_n: int = 3,
    status: str = "candidate",
) -> list[str]:
    """Return the ids of stuck-band candidates eligible for retry.

    Filters (all conjunctive):
      - ``skills.status = <status>`` (default ``'candidate'``)
      - ``min_trials ≤ skills.trials ≤ max_trials``
      - ``fitness_band[0] < (successes+1)/(trials+2) < fitness_band[1]``
        (strict inequalities — boundary skills are treated as
        outside the "stuck" zone)

    Ordering: ``updated_at ASC`` (oldest first → cron fairness).

    Returns up to ``max_n`` ids. Empty list on missing DB or
    SQL error (defensive — this is called from the Auto-Dream
    cooldown path and must never crash a hook).
    """
    p = Path(skill_db)
    if not p.exists():
        return []
    lo, hi = float(fitness_band[0]), float(fitness_band[1])
    try:
        conn = sqlite3.connect(str(p))
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id
                FROM skills
                WHERE status = ?
                  AND trials >= ?
                  AND trials <= ?
                  AND (CAST(successes + 1 AS REAL) / (trials + 2)) > ?
                  AND (CAST(successes + 1 AS REAL) / (trials + 2)) < ?
                ORDER BY updated_at ASC
                LIMIT ?
                """,
                (status, int(min_trials), int(max_trials),
                 lo, hi, int(max_n)),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []
    return [str(r["id"]) for r in rows]


__all__ = ["BETA_PRIOR_NOTE", "select_stuck_candidates"]
