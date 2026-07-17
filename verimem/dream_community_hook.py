"""Cycle 187 (2026-05-23) — dream_community_hook composition seed.

Composable pattern proven by cycle 175.1 (``dream_stuck_hook``):
returns a structured seed for the caller to splice into the
``instructions`` text passed to ``verimem.dream.propose_dream_tasks``.

Goal
----
Surface the top-K Louvain communities (cycle 186) as a soft hint to
the Auto-Dream cluster algorithm. The cluster algorithm in dream.py
is free to ignore — soft retry by design, no signature change to
``propose_dream_tasks``.

Composes-over
-------------
* ``verimem.community_detector.detect_communities`` (cycle 186 Louvain)

Failure modes (all return empty seed, never raise)
--------------------------------------------------
* Missing DB / SQL error
* No communities above min_community_size threshold
* ``detect_communities`` raises (caught defensively)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from verimem.community_detector import detect_communities

_EMPTY_SEED: dict[str, Any] = {
    "top_community_ids": [],
    "instructions_suffix": "",
}


def _format_suffix(communities: list[dict[str, Any]]) -> str:
    """Human-readable suffix for ``instructions``. Cites every
    community id + size for traceability."""
    if not communities:
        return ""
    lines = []
    for c in communities:
        lines.append(f"{c['id']} (size={c['size']})")
    summary = "; ".join(lines)
    return (
        "\n\nCommunity topology hint (cycle 187): "
        f"top dense subgraphs are {summary}. Consider proposing "
        "skills that synthesise the dominant pattern of each "
        "community, since topological cohesion frequently maps to "
        "shared procedural intent."
    )


def build_community_seed(
    semantic_db: Path | str,
    *,
    max_n: int = 3,
    min_community_size: int = 3,
    edges_source: str = "both",
    seed: int = 42,
) -> dict[str, Any]:
    """Return a seed for ``propose_dream_tasks(instructions=...)`` augment.

    Args:
        semantic_db: path to ``semantic.db``.
        max_n: cap on the number of community ids returned (default 3
            = matches stuck_hook + manageable LLM context).
        min_community_size: drop communities smaller than this.
        edges_source: passed through to ``detect_communities``
            ("lineage", "causal", "both").
        seed: deterministic Louvain seed.

    Returns:
        ``{"top_community_ids": list[str], "instructions_suffix": str}``.
        Both empty when no communities meet criteria or DB missing —
        never raises.
    """
    try:
        result = detect_communities(
            semantic_db=semantic_db,
            algorithm="louvain",
            edges_source=edges_source,  # type: ignore[arg-type]
            min_community_size=int(min_community_size),
            seed=int(seed),
        )
    except Exception:
        return dict(_EMPTY_SEED)

    communities = result.get("communities", [])
    if not communities:
        return dict(_EMPTY_SEED)

    # Pick top max_n by size (already sorted desc by detect_communities).
    top = communities[: int(max_n)]
    return {
        "top_community_ids": [str(c["id"]) for c in top],
        "instructions_suffix": _format_suffix(top),
    }


__all__ = ["build_community_seed"]
