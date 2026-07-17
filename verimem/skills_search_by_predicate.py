"""Find skills with a target predicate in pre/post.

FORGIA pezzo #268 — Wave 67. Useful: 'which skills require X?'
(pre) or 'which establish X?' (post).
"""
from __future__ import annotations

from typing import Any

from .skill import Skill


def skills_with_predicate(
    skills: list[Skill],
    *,
    predicate: str,
    side: str = "any",
    top_k: int = 100,
) -> dict[str, Any]:
    """Filter skills containing `predicate` in pre/post.

    Args:
      - `side`: "pre" | "post" | "any" (default).
    """
    if side not in ("pre", "post", "any"):
        raise ValueError(f"side must be pre/post/any; got {side}")

    matches: list[dict[str, Any]] = []
    for s in skills:
        in_pre = predicate in (s.preconditions or [])
        in_post = predicate in (s.postconditions or [])
        if side == "pre" and not in_pre:
            continue
        if side == "post" and not in_post:
            continue
        if side == "any" and not (in_pre or in_post):
            continue
        matches.append({
            "id": s.id,
            "name": s.name,
            "status": s.status,
            "in_pre": in_pre,
            "in_post": in_post,
        })

    return {
        "predicate": predicate,
        "side": side,
        "n_total": len(matches),
        "skills": matches[:top_k],
    }


__all__ = ["skills_with_predicate"]
