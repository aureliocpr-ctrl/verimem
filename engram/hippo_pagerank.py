"""HippoRAG-style dual-cue retrieval via Personalized PageRank.

Inspired by Gutiérrez et al. ICML 2025 (HippoRAG 2, arXiv:2502.14802),
adapted to HippoAgent's setting where the dual cue is:

  - skill fitness (Beta-Binomial posterior lower_bound — pezzo #4)
  - episode relevance (cosine + salience — pezzi #5/#6)

The legacy retrieval has skills picked one way (cosine + Thompson
sampling on Beta posterior) and episodes another (cosine + salience
+ recency). They live in two parallel pipelines that never inform each
other. PPR fuses them: a skill that fired on episodes which are
themselves cosine-close to the current query gets amplified beyond what
its raw fitness would suggest; an episode that uses a high-fitness
skill gets amplified beyond its raw cosine.

Math:

  - Bipartite graph G:
      skill_nodes  = {`sk:` + s.id  for s in skills}
      episode_nodes = {`ep:` + ep.id for ep in episodes}
      edges        = {(ep, sk) : sk in ep.skills_used}

  - Personalization vector p (the PPR seed):
      p[sk:s]  = fitness_lower_bound(s)
      p[ep:e]  = max(0, cosine(query, e.summary)) + α · salience(e)
      then L1-normalised to sum=1.

  - `nx.pagerank(G, alpha=damping, personalization=p)` converges to
    the stationary distribution. The graph topology then propagates
    seed mass: a skill connected to many high-personalization episodes
    accumulates mass via its neighbours.

Top-k nodes are returned as `(id, kind, score)` tuples — the caller
filters skills vs episodes as needed, or feeds both back into the wake
loop.

What this is NOT:
  - It's not a replacement for `consider_skills` / `consider_episodes`
    — those still drive the wake loop's selection. PPR is the
    *retrieval* layer that produces the candidate set those primitives
    rank. Two layers, complementary.
  - It's not the full HippoRAG OpenIE+phrase-graph pipeline. We don't
    do entity extraction with an LLM; the bipartite skill↔episode
    structure is already there for free in the HippoAgent data model.
"""
from __future__ import annotations

import networkx as nx
import numpy as np

from . import embedding
from .memory import EpisodicMemory
from .skill import SkillLibrary


def _normalize(v: np.ndarray) -> np.ndarray:
    """Unit-norm a vector. Pure-numpy."""
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def retrieve_pagerank(
    query: str,
    skills: SkillLibrary,
    memory: EpisodicMemory,
    *,
    top_k: int = 5,
    salience_alpha: float = 0.5,
    skill_fitness_floor: float = 0.0,
    pagerank_damping: float = 0.85,
) -> list[tuple[str, str, float]]:
    """Personalized-PageRank dual-cue retrieval over (skills, episodes).

    Parameters:
      - `top_k`: number of (id, kind, score) tuples to return.
      - `salience_alpha`: weight of `salience_score` inside the
        episode personalization. Default 0.5 — comparable to the
        weight ConsiderationSet uses for theta.
      - `skill_fitness_floor`: skills with `fitness_lower_bound`
        below this are excluded from the seed (their seed mass is
        zero, but they remain in the graph to receive flow if
        connected to relevant episodes).
      - `pagerank_damping`: the standard `α` in PPR. 0.85 is the
        canonical Brin-Page value.

    Returns: `[(id, kind, score), ...]` ordered by descending score.
    Empty input → empty list. Degenerate graphs (no edges, all-zero
    personalization) → empty list.
    """
    all_skills = skills.all()
    all_episodes = memory.all()
    if not all_skills and not all_episodes:
        return []

    # Build the bipartite graph. Node names carry the kind prefix so a
    # skill_id and episode_id with the same string don't collide.
    sk_prefix = "sk:"
    ep_prefix = "ep:"

    g = nx.Graph()
    skill_by_id = {s.id: s for s in all_skills}

    for s in all_skills:
        g.add_node(f"{sk_prefix}{s.id}")
    for ep in all_episodes:
        g.add_node(f"{ep_prefix}{ep.id}")
        for skill_id in ep.skills_used:
            if skill_id in skill_by_id:
                g.add_edge(
                    f"{ep_prefix}{ep.id}",
                    f"{sk_prefix}{skill_id}",
                )

    # Personalization vector — the dual cue.
    q_emb = _normalize(embedding.encode(query))
    personalization: dict[str, float] = {}

    for s in all_skills:
        lb = max(0.0, s.fitness_lower_bound - skill_fitness_floor)
        personalization[f"{sk_prefix}{s.id}"] = lb

    for ep in all_episodes:
        ep_emb = _normalize(embedding.encode(ep.summary()))
        cos = max(0.0, float(np.dot(q_emb, ep_emb)))
        salience = float(ep.salience_score)
        personalization[f"{ep_prefix}{ep.id}"] = (
            cos + salience_alpha * salience
        )

    total_p = sum(personalization.values())
    if total_p == 0.0:
        # No relevant seeds at all — PPR has nothing to propagate.
        return []

    # Normalise so PPR sees a proper probability vector.
    personalization = {k: v / total_p for k, v in personalization.items()}

    # Run PPR. networkx handles disconnected components by giving each
    # the personalization mass that lands on it; isolated nodes keep
    # their seed without amplification.
    try:
        pr = nx.pagerank(
            g, alpha=pagerank_damping,
            personalization=personalization,
            tol=1e-7,
        )
    except nx.PowerIterationFailedConvergence:
        # Extremely rare in practice (would need a tiny disconnected
        # graph). Fall back to the personalization itself — that's
        # equivalent to "no propagation, just seeds".
        pr = personalization

    items: list[tuple[str, str, float]] = []
    for node, score in pr.items():
        if node.startswith(sk_prefix):
            items.append((node[len(sk_prefix):], "skill", float(score)))
        elif node.startswith(ep_prefix):
            items.append((node[len(ep_prefix):], "episode", float(score)))

    items.sort(key=lambda t: -t[2])
    return items[:top_k]


__all__ = ["retrieve_pagerank"]
