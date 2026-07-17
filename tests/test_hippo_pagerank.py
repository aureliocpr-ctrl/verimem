"""Tests for FORGIA pezzo #8: PageRank dual-cue retrieval.

HippoRAG 2 (Gutiérrez et al. ICML 2025) shows that the right retrieval
for an agent with persistent memory isn't `cosine top-k on docs` —
it's Personalized PageRank on a graph where the seeds combine TWO
sources of relevance:

  - "what historically works" (here: skill fitness, our pezzo #4 lower_bound)
  - "what's semantically close to the query" (here: episode cosine + salience)

The PPR converges to a ranking that fuses both. Skill nodes that fired
on past episodes which are *also* cosine-close to the current query
get amplified; isolated skills with high fitness but no recent episode
context fade.

Math:
  - Bipartite graph: skill_node ↔ episode_node, edge weight = 1.0
    (presence in `episode.skills_used`).
  - Personalization vector:
      skill_i: fitness_lower_bound(skill_i)
      episode_j: cosine(query, episode_j) + α · salience_score(episode_j)
    Normalised to sum=1.
  - `networkx.pagerank(G, personalization=p)` is one BLAS call.
  - Top-k nodes returned, the caller filters skill vs episode as needed.

Three measurable invariants we test (declared BEFORE implementing):

  1. A skill connected to many cosine-relevant episodes ranks ABOVE
     a skill with the same fitness but no relevant episodes (graph
     amplification works).

  2. An episode that uses a high-fitness skill ranks above a same-cosine
     episode that uses a low-fitness skill (cross-amplification).

  3. The retrieval is deterministic given the same inputs (PPR converges
     to a unique stationary distribution under standard assumptions).
"""
from __future__ import annotations

import time

import pytest

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.skill import Skill, SkillLibrary


def _ep(
    *, id_: str, task_text: str, skills_used: list[str],
    outcome: str = "success", age_days: float = 1.0,
) -> Episode:
    return Episode(
        id=id_, task_id="t", task_text=task_text,
        outcome=outcome, final_answer="ok",
        skills_used=skills_used,
        created_at=time.time() - age_days * 86400,
        traces=[Trace(
            step=1, thought="x", action="x", action_input="{}",
            observation="x",
        )],
    )


def _skill(*, id_: str, trigger: str, trials: int, successes: int) -> Skill:
    return Skill(
        id=id_, name=id_, trigger=trigger, body="x",
        status="promoted", trials=trials, successes=successes,
    )


# ---------- Test 1: graph amplification favours connected high-fitness skill --


def test_skill_with_relevant_episode_neighbours_outranks_isolated_one(
    tmp_path,
):
    """sk_busy: same fitness as sk_isolated, but connected to 3
    cosine-relevant episodes. PPR amplifies sk_busy because the
    episode-seed mass flows into it. Cosine-only retrieval would
    show them tied."""
    skills = SkillLibrary(
        dir_path=tmp_path / "skills_dir", db_path=tmp_path / "sk.db",
    )
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")

    sk_busy = _skill(
        id_="sk_busy", trigger="fix calc.py arithmetic",
        trials=20, successes=18,
    )
    sk_isolated = _skill(
        id_="sk_isolated", trigger="fix calc.py arithmetic",
        trials=20, successes=18,
    )
    skills.store(sk_busy)
    skills.store(sk_isolated)

    # 3 relevant episodes that USE sk_busy — none use sk_isolated
    for i in range(3):
        mem.store(_ep(
            id_=f"e_busy_{i}",
            task_text="fix calc.py arithmetic bug",
            skills_used=["sk_busy"],
        ))

    from verimem.hippo_pagerank import retrieve_pagerank

    ranked = retrieve_pagerank(
        query="fix calc.py arithmetic bug",
        skills=skills, memory=mem, top_k=4,
    )
    skill_ranks = {
        node_id: i for i, (node_id, _kind, _score) in enumerate(ranked)
        if _kind == "skill"
    }
    assert skill_ranks.get("sk_busy", 99) < skill_ranks.get("sk_isolated", 99), (
        f"PPR didn't amplify sk_busy (connected to 3 relevant episodes) "
        f"over sk_isolated (no episodes). Ranking: {ranked}"
    )


