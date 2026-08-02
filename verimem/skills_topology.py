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

    # Max depth (longest path root->leaf).
    #
    # ERA UNA BFS, e la BFS trova il cammino PIU' CORTO. Con `if ch in
    # visited: continue` ogni nodo veniva fissato alla prima volta che lo si
    # raggiungeva, quindi su un grafo dove due strade portano allo stesso
    # nodo — A->B->C->D e A->D — la profondita' usciva 1 invece di 3. Il
    # commento diceva «longest path» dal principio.
    #
    # Ora e' una DFS con memoizzazione: `profondita(n)` = 1 + il massimo dei
    # figli. I nodi CHIUSI si riusano (il DAG si visita una volta sola), e
    # quelli APERTI segnalano un ciclo — dove «cammino piu' lungo» non e' una
    # domanda con risposta finita, e il ramo si tronca invece di girare per
    # sempre. Il grafo delle skill dovrebbe essere aciclico, ma dovrebbe non
    # e' una garanzia, e la vecchia BFS dai cicli era protetta.
    memo: dict[str, int] = {}
    aperti: set[str] = set()

    def _profondita(nodo: str) -> int:
        if nodo in memo:
            return memo[nodo]
        if nodo in aperti:           # ciclo: non si conta oltre
            return 0
        aperti.add(nodo)
        giu = 0
        for ch in children.get(nodo, ()):
            giu = max(giu, 1 + _profondita(ch))
        aperti.discard(nodo)
        memo[nodo] = giu
        return giu

    max_depth = max((_profondita(r) for r in roots), default=0)

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
