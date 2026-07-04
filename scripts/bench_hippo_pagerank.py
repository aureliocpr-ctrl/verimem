"""Bench: HippoRAG-style PPR — cross-amplification of skill ↔ episode.

Three dimensions declared BEFORE measuring (FORGIA discipline):

  1. CROSS-AMPLIFICATION:
     A skill connected to many cosine-relevant episodes should rank
     ABOVE a skill of identical fitness with no relevant episode
     neighbours. Cosine-only retrieval cannot make this distinction;
     PPR can. Measure: rank gap between "busy" and "isolated" skills.

  2. CROSS-AMPLIFICATION (the other direction):
     An episode that uses a high-fitness skill should rank ABOVE a
     similar-cosine episode that uses a low-fitness skill. Measure:
     rank gap between "high-fitness-using" and "low-fitness-using"
     episodes.

  3. MIX HEALTH:
     The top-k returned should be a mix of skills and episodes — not
     collapse to all-skills or all-episodes. Measure: ratio in top-5.

If 1 > 0 AND 2 > 0 AND 3 stays in [0.2, 0.8], the pezzo is forged.
"""
from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.episode import Episode, Trace
from engram.hippo_pagerank import retrieve_pagerank
from engram.memory import EpisodicMemory
from engram.skill import Skill, SkillLibrary


@dataclass
class BenchOutcome:
    skill_amplification: int    # rank(busy) - rank(isolated), positive = good
    episode_amplification: int  # rank(uses high-fit) - rank(uses low-fit)
    skill_share: float          # fraction of top-k that are skills


def _make_world(
    skills_dir: Path, db_dir: Path,
) -> tuple[SkillLibrary, EpisodicMemory]:
    """4 skills + 8 episodes designed to expose PPR's cross-amplification.

    sk_busy_high   : fitness ~0.85, 3 relevant episodes
    sk_isolated_high: fitness ~0.85, 0 episodes (orphan)
    sk_busy_low    : fitness ~0.20, 3 relevant episodes
    sk_isolated_low: fitness ~0.20, 0 episodes
    """
    skills = SkillLibrary(
        dir_path=skills_dir / "skills",
        db_path=skills_dir / "sk.db",
    )
    mem = EpisodicMemory(db_path=db_dir / "ep.db")

    skills.store(Skill(
        id="sk_busy_high", name="sk_busy_high",
        trigger="fix calc.py arithmetic",
        body="x", status="promoted",
        trials=20, successes=18,
    ))
    skills.store(Skill(
        id="sk_isolated_high", name="sk_isolated_high",
        trigger="fix calc.py arithmetic",
        body="x", status="promoted",
        trials=20, successes=18,
    ))
    skills.store(Skill(
        id="sk_busy_low", name="sk_busy_low",
        trigger="fix calc.py arithmetic",
        body="x", status="promoted",
        trials=20, successes=4,
    ))
    skills.store(Skill(
        id="sk_isolated_low", name="sk_isolated_low",
        trigger="fix calc.py arithmetic",
        body="x", status="promoted",
        trials=20, successes=4,
    ))

    # 3 episodes for sk_busy_high
    for i in range(3):
        mem.store(Episode(
            id=f"e_busy_high_{i}",
            task_id="t",
            task_text="fix calc.py arithmetic bug",
            outcome="success", final_answer="ok",
            skills_used=["sk_busy_high"],
            traces=[Trace(
                step=1, thought="x", action="x", action_input="{}",
                observation="x",
            )],
        ))
    # 3 episodes for sk_busy_low
    for i in range(3):
        mem.store(Episode(
            id=f"e_busy_low_{i}",
            task_id="t",
            task_text="fix calc.py arithmetic bug",
            outcome="failure", final_answer="ok",
            skills_used=["sk_busy_low"],
            traces=[Trace(
                step=1, thought="x", action="x", action_input="{}",
                observation="x",
            )],
        ))
    # 1 unrelated episode
    mem.store(Episode(
        id="e_unrelated",
        task_id="t",
        task_text="deploy frontend to production",
        outcome="success", final_answer="ok",
        skills_used=[],
        traces=[Trace(
            step=1, thought="x", action="x", action_input="{}",
            observation="x",
        )],
    ))
    # 1 isolated relevant episode (same query, no skill_used)
    mem.store(Episode(
        id="e_isolated",
        task_id="t",
        task_text="fix calc.py arithmetic bug",
        outcome="success", final_answer="ok",
        skills_used=[],
        traces=[Trace(
            step=1, thought="x", action="x", action_input="{}",
            observation="x",
        )],
    ))
    return skills, mem


