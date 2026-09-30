"""Time-decay penalty for cosine similarity scores.

Cycle #63 (2026-05-14). Pure numpy function, no I/O. Used by the embedding
daemon to push stale facts down the ranking after raw cosine scoring.

Motivating case (bench v2 MISS #4):
    A 2026-05-11 status report fact and a 2026-05-14 cycle #51 fact both
    contain the keywords "hippoagent", "episode". Raw cosine prefers the
    status report (more keyword density). Time decay applies a small
    multiplicative penalty per day past a grace period so the recent
    fact wins — without re-encoding the corpus, without changing the
    encoder, and without per-domain heuristics.

Parameters (all configurable per-call so the daemon can route env-var
overrides through; defaults match cycle #63 baseline):
    grace_days = 3.0    # no penalty under this age
    per_day    = 0.05   # 5% penalty per day after grace
    cap        = 0.20   # never penalise more than 20%

Formula:
    age_days = max(0, (now - created_at_epoch) / 86400)
    penalty  = clip((age_days - grace_days) * per_day, 0, cap)
    adj_sim  = sim * (1 - penalty)

Disable at runtime by passing per_day=0 (no-op).
"""
from __future__ import annotations

import numpy as np

SEC_PER_DAY = 86400.0


def apply_time_decay(
    sims: np.ndarray,
    created_ats: np.ndarray,
    *,
    now: float,
    grace_days: float = 3.0,
    per_day: float = 0.05,
    cap: float = 0.20,
) -> np.ndarray:
    """Return sims adjusted by a time-decay penalty.

    Args:
        sims: 1-D array of cosine similarities (any dtype).
        created_ats: 1-D array of epoch timestamps, same shape as sims.
        now: epoch reference time (typically `time.time()`).
        grace_days: ages under this are not penalised.
        per_day: linear penalty rate per day past the grace window.
        cap: hard upper bound on the penalty (so a 1-year-old fact does
             not get crushed to zero).

    Returns:
        np.ndarray of the same shape as sims, with `adj = sim * (1 - penalty)`.
        Future timestamps (negative age) are treated as age=0 (no penalty).
        Empty inputs return an empty array.

    Safety:
        - Does not mutate inputs.
        - Preserves dtype of `sims`.
        - per_day=0 makes the function a no-op regardless of cap/grace.
    """
    sims_arr = np.asarray(sims)
    if sims_arr.size == 0:
        return sims_arr.copy()

    ats = np.asarray(created_ats, dtype=np.float64)
    age_days = np.maximum(0.0, (now - ats) / SEC_PER_DAY)
    penalties = np.clip(
        (age_days - grace_days) * per_day,
        0.0,
        cap,
    )
    factor = (1.0 - penalties).astype(sims_arr.dtype, copy=False)
    return sims_arr * factor


__all__ = ["apply_time_decay", "SEC_PER_DAY"]
