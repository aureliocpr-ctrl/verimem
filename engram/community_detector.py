"""Cycle 186 (2026-05-23) — Louvain community detection over the fact graph.

Closes gap §5.1 of docs/sota/community-detection-channel-pattern.md
(cycle 185). Pure function that returns dense subgraph clusters
("channels") via Louvain modularity maximisation.

Composes over ``networkx.algorithms.community.louvain_communities``
(networkx >= 3.2 already in pyproject.toml dependencies — NO new
external package).

Defensive: missing DB / empty graph / SQL error → empty result, never
raises. Hard-cap LIMIT 50_000 nodes so the algorithm degrades
gracefully on pathologically large corpora.

Composes-over, not replaces:
  * ``engram.consolidation`` (pairwise cosine clustering, cycle #144)
  * ``engram.facts_cluster_by_topic`` (string equality)
  * ``engram.hippo_pagerank`` (global centrality)

This function adds the **topological** view that the three above miss
— facts grouped by ``lineage_to`` + ``causal_edges`` adjacency rather
than embedding similarity or string-equal topic.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Literal

# networkx is already a hard dependency (pyproject.toml line 46).
import networkx as nx

Algorithm = Literal["louvain"]
EdgesSource = Literal["lineage", "causal", "both"]

#: Hard cap on nodes loaded into the in-memory graph. Louvain is
#: O(N log N) but the SQL+adjacency build is O(N) — picking 50k as a
#: safety net well above realistic corpus sizes (current ~1.7k).
_MAX_NODES: int = 50_000

#: Cap on fact fan-out per episode when projecting episode->episode causal
#: edges onto the fact graph (scan #316). A "popular" episode shared by many
#: facts would otherwise explode into a near-clique; 32 keeps the projection
#: bounded while covering the real corpus (median facts/episode ~1).
_CAUSAL_FANOUT_CAP: int = 32


def _sibling_episodes_db(semantic_db: Path) -> Path:
    """Convention: ``~/.engram/semantic/semantic.db`` ->
    ``~/.engram/episodes/episodes.db``. Lets the existing 2-arg callers of
    _load_graph get the causal-edge fix without threading a new path."""
    return semantic_db.parent.parent / "episodes" / "episodes.db"


def _empty_result(algo: str) -> dict[str, Any]:
    return {
        "algorithm": algo,
        "n_communities": 0,
        "modularity": 0.0,
        "communities": [],
    }


def _load_graph(
    db_path: Path,
    edges_source: EdgesSource,
    *,
    episodes_db: Path | str | None = None,
) -> nx.Graph:
    """Build an undirected networkx graph from semantic.db.

    Nodes = alive (non-superseded) facts. Edges = lineage_to (parent
    pointer) and/or causal_edges (skill-derived correlations),
    depending on ``edges_source``.

    Scan #316: the causal branch was a permanent no-op — it queried
    ``causal_edges`` on semantic.db (the table lives in episodes.db), with
    the wrong column names (src/dst vs src_episode_id/dst_episode_id), and
    even then linked EPISODE ids against a FACT-keyed graph. Now causal_edges
    are read from ``episodes_db`` (default: the sibling episodes.db) and each
    episode->episode edge is projected onto the fact graph via
    ``facts.source_episodes`` (episode -> facts), capped per episode.
    """
    g = nx.Graph()
    conn = sqlite3.connect(str(db_path))
    try:
        # Load alive nodes only (+ source_episodes for the causal projection).
        # Synthetic/legacy DBs (e.g. the second_pass_louvain test fixtures)
        # may lack the source_episodes column: fall back to a 2-column SELECT
        # and an empty causal projection instead of exploding — an unguarded
        # OperationalError here surfaced as "0 communities" upstream.
        try:
            rows = conn.execute(
                """
                SELECT id, lineage_to, source_episodes FROM facts
                WHERE superseded_by IS NULL
                  AND (status IS NULL OR status NOT IN ('orphaned', 'quarantined'))
                LIMIT ?
                """,
                (_MAX_NODES,),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = [
                (fid, lin, None) for fid, lin in conn.execute(
                    """
                    SELECT id, lineage_to FROM facts
                    WHERE superseded_by IS NULL
                      AND (status IS NULL OR status NOT IN ('orphaned', 'quarantined'))
                    LIMIT ?
                    """,
                    (_MAX_NODES,),
                ).fetchall()
            ]
        alive_ids: set[str] = set()
        lineage_edges: list[tuple[str, str]] = []
        ep_to_facts: dict[str, list[str]] = {}
        for fact_id, lineage_to, source_eps in rows:
            fid = str(fact_id)
            alive_ids.add(fid)
            g.add_node(fid)
            if lineage_to:
                lineage_edges.append((fid, str(lineage_to)))
            if edges_source in ("causal", "both") and source_eps:
                # Schema reality check (the orphan draft assumed JSON and was
                # a silent no-op): facts.source_episodes is COMMA-SEPARATED
                # TEXT — semantic.py stores ",".join(...) and loads
                # .split(","). Accept a stray legacy JSON list defensively.
                raw = str(source_eps).strip()
                if raw.startswith("["):
                    try:
                        parsed = json.loads(raw)
                    except ValueError:
                        parsed = []
                    eps = [str(x) for x in parsed] if isinstance(parsed, list) else []
                else:
                    eps = [p.strip() for p in raw.split(",") if p.strip()]
                for ep in eps:
                    ep_to_facts.setdefault(ep, []).append(fid)

        if edges_source in ("lineage", "both"):
            for src, dst in lineage_edges:
                # Only add the edge if both endpoints are alive (skip
                # dangling lineage_to that points to a superseded
                # parent — those facts won't be in alive_ids).
                if src in alive_ids and dst in alive_ids:
                    g.add_edge(src, dst, weight=1.0)

        if edges_source in ("causal", "both"):
            _project_causal_edges(g, ep_to_facts, db_path, episodes_db)
    finally:
        conn.close()
    return g


def _project_causal_edges(
    g: nx.Graph,
    ep_to_facts: dict[str, list[str]],
    semantic_db: Path,
    episodes_db: Path | str | None,
) -> None:
    """Read episode->episode causal_edges and project them onto the
    fact graph via ``ep_to_facts``. Best-effort: a missing episodes.db or
    table degrades to no edges (never raises)."""
    if not ep_to_facts:
        return  # no fact carries source_episodes -> nothing to project
    ep_db = Path(episodes_db) if episodes_db else _sibling_episodes_db(Path(semantic_db))
    if not ep_db.exists():
        return
    try:
        ep_conn = sqlite3.connect(f"file:{ep_db}?mode=ro", uri=True, timeout=5)
    except sqlite3.Error:
        return
    try:
        causal_rows = ep_conn.execute(
            "SELECT src_episode_id, dst_episode_id, COALESCE(weight, 1.0) "
            "FROM causal_edges"
        ).fetchall()
    except sqlite3.OperationalError:
        causal_rows = []  # table absent on an old schema — graceful
    finally:
        ep_conn.close()

    for src_ep, dst_ep, w in causal_rows:
        src_facts = ep_to_facts.get(str(src_ep), [])[:_CAUSAL_FANOUT_CAP]
        dst_facts = ep_to_facts.get(str(dst_ep), [])[:_CAUSAL_FANOUT_CAP]
        for fx in src_facts:
            for fy in dst_facts:
                if fx == fy:
                    continue  # self-loop is meaningless for community detection
                if g.has_edge(fx, fy):
                    old = g[fx][fy].get("weight", 1.0)
                    g[fx][fy]["weight"] = max(float(old), float(w))
                else:
                    g.add_edge(fx, fy, weight=float(w))


def detect_communities(
    *,
    semantic_db: Path | str,
    algorithm: Algorithm = "louvain",
    edges_source: EdgesSource = "both",
    min_community_size: int = 3,
    seed: int = 42,
) -> dict[str, Any]:
    """Detect communities (densely-connected sub-graphs) in the fact graph.

    Args:
        semantic_db: path to ``semantic.db``.
        algorithm: only ``"louvain"`` supported in cycle 186.
        edges_source: which edge family to include in the graph.
        min_community_size: drop communities smaller than this.
        seed: RNG seed for Louvain (determinism).

    Returns:
        {
          "algorithm": "louvain",
          "n_communities": int,                # post min_community_size filter
          "modularity": float,                 # Newman Q on the full partition
          "communities": [
            {"id": "c-001", "size": int, "fact_ids": [str, ...]}
          ],
        }

        Empty dict-shape on missing DB / empty graph / error path
        (never raises).
    """
    p = Path(semantic_db)
    if not p.exists():
        return _empty_result(algorithm)

    try:
        g = _load_graph(p, edges_source)
    except sqlite3.Error:
        return _empty_result(algorithm)

    if g.number_of_nodes() == 0:
        return _empty_result(algorithm)

    if algorithm != "louvain":  # pragma: no cover — future-proofing
        return _empty_result(algorithm)

    try:
        partitions = nx.algorithms.community.louvain_communities(
            g, weight="weight", seed=int(seed),
        )
        modularity = float(
            nx.algorithms.community.modularity(g, partitions, weight="weight")
        )
    except Exception:
        return _empty_result(algorithm)

    communities: list[dict[str, Any]] = []
    # Sort partitions by size desc so caller gets the dominant
    # communities first (better operator UX).
    sorted_partitions = sorted(partitions, key=len, reverse=True)
    for i, members in enumerate(sorted_partitions):
        if len(members) < int(min_community_size):
            continue
        # Sort fact_ids for deterministic output across runs.
        fact_ids = sorted(str(m) for m in members)
        communities.append({
            "id": f"c-{i + 1:03d}",
            "size": len(fact_ids),
            "fact_ids": fact_ids,
        })

    return {
        "algorithm": algorithm,
        "n_communities": len(communities),
        "modularity": modularity,
        "communities": communities,
    }


__all__ = ["detect_communities"]
