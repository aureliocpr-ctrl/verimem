"""Cycle 210 (2026-05-23) — Thompson sampling for active learning.

Closes gap §5.1 of docs/sota/active-learning-bandit-vs-cron.md
(cycle 209). Pure function that samples skill candidates from their
Beta posterior — the natural counterpart to the deterministic
stuck-list cron (cycle 175 ``select_stuck_candidates``).

Why Thompson sampling for HippoAgent
------------------------------------
Skills already store ``trials`` and ``successes``. The cycle-129
Bayesian smoothed fitness ``(s+1)/(t+2)`` IS the posterior mean of
``Beta(s+1, t-s+1)``. So drawing a sample from that posterior per
skill — then arg-max'ing — exploits the existing data WITHOUT
any extra plumbing or new schema.

This module ships ONLY the primitive. The Auto-Dream wire (a
``dream_thompson_hook`` analogous to cycle 175.1's
``dream_stuck_hook``) is scope of cycle 211.

Defensive
---------
* Missing DB / SQL error → ``[]``, never raises.
* Zero candidate rows → ``[]``.
* `rng_seed=None` → uses ``numpy.random.default_rng()`` (non-
  deterministic). Production should pass a seed derived from
  ``time.time()`` for reproducibility-on-replay.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np

#: Max trials beyond which a skill is considered out of the
#: warm-up phase (cycle 175 max_trials default).
_DEFAULT_MAX_TRIALS: int = 10


def thompson_sample_candidates(
    skill_db: Path | str,
    *,
    max_n: int = 3,
    max_trials: int = _DEFAULT_MAX_TRIALS,
    status: str = "candidate",
    rng_seed: int | None = None,
) -> list[str]:
    """Return ``max_n`` skill ids sampled by Thompson sampling.

    Filter (all conjunctive):
      - ``skills.status = <status>`` (default ``'candidate'``)
      - ``skills.trials < max_trials`` (warm-up phase only)

    Sampling: per row draw ``r ~ Beta(successes + 1, trials -
    successes + 1)``. Sort by ``r`` DESC. Return top ``max_n`` ids.

    Args:
        skill_db: path to ``skills_index.db``.
        max_n: number of ids to return.
        max_trials: cap on ``trials`` (warm-up filter).
        status: skill status to consider.
        rng_seed: deterministic seed; ``None`` = system RNG.

    Returns:
        ``list[str]`` of up to ``max_n`` ids. Empty on missing DB,
        SQL error, or zero matches.
    """
    p = Path(skill_db)
    if not p.exists():
        return []
    rng = np.random.default_rng(rng_seed)
    try:
        conn = sqlite3.connect(str(p))
        try:
            rows = conn.execute(
                "SELECT id, trials, successes FROM skills "
                "WHERE status = ? AND trials < ?",
                (status, int(max_trials)),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []
    if not rows:
        return []

    scored: list[tuple[str, float]] = []
    for fact_id, trials, successes in rows:
        t = max(0, int(trials or 0))
        s = max(0, min(t, int(successes or 0)))
        alpha = s + 1
        beta_param = (t - s) + 1
        sample = float(rng.beta(alpha, beta_param))
        scored.append((str(fact_id), sample))

    scored.sort(key=lambda kv: -kv[1])
    return [fid for fid, _ in scored[: int(max_n)]]


__all__ = ["thompson_sample_candidates"]