def _rank_of(node_id: str, ranked: list[tuple[str, str, float]]) -> int:
    """0-indexed rank of node_id in ranked list, or len(ranked)+1 if absent."""
    for i, (n, _kind, _score) in enumerate(ranked):
        if n == node_id:
            return i
    return len(ranked) + 1


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        skills, mem = _make_world(root, root)
        ranked = retrieve_pagerank(
            query="fix calc.py arithmetic bug",
            skills=skills, memory=mem,
            top_k=12,  # see everything
        )

    # Cross-amplification 1: among the 2 high-fitness skills,
    # the busy one should rank lower index (= higher) than the isolated.
    rank_busy_high = _rank_of("sk_busy_high", ranked)
    rank_iso_high = _rank_of("sk_isolated_high", ranked)
    skill_amp = rank_iso_high - rank_busy_high

    # Cross-amplification 2: episodes using high-fitness skill should
    # outrank similar-cosine episodes using low-fitness skill.
    high_eps = [
        _rank_of(f"e_busy_high_{i}", ranked) for i in range(3)
    ]
    low_eps = [
        _rank_of(f"e_busy_low_{i}", ranked) for i in range(3)
    ]
    avg_rank_high = sum(high_eps) / len(high_eps)
    avg_rank_low = sum(low_eps) / len(low_eps)
    ep_amp = round(avg_rank_low - avg_rank_high)

    # Mix: ratio of skills in top-5
    top5 = ranked[:5]
    n_skills_in_top5 = sum(1 for _, kind, _ in top5 if kind == "skill")
    skill_share = n_skills_in_top5 / max(1, len(top5))

    outcome = BenchOutcome(
        skill_amplification=skill_amp,
        episode_amplification=ep_amp,
        skill_share=skill_share,
    )

    print()
    print("Bench: HippoRAG-style PPR — dual-cue retrieval cross-amplification")
    print()
    print("  ranked (top-12):")
    for i, (node_id, kind, score) in enumerate(ranked):
        print(f"    {i:>2}. {kind:<8} {node_id:<25} score={score:.4f}")
    print()
    print(f"  skill cross-amp:    rank(isolated)-rank(busy) = "
          f"{rank_iso_high}-{rank_busy_high} = {skill_amp}")
    print(f"  episode cross-amp:  avg_rank(low_fit)-avg_rank(high_fit) = "
          f"{avg_rank_low:.1f}-{avg_rank_high:.1f} = {ep_amp}")
    print(f"  top-5 mix:          {n_skills_in_top5} skills + "
          f"{5-n_skills_in_top5} episodes  (skill share {skill_share:.2f})")
    print()
    print("Verdict (3 dimensions, declared up front):")
    print(
        f"  skill amplification > 0:       {skill_amp}  "
        f"{'+' if skill_amp > 0 else '!'}"
    )
    print(
        f"  episode amplification > 0:     {ep_amp}  "
        f"{'+' if ep_amp > 0 else '!'}"
    )
    print(
        f"  mix in [0.2, 0.8]:             {skill_share:.2f}  "
        f"{'+' if 0.2 <= skill_share <= 0.8 else '!'}"
    )

    forged = (
        outcome.skill_amplification > 0
        and outcome.episode_amplification > 0
        and 0.2 <= outcome.skill_share <= 0.8
    )
    return 0 if forged else 1


if __name__ == "__main__":
    sys.exit(main())