# ---------- Test 2: high-fitness skill amplifies episode ranking --------


def test_episode_using_high_fitness_skill_ranks_above_same_cosine_low_fitness(
    tmp_path,
):
    """Two episodes with similar cosine to the query, one uses a
    high-fitness skill, the other a low-fitness one. PPR should
    rank the high-fitness-using episode higher."""
    skills = SkillLibrary(
        dir_path=tmp_path / "skills_dir", db_path=tmp_path / "sk.db",
    )
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")

    skills.store(_skill(
        id_="sk_proven", trigger="fix calc.py", trials=20, successes=18,
    ))
    skills.store(_skill(
        id_="sk_weak", trigger="fix calc.py", trials=20, successes=4,
    ))

    mem.store(_ep(
        id_="e_proven", task_text="fix calc.py arithmetic",
        skills_used=["sk_proven"],
    ))
    mem.store(_ep(
        id_="e_weak", task_text="fix calc.py arithmetic",
        skills_used=["sk_weak"],
    ))

    from verimem.hippo_pagerank import retrieve_pagerank

    ranked = retrieve_pagerank(
        query="fix calc.py arithmetic", skills=skills, memory=mem, top_k=4,
    )
    ep_order = [
        node_id for (node_id, kind, _score) in ranked if kind == "episode"
    ]
    assert ep_order.index("e_proven") < ep_order.index("e_weak"), (
        f"PPR didn't propagate skill fitness into episode ranking. "
        f"Order: {ep_order}"
    )


# ---------- Test 3: determinism ------------------------------------------


def test_pagerank_retrieval_is_deterministic(tmp_path):
    """Same inputs → same ranked output. PPR has a unique stationary
    distribution; we just need to ensure we don't introduce randomness."""
    skills = SkillLibrary(
        dir_path=tmp_path / "skills_dir", db_path=tmp_path / "sk.db",
    )
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")

    for i in range(4):
        skills.store(_skill(
            id_=f"sk{i}", trigger=f"topic {i}",
            trials=10 + i, successes=8 + i,
        ))
    for i in range(6):
        mem.store(_ep(
            id_=f"e{i}", task_text=f"topic {i % 4}",
            skills_used=[f"sk{i % 4}"],
        ))

    from verimem.hippo_pagerank import retrieve_pagerank

    a = retrieve_pagerank(
        query="topic 1", skills=skills, memory=mem, top_k=5,
    )
    b = retrieve_pagerank(
        query="topic 1", skills=skills, memory=mem, top_k=5,
    )
    # node ids and order must match
    assert [(n, k) for n, k, _ in a] == [(n, k) for n, k, _ in b]
    # scores must match within float tolerance
    for (_, _, sa), (_, _, sb) in zip(a, b, strict=False):
        assert abs(sa - sb) < 1e-9


# ---------- Test 4: empty inputs produce empty result --------------------


def test_empty_skills_or_memory_returns_empty(tmp_path):
    skills = SkillLibrary(
        dir_path=tmp_path / "skills_dir", db_path=tmp_path / "sk.db",
    )
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    from verimem.hippo_pagerank import retrieve_pagerank
    assert retrieve_pagerank(
        query="anything", skills=skills, memory=mem, top_k=3,
    ) == []


# ---------- Test 5: PPR converges even on disconnected components --------


def test_pagerank_handles_isolated_nodes(tmp_path):
    """Disconnected components in the bipartite graph (orphan skills,
    orphan episodes) shouldn't crash the PPR call. NetworkX handles
    this — we just need to not feed it a degenerate input."""
    skills = SkillLibrary(
        dir_path=tmp_path / "skills_dir", db_path=tmp_path / "sk.db",
    )
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills.store(_skill(
        id_="orphan_sk", trigger="x", trials=5, successes=4,
    ))
    mem.store(_ep(
        id_="orphan_ep", task_text="y", skills_used=[],
    ))
    from verimem.hippo_pagerank import retrieve_pagerank
    result = retrieve_pagerank(
        query="anything", skills=skills, memory=mem, top_k=2,
    )
    assert len(result) <= 2  # doesn't crash, returns something
