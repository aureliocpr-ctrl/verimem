"""R22: Cross-agent consensus on facts.

Cluster facts by token-overlap of their propositions; keep clusters
where the facts come from >= min_agents DISTINCT agent_ids (using
the R4 namespace convention `agent:<id>/<rest>`).

These clusters represent CONSENSUS: independent agents arrived at
the same proposition. Strong evidence for the agent team.
"""
from __future__ import annotations

import re
from typing import Any

from .agent_scope import agent_id_from_topic

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_consensus_facts(
    facts: list[Any],
    *,
    min_agents: int = 2,
    sim_threshold: float = 0.6,
    top_k: int = 50,
) -> dict[str, Any]:
    """Identify facts mirrored across multiple distinct agents."""
    if not facts:
        return {"consensus": [], "n_facts_scanned": 0}

    # Greedy clustering on Jaccard
    clusters: list[list[Any]] = []
    for f in facts:
        f_tokens = _tokens(getattr(f, "proposition", ""))
        if not f_tokens:
            continue
        placed = False
        for cl in clusters:
            sample = cl[0]
            s_tokens = _tokens(getattr(sample, "proposition", ""))
            if _jaccard(f_tokens, s_tokens) >= sim_threshold:
                cl.append(f)
                placed = True
                break
        if not placed:
            clusters.append([f])

    consensus: list[dict[str, Any]] = []
    for cl in clusters:
        agent_ids = set()
        for f in cl:
            owner = agent_id_from_topic(getattr(f, "topic", ""))
            if owner:
                agent_ids.add(owner)
        if len(agent_ids) >= min_agents:
            consensus.append({
                "representative": getattr(cl[0], "proposition", "")[:120],
                "n_agents": len(agent_ids),
                "agent_ids": sorted(agent_ids),
                "fact_ids": [getattr(f, "id", "") for f in cl],
                "n_facts": len(cl),
            })

    consensus.sort(key=lambda c: (-c["n_agents"], -c["n_facts"]))
    return {
        "consensus": consensus[:top_k],
        "n_facts_scanned": len(facts),
    }


__all__ = ["find_consensus_facts"]
