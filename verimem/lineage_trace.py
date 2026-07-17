"""Cycle #52 — unified-graph lineage tracer.

Walks BFS over the connected graph of episodes, facts and skills:
- episode ↔ episode  via causal_edges (memory.causal_graph)
- episode ↔ fact     via facts.source_episodes (Python-side reverse index)
- episode ↔ skill    via episode.skills_used
- skill   ↔ skill    via skill_lineage (skills.lineage_graph)

Direction:
- 'forward':  outgoing edges (what this leads to)
- 'backward': incoming edges (what leads to this)
- 'both':     follow both

Safety:
- max_depth caps BFS depth (default 3, hard cap 10)
- max_nodes caps result size (default 200, hard cap 1000)
- `truncated: True` flag set when cap is hit

Performance note (2026-05-14): facts.source_episodes is a CSV string,
so we cannot index it cheaply in SQLite. Instead we load all facts once
(SemanticMemory.all() returns ordered list — O(N) read) and build a
reverse index `episode_id → [fact_id, ...]` in memory. For N<10k facts
this is ~ms on first call. Above 10k, refactor to dedicated
`fact_source_episode (fact_id, episode_id)` table — tracked as a
future cycle. For the current corpus (515 facts, 181 ep, 318 skills)
the warm walk completes in single-digit ms.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from typing import Any

import networkx as nx

_VALID_KINDS = ("episode", "fact", "skill")
_VALID_DIRECTIONS = ("forward", "backward", "both")


def _label_for(node_id: str, kind: str, agent: Any) -> str | None:
    """Return a short human-readable label for the node, or None if
    the node does not exist (lets the walker silently skip dangling
    refs like a causal_edges row pointing to a deleted episode)."""
    try:
        if kind == "episode":
            ep = agent.memory.get(node_id)
            if ep is None:
                return None
            return (getattr(ep, "task_text", "") or "")[:140]
        if kind == "fact":
            f = agent.semantic.get(node_id)
            if f is None:
                return None
            return (getattr(f, "proposition", "") or "")[:140]
        if kind == "skill":
            s = agent.skills.get(node_id)
            if s is None:
                return None
            return getattr(s, "name", "") or node_id
    except Exception:  # noqa: BLE001
        return None
    return None


def _neighbors(
    node_id: str, kind: str, direction: str, agent: Any,
    *, fact_by_episode: dict[str, list[str]],
    causal_g: nx.DiGraph, lineage_g: nx.DiGraph,
    skill_to_episodes: dict[str, list[str]],
) -> Iterable[tuple[str, str, str]]:
    """Yield (neighbor_id, neighbor_kind, relation_label) tuples.

    Relations are short labels callers can group by:
      causal, caused_by, has_fact, from_episode,
      used_skill, used_by_episode, child:<rel>, parent:<rel>
    """
    out: list[tuple[str, str, str]] = []

    if kind == "episode":
        ep = agent.memory.get(node_id)
        if ep is None:
            return out

        if direction in ("forward", "both"):
            # episode → episode via causal_edges (outgoing)
            if causal_g.has_node(node_id):
                for nbr in causal_g.successors(node_id):
                    out.append((nbr, "episode", "causal"))
            # episode → fact via facts.source_episodes (reverse index)
            for fid in fact_by_episode.get(node_id, []):
                out.append((fid, "fact", "has_fact"))
            # episode → skill via skills_used
            for sid in getattr(ep, "skills_used", None) or []:
                out.append((sid, "skill", "used_skill"))

        if direction in ("backward", "both"):
            # episode ← episode via causal_edges (incoming)
            if causal_g.has_node(node_id):
                for nbr in causal_g.predecessors(node_id):
                    out.append((nbr, "episode", "caused_by"))
            # Note: facts pointing TO this episode would re-yield
            # has_fact in the opposite direction. The fact-side
            # branch below handles fact→episode walking explicitly.

    elif kind == "fact":
        f = agent.semantic.get(node_id)
        if f is None:
            return out
        # fact ↔ episode is symmetric in the graph (a fact "comes from"
        # episodes that recorded it). Both forward/backward expose it.
        for eid in getattr(f, "source_episodes", None) or []:
            out.append((eid, "episode", "from_episode"))

    elif kind == "skill":
        s = agent.skills.get(node_id)
        if s is None:
            return out

        if direction in ("forward", "both"):
            # skill → child via skill_lineage
            if lineage_g.has_node(node_id):
                for child in lineage_g.successors(node_id):
                    rel = lineage_g[node_id][child].get(
                        "relation", "child"
                    )
                    out.append((child, "skill", f"child:{rel}"))
            # skill → episodes using it (reverse index)
            for eid in skill_to_episodes.get(node_id, []):
                out.append((eid, "episode", "used_by_episode"))

        if direction in ("backward", "both"):
            if lineage_g.has_node(node_id):
                for parent in lineage_g.predecessors(node_id):
                    rel = lineage_g[parent][node_id].get(
                        "relation", "parent"
                    )
                    out.append((parent, "skill", f"parent:{rel}"))

    return out


def trace(
    start_id: str, kind: str, agent: Any, *,
    direction: str = "both", max_depth: int = 3,
    max_nodes: int = 200,
) -> dict[str, Any]:
    """BFS walker. See module docstring.

    Returns a dict with:
      - ok: bool (False only on invalid input)
      - error: str (when ok=False)
      - start: {id, kind}
      - nodes: list of {id, kind, label, depth}
      - edges: list of {src='kind:id', dst='kind:id', relation}
      - depth_reached: int
      - truncated: bool (True when max_nodes reached)
      - not_found: bool (True when start_id doesn't exist)
    """
    if kind not in _VALID_KINDS:
        return {
            "ok": False,
            "error": (
                f"invalid kind: {kind!r}, must be one of "
                f"{list(_VALID_KINDS)}"
            ),
        }
    if direction not in _VALID_DIRECTIONS:
        return {
            "ok": False,
            "error": (
                f"invalid direction: {direction!r}, must be one of "
                f"{list(_VALID_DIRECTIONS)}"
            ),
        }
    max_depth = max(0, min(int(max_depth), 10))
    max_nodes = max(1, min(int(max_nodes), 1000))

    start_label = _label_for(start_id, kind, agent)
    if start_label is None:
        return {
            "ok": True,
            "start": {"id": start_id, "kind": kind},
            "nodes": [], "edges": [],
            "depth_reached": 0, "truncated": False,
            "not_found": True,
        }

    # Pre-load auxiliary graphs/indexes ONCE per call.
    causal_g = agent.memory.causal_graph()
    lineage_g = agent.skills.lineage_graph()

    # Reverse index: episode_id → [fact_id, ...]
    fact_by_episode: dict[str, list[str]] = {}
    for f in agent.semantic.all():
        for eid in (getattr(f, "source_episodes", None) or []):
            fact_by_episode.setdefault(eid, []).append(f.id)

    # Reverse index: skill_id → [episode_id, ...] (computed lazily —
    # only needed when walker enters a skill node with forward dir)
    skill_to_episodes: dict[str, list[str]] = {}
    for ep in agent.memory.all():
        for sid in (getattr(ep, "skills_used", None) or []):
            skill_to_episodes.setdefault(sid, []).append(ep.id)

    visited: dict[tuple[str, str], dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    edge_seen: set[tuple[str, str, str, str, str]] = set()
    queue: deque[tuple[str, str, int]] = deque()

    visited[(start_id, kind)] = {"label": start_label, "depth": 0}
    queue.append((start_id, kind, 0))
    truncated = False

    while queue:
        node_id, node_kind, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for nbr_id, nbr_kind, relation in _neighbors(
            node_id, node_kind, direction, agent,
            fact_by_episode=fact_by_episode,
            causal_g=causal_g, lineage_g=lineage_g,
            skill_to_episodes=skill_to_episodes,
        ):
            edge_key = (node_kind, node_id, nbr_kind, nbr_id, relation)
            if edge_key not in edge_seen:
                edge_seen.add(edge_key)
                edges.append({
                    "src": f"{node_kind}:{node_id}",
                    "dst": f"{nbr_kind}:{nbr_id}",
                    "relation": relation,
                })
            nbr_key = (nbr_id, nbr_kind)
            if nbr_key in visited:
                continue
            nbr_label = _label_for(nbr_id, nbr_kind, agent)
            if nbr_label is None:
                # Dangling reference (e.g. ep deleted but causal_edge
                # still present). Silently skip — the edge already
                # surfaced in `edges` for transparency.
                continue
            if len(visited) >= max_nodes:
                truncated = True
                break
            visited[nbr_key] = {
                "label": nbr_label, "depth": depth + 1,
            }
            queue.append((nbr_id, nbr_kind, depth + 1))
        if truncated:
            break

    nodes_out = [
        {"id": k[0], "kind": k[1],
         "label": v["label"], "depth": v["depth"]}
        for k, v in visited.items()
    ]
    depth_reached = max(
        (v["depth"] for v in visited.values()), default=0
    )

    return {
        "ok": True,
        "start": {"id": start_id, "kind": kind},
        "nodes": nodes_out,
        "edges": edges,
        "depth_reached": depth_reached,
        "truncated": truncated,
    }
