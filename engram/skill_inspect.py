"""Per-skill deep inspect orchestrator.

FORGIA pezzo #236 — Wave 35. Composes the per-skill diagnostics
into one call: health + path + failure_audit + analogues. Useful
for debug ("perché questo skill si comporta così?") and curation.
"""
from __future__ import annotations

from typing import Any

from .analogy import find_structural_analogues
from .skill_failure_audit import skill_failure_audit
from .skill_health import skill_health
from .skill_path import skill_path


def skill_inspect(
    *,
    skill_id: str,
    agent: Any,
    analogue_top_k: int = 3,
    analogue_min_structural: float = 0.3,
    analogue_max_semantic: float = 0.7,
) -> dict[str, Any]:
    """Return everything-about-this-skill in one payload."""
    skills_store = getattr(agent, "skills", None)
    memory = getattr(agent, "memory", None)
    if skills_store is None:
        return {"skill_id": skill_id, "found": False}

    target = skills_store.get(skill_id)
    if target is None:
        return {"skill_id": skill_id, "found": False}

    episodes_all: list[Any] = []
    try:
        if memory is not None and hasattr(memory, "all"):
            episodes_all = memory.all(limit=5000)
    except Exception:
        episodes_all = []

    # 1. Health.
    health = skill_health(target, episodes=episodes_all)

    # 2. Path.
    path = skill_path(
        skill_id=skill_id, episodes=episodes_all, top_k=5,
    )

    # 3. Failure audit.
    audit = skill_failure_audit(
        skill_id=skill_id, episodes=episodes_all, top_k=10,
    )

    # 4. Analogues. Use a neutral cosine fn (0.0) — without a real
    # embedding, every pair has semantic=0, so the structural
    # filter dominates. Caller can wire embeddings in via the MCP
    # layer if desired.
    pool = []
    try:
        pool = skills_store.all()
    except Exception:
        pool = []
    analogues = find_structural_analogues(
        target, pool,
        semantic_cosine_fn=lambda a, b: 0.0,
        min_structural=analogue_min_structural,
        max_semantic=analogue_max_semantic,
        top_k=analogue_top_k,
    )

    return {
        "skill_id": skill_id,
        "found": True,
        "basic": {
            "id": target.id,
            "name": target.name,
            "trigger": target.trigger,
            "status": target.status,
            "stage": target.stage,
            "trials": int(target.trials),
            "successes": int(target.successes),
            "fitness_mean": float(target.fitness_mean),
            "preconditions": list(target.preconditions),
            "postconditions": list(target.postconditions),
            "parent_skills": list(target.parent_skills),
        },
        "health": {
            "suggested_action": health["suggested_action"],
            "reasoning": health["reasoning"],
            "fitness": health["fitness"],
            "recency": health["recency"],
        },
        "path": {
            "n_total_appearances": path["n_total_appearances"],
            "predecessors": path["predecessors"],
            "successors": path["successors"],
        },
        "failure_audit": {
            "n_total_uses": audit["n_total_uses"],
            "n_failures": audit["n_failures"],
            "failure_rate": audit["failure_rate"],
            "recent_failures": audit["failures"][:5],
        },
        "analogues": [
            {
                "id": cand.id, "name": cand.name,
                "structural": info["structural"],
                "semantic": info["semantic"],
            }
            for cand, info in analogues
        ],
    }


__all__ = ["skill_inspect"]
