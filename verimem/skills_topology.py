"""Skill DAG topology aggregate stats.

FORGIA pezzo #250 — Wave 49. Aggregate metrics on the
parent_skills DAG: degree distribution, roots, leaves, max depth.
Useful to characterise the library's "shape" at a glance.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .skill import Skill


def skills_topology(skills: list[Skill]) -> dict[str, Any]:
    """Compute DAG-level topology stats."""
    ids = {s.id for s in skills}
    in_deg: defaultdict[str, int] = defaultdict(int)
    out_deg: defaultdict[str, int] = defaultdict(int)
    children: defaultdict[str, list[str]] = defaultdict(list)

    for s in skills:
        for p in (s.parent_skills or []):
            if p in ids:
                in_deg[s.id] += 1
                out_deg[p] += 1
                children[p].append(s.id)

    n_edges = sum(in_deg.values())
    roots = sorted([s.id for s in skills if in_deg[s.id] == 0])
    leaves = sorted([s.id for s in skills if out_deg[s.id] == 0])

    # Max depth (longest path root->leaf). BFS from each root.
    max_depth = 0
    for root in roots:
        # BFS depth.
        visited = {root: 0}
        queue = [root]
        while queue:
            cur = queue.pop(0)
            for ch in children.get(cur, ()):
                if ch in visited:
                    continue
                visited[ch] = visited[cur] + 1
                if visited[ch] > max_depth:
                    max_depth = visited[ch]
                queue.append(ch)

    return {
        "n_nodes": len(skills),
        "n_edges": n_edges,
        "roots": roots,
        "leaves": leaves,
        "max_depth": max_depth,
        "out_degree_max": max(out_deg.values(), default=0),
        "in_degree_max": max(in_deg.values(), default=0),
        "n_roots": len(roots),
        "n_leaves": len(leaves),
    }


__all__ = ["skills_topology"]
