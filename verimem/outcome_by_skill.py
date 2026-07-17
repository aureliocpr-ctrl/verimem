"""Per-skill outcome distribution across episodes.

FORGIA pezzo #221 — Wave 20. Cross-checks the Beta-posterior
fitness with raw empirical counts: "out of N episodes that used
skill X, how many succeeded vs failed?".
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from .skill import Skill


def outcomes_by_skill(
    skills: list[Skill],
    episodes: list[Any],
    *,
    top_k: int = 50,
) -> list[dict[str, Any]]:
    """Per-skill outcome counts.

    Args:
      - `skills`: skill pool to consider.
      - `episodes`: iterable of episode-likes with `outcome` and
        `skills_used`.
      - `top_k`: cap on result list (sorted by n_episodes DESC).

    Returns: list of `{skill_id, name, n_episodes, n_success,
    n_failure, success_rate}`. `success_rate` is None when
    `n_episodes == 0`.
    """
    by_skill_success: Counter[str] = Counter()
    by_skill_failure: Counter[str] = Counter()
    by_skill_total: Counter[str] = Counter()

    for ep in episodes:
        outcome = getattr(ep, "outcome", "")
        used = set(getattr(ep, "skills_used", None) or [])
        for sid in used:
            by_skill_total[sid] += 1
            if outcome == "success":
                by_skill_success[sid] += 1
            elif outcome == "failure":
                by_skill_failure[sid] += 1

    out: list[dict[str, Any]] = []
    for s in skills:
        n = by_skill_total.get(s.id, 0)
        ns = by_skill_success.get(s.id, 0)
        nf = by_skill_failure.get(s.id, 0)
        rate: float | None
        if n == 0:
            rate = None
        else:
            rate = ns / n
        out.append({
            "skill_id": s.id,
            "name": s.name,
            "n_episodes": n,
            "n_success": ns,
            "n_failure": nf,
            "success_rate": rate,
        })

    out.sort(key=lambda r: -r["n_episodes"])
    return out[:top_k]


__all__ = ["outcomes_by_skill"]
