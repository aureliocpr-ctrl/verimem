"""STRIPS predicate-graph DAG validation.

FORGIA pezzo #229 — Wave 28. After auto-deriving pre/post (#213,
#215) on hundreds of skills, the planner is much faster on a DAG.
This tool detects cycles + isolated nodes so the user can fix
inconsistencies.

Edge: skill_a → skill_b iff
  set(skill_a.postconditions) ∩ set(skill_b.preconditions) ≠ ∅
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .skill import Skill


def _build_edges(
    skills: list[Skill],
) -> dict[str, list[str]]:
    """Return adjacency dict `skill_id -> [successor_ids]`."""
    edges: defaultdict[str, set[str]] = defaultdict(set)
    for a in skills:
        a_post = set(a.postconditions or [])
        if not a_post:
            continue
        for b in skills:
            b_pre = set(b.preconditions or [])
            if not b_pre:
                continue
            if a_post & b_pre:
                edges[a.id].add(b.id)
    return {sid: sorted(succs) for sid, succs in edges.items()}


def _find_cycles(adj: dict[str, list[str]]) -> list[list[str]]:
    """DFS-based cycle detection. Returns a list of cycle paths."""
    cycles: list[list[str]] = []
    GRAY, BLACK = 1, 2
    color: dict[str, int] = {}

    def dfs(start: str, path: list[str]) -> None:
        color[start] = GRAY
        for succ in adj.get(start, []):
            if color.get(succ) is GRAY:
                # Found cycle: succ is on current path.
                idx = path.index(succ) if succ in path else 0
                cycles.append(path[idx:] + [succ])
            elif color.get(succ) is None:
                dfs(succ, path + [succ])
        color[start] = BLACK

    for node in adj:
        if color.get(node) is None:
            dfs(node, [node])

    # Self-loop detection (adj[x] contains x).
    for node, succs in adj.items():
        if node in succs:
            cycles.append([node, node])

    return cycles


def predicate_graph_check(
    skills: list[Skill],
) -> dict[str, Any]:
    """Build the predicate graph and report cycles + isolated.

    Returns: `{has_cycles, cycles, n_nodes, n_edges,
    isolated_skill_ids}`.
    """
    adj = _build_edges(skills)
    n_edges = sum(len(v) for v in adj.values())

    # Determine which skill ids participate in NON-SELF edges.
    # Self-loops alone do NOT make a skill "in the graph" — a
    # skill that only references itself (because pre ∩ post is
    # non-empty internally) is functionally isolated from others.
    in_graph: set[str] = set()
    for source, targets in adj.items():
        for target in targets:
            if source != target:
                in_graph.add(source)
                in_graph.add(target)

    isolated = [s.id for s in skills if s.id not in in_graph]

    # Cycle detection.
    cycles = _find_cycles(adj)

    # Dedupe cycles (different DFS paths can hit the same loop).
    seen: set[tuple[str, ...]] = set()
    unique_cycles: list[list[str]] = []
    for c in cycles:
        # Canonicalise: rotate to start at lex-smallest node.
        if len(c) > 1 and c[0] == c[-1]:
            base = c[:-1]
        else:
            base = c
        if not base:
            continue
        smallest = min(range(len(base)), key=lambda i: base[i])
        canon = tuple(base[smallest:] + base[:smallest])
        if canon not in seen:
            seen.add(canon)
            unique_cycles.append(list(canon))

    return {
        "has_cycles": bool(unique_cycles),
        "cycles": unique_cycles,
        "n_nodes": len(skills),
        "n_edges": n_edges,
        "isolated_skill_ids": sorted(isolated),
    }


__all__ = ["predicate_graph_check"]
