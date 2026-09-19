"""Cycle 211 (2026-05-23) — dream_thompson_hook composition seed.

Closes gap §5 of docs/sota/active-learning-bandit-vs-cron.md
(cycle 209). Composable pattern identical to cycle 175.1
(``dream_stuck_hook``) and cycle 187 (``dream_community_hook``):
returns a structured seed that the Auto-Dream worker splices into
the ``instructions`` text passed to ``propose_dream_tasks``.

Goal
----
Surface the top-K Thompson-sampled warm-up candidate skills (cycle
210) as a soft hint for Auto-Dream. Complements the stuck-list cron
(cycle 175.1) by addressing the 233/326 untrialed skills problem
documented in fact ``d778cce2faa8`` (cycle 174 audit).

Composes-over
-------------
* ``verimem.thompson_sampling.thompson_sample_candidates`` (cycle 210)

Defensive: missing DB / sampler raises → empty seed, never raises.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from verimem.thompson_sampling import thompson_sample_candidates

_EMPTY_SEED: dict[str, Any] = {
    "thompson_skill_ids": [],
    "instructions_suffix": "",
}


def _format_suffix(skill_ids: list[str]) -> str:
    if not skill_ids:
        return ""
    ids_str = ", ".join(skill_ids)
    return (
        "\n\nWarm-up exploration hint (cycle 211 Thompson sampling): "
        f"posterior-sampled candidate skills {ids_str} have high "
        "potential upside given their Beta(s+1, t-s+1) posterior. "
        "Consider proposing dream tasks that exercise these specific "
        "skills to gather evidence."
    )


def build_thompson_seed(
    skill_db: Path | str,
    *,
    max_n: int = 3,
    max_trials: int = 10,
    rng_seed: int | None = None,
) -> dict[str, Any]:
    """Return a seed for ``propose_dream_tasks(instructions=...)`` augment.

    Args:
        skill_db: path to ``skills_index.db``.
        max_n: cap on the number of skill ids returned (default 3
            matches stuck_hook + community_hook conventions).
        max_trials: pass-through to ``thompson_sample_candidates``
            (warm-up filter).
        rng_seed: deterministic seed. Production uses ``None`` =
            stochastic; tests / replays pass a fixed seed.

    Returns:
        ``{"thompson_skill_ids": list[str], "instructions_suffix": str}``.
        Both empty when no candidates meet criteria or DB missing —
        never raises.
    """
    try:
        ids = thompson_sample_candidates(
            skill_db,
            max_n=int(max_n),
            max_trials=int(max_trials),
            rng_seed=rng_seed,
        )
    except Exception:
        return dict(_EMPTY_SEED)
    if not ids:
        return dict(_EMPTY_SEED)
    return {
        "thompson_skill_ids": list(ids),
        "instructions_suffix": _format_suffix(list(ids)),
    }


__all__ = ["build_thompson_seed"]
