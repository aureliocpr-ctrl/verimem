"""Cycle 175.1 (2026-05-22) — dream_stuck_hook: composition seed.

Connects the active-learning stuck-list cron (cycle 175,
``engram.active_learning.select_stuck_candidates``) to the Auto-Dream
trigger pipeline. The hook is intentionally tiny: a pure composition
that returns a structured seed for the caller to splice into the
``instructions`` text passed to ``engram.dream.propose_dream_tasks``.

Soft retry contract (cycle 175.1)
---------------------------------
  - We DO NOT touch ``propose_dream_tasks`` signature.
  - We DO NOT force cluster inclusion of stuck skills.
  - We only augment the human-readable ``instructions`` text with a
    traceable suffix mentioning each stuck skill id.
  - The cluster algorithm is free to ignore the hint.

The trade-off is intentional: ``instructions`` is logged into the
dream artifact + audit trail (cycle 35 contract), so even an ignored
hint shows up as evidence in the pipeline's observability surface.

Hard retry (cycle 175.3) is *gated on falsification of H1*: if 20
Auto-Dream cycles with soft retry alone fail to lift the
candidate→promoted conversion above 10%, cycle 175.3 will thread a
dedicated ``priority_skill_ids`` parameter through
``propose_dream_tasks`` for deterministic inclusion. See
``docs/cycle174_active_learning_design.md`` § H1.

Defensive contract
------------------
The module catches any exception from ``select_stuck_candidates`` and
returns the empty seed instead of propagating, so the Auto-Dream
worker hook never crashes a SessionStart-time callable. The empty seed
is safe to splice unchanged into ``instructions`` (zero-length string).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from engram.active_learning import select_stuck_candidates

#: Returned when there are no stuck candidates or the DB is missing.
#: Both keys MUST be present so callers can splice unconditionally.
_EMPTY_SEED: dict[str, Any] = {"stuck_skill_ids": [], "instructions_suffix": ""}


def _format_suffix(stuck_ids: list[str]) -> str:
    """Human-readable suffix for ``instructions``.

    Cites every id verbatim for traceability in the dream artifact +
    audit log. Format is deliberately fact-heavy (band thresholds,
    cycle number) so a reader of the artifact can falsify the choice
    of these specific ids without re-running active_learning.
    """
    if not stuck_ids:
        return ""
    ids_str = ", ".join(stuck_ids)
    return (
        "\n\nActive learning retry (cycle 175): the following "
        f"candidate skills {ids_str} are stuck in fitness band "
        "(0.3, 0.5) after 3-10 trials. Prioritize generating dream "
        "tasks that exercise these specific skills to gather "
        "additional evidence."
    )


def build_stuck_retry_seed(
    skill_db: Path | str,
    *,
    max_n: int = 3,
) -> dict[str, Any]:
    """Build a seed for the Auto-Dream worker to splice into instructions.

    Args:
        skill_db: path to ``skills_index.db``.
        max_n: cap on number of stuck ids returned (default 3 — matches
            the ``engram.active_learning.select_stuck_candidates``
            default; keep both in lockstep so the soft retry size is
            consistent across the pipeline).

    Returns:
        Dict with shape ``{"stuck_skill_ids": list[str],
        "instructions_suffix": str}``. Both fields are empty when no
        stuck candidates exist or the DB is missing — never raises.
    """
    try:
        stuck_ids = select_stuck_candidates(skill_db, max_n=max_n)
    except Exception:
        return dict(_EMPTY_SEED)
    if not stuck_ids:
        return dict(_EMPTY_SEED)
    return {
        "stuck_skill_ids": list(stuck_ids),
        "instructions_suffix": _format_suffix(list(stuck_ids)),
    }


__all__ = ["build_stuck_retry_seed"]
