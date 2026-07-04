"""R39: Skill lineage metrics.

Compute depth-related stats over the parent_skills DAG:
  - max_depth: longest path from any root to any leaf
  - n_roots: skills with no parents (in-degree 0)
  - n_leaves: skills with no children (out-degree 0)
  - max_fanout: max number of children any skill has
  - avg_fanout: average over non-leaf nodes
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def compute_lineage_metrics(skills: list[Any]) -> dict[str, Any]:
    """DAG metrics over parent_skills relationships."""
    if not skills:
        return {
            "max_depth": 0,
            "n_roots": 0,
            "n_leaves": 0,
            "max_fanout": 0,
            "avg_fanout": 0.0,
            "n_total": 0,
        }

    ids = {getattr(s, "id", "") for s in skills}
    children_of: dict[str, list[str]] = defaultdict(list)
    parents_of: dict[str, list[str]] = defaultdict(list)
    for s in skills:
        sid = getattr(s, "id", "")
        for p in getattr(s, "parent_skills", []) or []:
            if p in ids:
                children_of[p].append(sid)
                parents_of[sid].append(p)

    roots = [sid for sid in ids if sid not in parents_of]
    leaves = [sid for sid in ids if sid not in children_of]

    # Depth via DFS from roots
    depth: dict[str, int] = {r: 0 for r in roots}
    max_depth = 0

    def dfs(node: str, d: int, visited: set[str]) -> None:
        nonlocal max_depth
        if node in visited:
            return
        visited.add(node)
        depth[node] = max(depth.get(node, 0), d)
        max_depth = max(max_depth, d)
        for c in children_of.get(node, []):
            dfs(c, d + 1, visited)

    for r in roots:
        dfs(r, 0, set())

    fanouts = [len(children_of[node]) for node in ids if children_of.get(node)]
    max_fanout = max(fanouts) if fanouts else 0
    avg_fanout = (sum(fanouts) / len(fanouts)) if fanouts else 0.0

    return {
        "max_depth": max_depth,
        "n_roots": len(roots),
        "n_leaves": len(leaves),
        "max_fanout": max_fanout,
        "avg_fanout": round(avg_fanout, 2),
        "n_total": len(skills),
    }


__all__ = ["compute_lineage_metrics"]
