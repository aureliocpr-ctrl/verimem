"""Per-skill health diagnostic + suggested-action policy.

FORGIA pezzo #216 — Wave 15. Exposes the curation logic HippoAgent
already runs internally (during sleep cycles) as a queryable tool.
The user can ask "what should I do with skill X?" and get a
structured answer mid-session.

Action policy (precedence-ordered):

  1. trials == 0
       → "test" (no signal yet)
  2. status == candidate AND trials ≥ 5 AND fitness_lower_bound ≥ 0.6
       → "promote" (vetted enough to graduate)
  3. status == promoted AND trials ≥ 10 AND fitness_mean < 0.3
       → "retire" (consistently underperforms)
  4. status == promoted AND trials ≥ 20 AND fitness_mean ≥ 0.85
       → "pin" (top performer, lock in for protection)
  5. fitness_variance > 0.05 AND trials < 10
       → "test" (high uncertainty, gather more data)
  6. otherwise → "ok"

Each branch produces a 1-line reasoning string the host can show.

This is a pure function — no DB writes, no LLM. Compatible with
HOSTED MODE and read-only contexts.
"""
from __future__ import annotations

import time
from typing import Any

from .skill import Skill


def _days_since(ts: float) -> float | None:
    """Convert a Unix-epoch timestamp to days-since-now. Returns
    None for the sentinel `0.0` (never used). Caps very old values
    at 1e6 days as a defensive ceiling."""
    if ts <= 0.0:
        return None
    delta = max(0.0, time.time() - ts)
    return delta / 86400.0


def _suggest_action(
    skill: Skill,
    fitness_mean: float,
    fitness_lower_bound: float,
    fitness_variance: float,
) -> tuple[str, str]:
    """Apply the policy. Returns (action, reasoning)."""
    trials = int(getattr(skill, "trials", 0))
    status = getattr(skill, "status", "candidate")

    if trials == 0:
        return ("test",
                "no trials yet — run the skill on real tasks to gather signal")

    if (status == "candidate" and trials >= 5
            and fitness_lower_bound >= 0.6):
        return ("promote",
                f"candidate with {trials} trials and "
                f"lower-bound {fitness_lower_bound:.2f} ≥ 0.6 — graduate")

    if (status == "promoted" and trials >= 10
            and fitness_mean < 0.3):
        return ("retire",
                f"promoted skill with {trials} trials and "
                f"mean fitness {fitness_mean:.2f} < 0.3 — retire")

    if (status == "promoted" and trials >= 20
            and fitness_mean >= 0.85):
        return ("pin",
                f"top performer ({trials} trials, "
                f"mean {fitness_mean:.2f}) — pin for protection")

    if fitness_variance > 0.05 and trials < 10:
        return ("test",
                f"high uncertainty (var={fitness_variance:.3f}, "
                f"only {trials} trials) — needs more testing")

    return ("ok",
            f"skill performing within expected range "
            f"({trials} trials, mean {fitness_mean:.2f})")


def skill_health(
    skill: Skill,
    *,
    episodes: list[Any] | None = None,
    days_window: float = 7.0,
) -> dict[str, Any]:
    """Compute the health diagnostic for a single skill.

    Args:
      - `skill`: the Skill instance.
      - `episodes`: optional iterable of episode-likes; used to
        compute uses-in-window. If empty/None, that field is None.
      - `days_window`: window in days for "recent uses" count
        (default 7).

    Returns: dict with `id, name, status, fitness, trials,
    successes, recency, suggested_action, reasoning`.
    """
    fm = float(getattr(skill, "fitness_mean", 0.0))
    fl = float(getattr(skill, "fitness_lower_bound", 0.0))
    fv = float(getattr(skill, "fitness_variance", 0.0))

    last_used = float(getattr(skill, "last_used_at", 0.0))
    days_since = _days_since(last_used)
    uses_in_window = 0
    if episodes:
        cutoff = time.time() - days_window * 86400.0
        for ep in episodes:
            ep_used = getattr(ep, "skills_used", None) or []
            ep_ts = float(getattr(ep, "created_at", 0.0))
            if ep_ts >= cutoff and skill.id in ep_used:
                uses_in_window += 1

    action, reasoning = _suggest_action(skill, fm, fl, fv)

    return {
        "id": skill.id,
        "name": getattr(skill, "name", ""),
        "status": getattr(skill, "status", "candidate"),
        "fitness": {
            "mean": fm,
            "lower_bound": fl,
            "variance": fv,
        },
        "trials": int(getattr(skill, "trials", 0)),
        "successes": int(getattr(skill, "successes", 0)),
        "recency": {
            "days_since_last_use": days_since,
            "uses_in_window": uses_in_window,
            "window_days": days_window,
        },
        "suggested_action": action,
        "reasoning": reasoning,
    }


__all__ = ["skill_health"]
