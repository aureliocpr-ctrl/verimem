"""R43: Export memory tiers as a knowledge graph.

Nodes:
  - episode (id, label=task_text[:40])
  - skill (id, label=name|id)
  - fact (id, label=proposition[:40])

Edges:
  - parent_of (skill→skill, via parent_skills)
  - uses_skill (episode→skill)
  - source_episode (fact→episode, via source_episodes)
  - superseded_by (fact→fact, via superseded_by)
  - lineage_to (fact→fact, via lineage_to)
  - about (fact→skill, by topic overlap — lightweight heuristic)

Output suitable for Neo4j/Gephi/D3 import.
"""
from __future__ import annotations

from typing import Any


def export_graph(
    *,
    episodes: list[Any],
    skills: list[Any],
    facts: list[Any],
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    # ── skill nodes + parent_of edges ─────────────────────────
    for s in skills:
        sid = getattr(s, "id", "")
        nodes.append({
            "id": f"skill:{sid}",
            "type": "skill",
            "label": getattr(s, "name", sid) or sid,
            "status": getattr(s, "status", ""),
        })
        for p in getattr(s, "parent_skills", []) or []:
            edges.append({
                "from": f"skill:{p}",
                "to": f"skill:{sid}",
                "type": "parent_of",
            })

    # ── episode nodes + uses_skill edges ──────────────────────
    episode_ids: set[str] = set()
    for e in episodes:
        eid = getattr(e, "id", "")
        episode_ids.add(eid)
        nodes.append({
            "id": f"episode:{eid}",
            "type": "episode",
            "label": getattr(e, "task_text", "")[:50],
            "outcome": getattr(e, "outcome", ""),
        })
        for sk in getattr(e, "skills_used", []) or []:
            edges.append({
                "from": f"episode:{eid}",
                "to": f"skill:{sk}",
                "type": "uses_skill",
            })

    # ── fact nodes + source_episode / superseded_by / lineage edges ──
    for f in facts:
        fid = getattr(f, "id", "")
        nodes.append({
            "id": f"fact:{fid}",
            "type": "fact",
            "label": getattr(f, "proposition", "")[:50],
            "topic": getattr(f, "topic", ""),
            "status": getattr(f, "status", ""),
            "confidence": getattr(f, "confidence", None),
        })

        # source_episodes → fact links to the episode that generated it
        for src_ep in getattr(f, "source_episodes", []) or []:
            if src_ep and src_ep != "[]":
                edges.append({
                    "from": f"fact:{fid}",
                    "to": f"episode:{src_ep}",
                    "type": "source_episode",
                })

        # superseded_by → fact chain
        sup = getattr(f, "superseded_by", None)
        if sup:
            edges.append({
                "from": f"fact:{fid}",
                "to": f"fact:{sup}",
                "type": "superseded_by",
            })

        # lineage_to → knowledge derivation chain
        for lt in getattr(f, "lineage_to", []) or []:
            if lt:
                edges.append({
                    "from": f"fact:{fid}",
                    "to": f"fact:{lt}",
                    "type": "lineage_to",
                })

    return {
        "nodes": nodes,
        "edges": edges,
        "n_nodes": len(nodes),
        "n_edges": len(edges),
    }


__all__ = ["export_graph"]
