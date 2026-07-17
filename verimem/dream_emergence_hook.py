"""Cycle 219 (2026-05-23) — dream_emergence_hook composition seed.

Fourth Auto-Dream hook (after cycle 175.1 stuck, 187 community, 211
thompson). Builds a structured seed from the cycle 213 + 217 emergent
skill DRAFT pipeline:

  Louvain community + topic purity + cohesion       (cycle 213)
    ↓
  normalize_topic family key                          (cycle 214/215)
    ↓
  deterministic LLM-free DRAFT (name + keywords)     (cycle 217)
    ↓
  instructions_suffix for propose_dream_tasks         ← here

When this hook fires non-empty, the Auto-Dream cluster algorithm
inside ``propose_dream_tasks`` sees a list of skill names that the
graph itself thinks are READY to crystallise. The dream task it
generates can then refine the DRAFT into a fully-shaped skill — the
LLM call becomes a polish step, NOT a discovery step.

Composes-over
-------------
* ``verimem.skill_emergence_detector.detect_emerging_skills`` (cycle 213)
* ``verimem.skill_drafter.draft_skill_from_community`` (cycle 217)

Defensive
---------
All failure modes (missing DB, no communities, empty corpus, low
cohesion, low purity) return ``{"draft_skill_names": [], "instructions_suffix": ""}``.
The dream cluster algorithm sees a no-op seed and proceeds with the
other three hooks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from verimem.skill_drafter import draft_skill_from_community
from verimem.skill_emergence_detector import detect_emerging_skills

_EMPTY_SEED: dict[str, Any] = {
    "draft_skill_names": [],
    "instructions_suffix": "",
}


def _format_suffix(drafts: list[dict[str, Any]]) -> str:
    if not drafts:
        return ""
    parts: list[str] = []
    for d in drafts:
        name = d.get("skill_name", "")
        evidence = d.get("evidence", {})
        size = evidence.get("size", 0)
        purity = float(evidence.get("topic_purity", 0.0) or 0.0)
        cohesion = float(evidence.get("cohesion", 0.0) or 0.0)
        kws = d.get("trigger_keywords", []) or []
        kw_preview = ", ".join(kws[:5])
        parts.append(
            f"{name} (size={size}, purity={purity:.2f}, "
            f"cohesion={cohesion:.2f}, keywords: {kw_preview})",
        )
    summary = "; ".join(parts)
    return (
        "\n\nEmergent skill hint (cycle 219): the fact graph is "
        f"surfacing {len(drafts)} draft skill candidate(s) ready for "
        f"refinement: {summary}. These were auto-discovered "
        "algorithmically (zero LLM tokens) via cycle 213 community "
        "detection + cycle 217 deterministic drafter. Prioritise dream "
        "tasks that polish these drafts into adopted skills, since the "
        "graph topology + topic purity + embedding cohesion all agree "
        "that the underlying fact cluster is coherent enough to "
        "warrant promotion."
    )


def build_emergence_seed(
    semantic_db: Path | str,
    *,
    max_n: int = 3,
    min_community_size: int = 4,
    min_topic_purity: float = 0.5,
    min_cohesion: float = 0.3,
) -> dict[str, Any]:
    """Build an emergent-skill seed dict for Auto-Dream instructions.

    Args:
        semantic_db: path to ``semantic.db`` (live fact corpus).
        max_n: cap on emergent skills surfaced (3 is plenty for a
            single dream cycle).
        min_community_size: forwarded to ``detect_emerging_skills``.
        min_topic_purity: forwarded.
        min_cohesion: forwarded.

    Returns:
        ``{"draft_skill_names": list[str], "instructions_suffix": str}``.
        Empty seed (no names, no suffix) on any failure or no match.
    """
    p = Path(semantic_db)
    if not p.exists():
        return dict(_EMPTY_SEED)
    try:
        candidates = detect_emerging_skills(
            p,
            min_community_size=int(min_community_size),
            min_topic_purity=float(min_topic_purity),
            min_cohesion=float(min_cohesion),
            max_n=int(max_n),
        )
    except Exception:  # noqa: BLE001
        # Defensive: any unexpected failure → no-op seed.
        return dict(_EMPTY_SEED)
    if not candidates:
        return dict(_EMPTY_SEED)

    drafts: list[dict[str, Any]] = []
    for c in candidates:
        try:
            d = draft_skill_from_community(p, c)
        except Exception:  # noqa: BLE001
            continue
        if d.get("skill_name"):
            drafts.append(d)

    if not drafts:
        return dict(_EMPTY_SEED)

    return {
        "draft_skill_names": [d["skill_name"] for d in drafts],
        "instructions_suffix": _format_suffix(drafts),
    }


__all__ = ["build_emergence_seed"]
