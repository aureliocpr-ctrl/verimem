"""Bidirectional skill lineage.

FORGIA pezzo #249 — Wave 48. Extends `hippo_skill_lineage` (ancestors
only) with descendants direction. Useful to see "this skill spawned
N derived versions" or "promoting propagates DOWN to children".
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .skill import Skill


def skill_lineage_full(
    *,
    skill_id: str,
    all_skills: list[Skill],
    max_depth: int = 10,
) -> dict[str, Any]:
    """Walk ancestors AND descendants. BFS with depth tracking and
    cycle protection."""
    by_id: dict[str, Skill] = {s.id: s for s in all_skills}
    target = by_id.get(skill_id)
    if target is None:
        return {
            "skill_id": skill_id, "found": False,
            "ancestors": [], "descendants": [],
        }

    # Reverse index: child -> parents who claim it.
    children: defaultdict[str, set[str]] = defaultdict(set)
    for s in all_skills:
        for p in (s.parent_skills or []):
            children[p].add(s.id)

    # Ancestors BFS (via parent_skills).
    ancestors: list[dict[str, Any]] = []
    seen_anc: set[str] = {skill_id}
    queue: list[tuple[str, int]] = [(skill_id, 0)]
    while queue:
        cur, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        cur_sk = by_id.get(cur)
        if cur_sk is None:
            continue
        for parent_id in (cur_sk.parent_skills or []):
            if parent_id in seen_anc:
                continue
            seen_anc.add(parent_id)
            psk = by_id.get(parent_id)
            ancestors.append({
                "id": parent_id,
                "name": psk.name if psk else "",
                "depth": depth + 1,
            })
            queue.append((parent_id, depth + 1))

    # Descendants BFS (via children index).
    descendants: list[dict[str, Any]] = []
    seen_desc: set[str] = {skill_id}
    queue = [(skill_id, 0)]
    while queue:
        cur, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        for ch_id in children.get(cur, ()):
            if ch_id in seen_desc:
                continue
            seen_desc.add(ch_id)
            csk = by_id.get(ch_id)
            descendants.append({
                "id": ch_id,
                "name": csk.name if csk else "",
                "depth": depth + 1,
            })
            queue.append((ch_id, depth + 1))

    return {
        "skill_id": skill_id,
        "found": True,
        "ancestors": ancestors,
        "descendants": descendants,
    }


__all__ = ["skill_lineage_full"]
