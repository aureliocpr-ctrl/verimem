"""Bench: Bayesian skill selection vs legacy top-k cosine.

The three dimensions were declared in FORGIA.md BEFORE running this:

  1. Hit-rate@1 on synthetic tasks with a known "ideal" skill (high
     cosine + high fitness). The Ferrari path should pick the ideal
     skill more often.

  2. Wasted compute: number of episodes that select a skill with
     `fitness_lower_bound < 0.30`. Such skills are pessimistically
     unreliable; sending them to the wake LLM is paying tokens for
     a bad bet. The Ferrari path should burn fewer.

  3. Selection diversity (Shannon entropy of the pick distribution
     across tasks): we DO NOT want the Bayesian path to collapse
     onto one skill. Entropy should stay roughly comparable to the
     legacy path — losing diversity would mean the system stopped
     exploring.

If at least 3 of 3 metrics improve (or stay neutral) for the Bayesian
path, the pezzo is forged.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.selection import consider_skills
from verimem.skill import Skill


@dataclass
class BenchOutcome:
    name: str
    hit_rate_at_1: float
    wasted_compute_episodes: int
    selection_entropy: float
    n_tasks: int

    def render(self) -> str:
        return (
            f"  {self.name:<10}  "
            f"hit@1={self.hit_rate_at_1:.3f}  "
            f"wasted={self.wasted_compute_episodes}/{self.n_tasks}  "
            f"entropy={self.selection_entropy:.3f}"
        )


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def _make_skill_population(
    n_pairs: int, dim: int, rng: np.random.Generator,
) -> list[Skill]:
    """Build a library of skill *pairs*: each pair shares a near-identical
    embedding direction but very different fitness. This is the classic
    failure mode of top-k cosine: a 'bad twin' (low fitness) sits right
    next to a 'good twin' (high fitness), and cosine alone can't tell
    them apart. Bayesian re-rank should prefer the good twin.

    Returns 2 * n_pairs skills.
    """
    skills: list[Skill] = []
    for i in range(n_pairs):
        # Family direction
        family = _unit(rng.standard_normal(dim).astype(np.float32))

        # Bad twin — slightly perturbed, low fitness (3/15 = 0.20)
        bad_emb = _unit(family + 0.05 * rng.standard_normal(dim).astype(np.float32))
        skills.append(Skill(
            id=f"bad_{i:02d}", name=f"bad_{i:02d}",
            trigger=f"family {i}", body="...",
            trials=15, successes=3,  # mean ~0.20
            learned_embedding=bad_emb.tolist(),
        ))

        # Good twin — slightly perturbed, high fitness (17/20 = 0.85)
        good_emb = _unit(family + 0.05 * rng.standard_normal(dim).astype(np.float32))
        skills.append(Skill(
            id=f"good_{i:02d}", name=f"good_{i:02d}",
            trigger=f"family {i}", body="...",
            trials=20, successes=17,  # mean ~0.85
            learned_embedding=good_emb.tolist(),
        ))
    return skills


def _make_tasks(
    skills: list[Skill], n: int, dim: int, rng: np.random.Generator,
) -> list[np.ndarray]:
    """Each task is a 'family' query: cosine-equally-close to both twins,
    but only the good twin is the right pick.

    Building tasks as the average of bad+good twin embeddings places them
    in the cosine midpoint — both are competitive on relevance, fitness
    is the only useful signal. This is exactly the scenario where the
    legacy top-cosine policy is forced to pick arbitrarily.
    """
    tasks: list[np.ndarray] = []
    bad_skills = [s for s in skills if s.id.startswith("bad_")]
    good_skills = [s for s in skills if s.id.startswith("good_")]
    assert len(bad_skills) == len(good_skills)
    for _ in range(n):
        idx = int(rng.integers(0, len(bad_skills)))
        bad = np.asarray(bad_skills[idx].learned_embedding, dtype=np.float32)
        good = np.asarray(good_skills[idx].learned_embedding, dtype=np.float32)
        # Symmetric midpoint + small noise
        mid = (bad + good) / 2.0
        mid += rng.standard_normal(dim).astype(np.float32) * 0.05
        tasks.append(_unit(mid))
    return tasks


def _ideal_skills_for_task(
    skills: list[Skill], task_emb: np.ndarray,
    relevance_floor: float = 0.50,
    fitness_floor: float = 0.50,
) -> set[str]:
    """The set of 'good enough' skills: any skill simultaneously cosine-
    relevant AND with proven fitness.

    With the bad/good-twin construction, the only ideal skill for each
    task is its 'good' twin — the bad twin is cosine-equal but fails
    the fitness floor.
    """
    out: set[str] = set()
    for s in skills:
        emb = np.asarray(s.learned_embedding, dtype=np.float32)
        cos = float(np.dot(_unit(task_emb), _unit(emb)))
        if cos >= relevance_floor and s.fitness_mean >= fitness_floor:
            out.add(s.id)
    return out


def _entropy(counts: dict[str, int]) -> float:
    """Shannon entropy of the empirical pick distribution (in nats)."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            h -= p * math.log(p)
    return h


def _run_bench(
    name: str,
    skills: list[Skill],
    tasks: list[np.ndarray],
    *,
    bayesian: bool,
    rng_seed: int,
) -> BenchOutcome:
    """Run the chosen policy across all tasks and tally the 3 metrics."""
    pick_counts: dict[str, int] = {}
    hits = 0
    n_eligible = 0
    wasted = 0

    rng = np.random.default_rng(rng_seed)

    for t_emb in tasks:
        ideal = _ideal_skills_for_task(skills, t_emb)
        if not ideal:
            continue
        n_eligible += 1

        if bayesian:
            choices = consider_skills(skills, t_emb, rng=rng)
            chosen = choices[0].skill if choices else None
        else:
            # Legacy: top-1 by cosine, ignoring fitness.
            scored = []
            for s in skills:
                emb = np.asarray(s.learned_embedding, dtype=np.float32)
                cos = float(np.dot(_unit(t_emb), _unit(emb)))
                scored.append((cos, s))
            scored.sort(key=lambda x: -x[0])
            chosen = scored[0][1] if scored else None

        if chosen is None:
            continue
        pick_counts[chosen.id] = pick_counts.get(chosen.id, 0) + 1

        if chosen.id in ideal:
            hits += 1
        if chosen.fitness_lower_bound < 0.30:
            wasted += 1

    return BenchOutcome(
        name=name,
        hit_rate_at_1=hits / n_eligible if n_eligible else 0.0,
        wasted_compute_episodes=wasted,
        selection_entropy=_entropy(pick_counts),
        n_tasks=n_eligible,
    )


def main() -> int:
    dim = 32
    n_pairs = 16  # 32 skills total — 16 good-twin / 16 bad-twin
    n_tasks = 400

    rng = np.random.default_rng(seed=20260508)
    skills = _make_skill_population(n_pairs, dim, rng)
    tasks = _make_tasks(skills, n_tasks, dim, rng)

    legacy = _run_bench(
        "legacy", skills, tasks, bayesian=False, rng_seed=1,
    )
    ferrari = _run_bench(
        "ferrari", skills, tasks, bayesian=True, rng_seed=1,
    )

    print()
    print("Three-dimension bench: skill selection")
    print(legacy.render())
    print(ferrari.render())
    print()

    # Verdict — declared in FORGIA.md before measuring.
    print("Verdict (3 dimensions, declared up front):")
    print(
        f"  hit@1:  ferrari {ferrari.hit_rate_at_1:.3f} vs legacy "
        f"{legacy.hit_rate_at_1:.3f}  "
        f"{'+' if ferrari.hit_rate_at_1 > legacy.hit_rate_at_1 else '~'}"
    )
    print(
        f"  wasted: ferrari {ferrari.wasted_compute_episodes:>3} vs legacy "
        f"{legacy.wasted_compute_episodes:>3}  "
        f"{'+' if ferrari.wasted_compute_episodes < legacy.wasted_compute_episodes else '~'}"
    )
    print(
        f"  entropy: ferrari {ferrari.selection_entropy:.3f} vs legacy "
        f"{legacy.selection_entropy:.3f}  "
        f"{'+' if ferrari.selection_entropy >= 0.5 * legacy.selection_entropy else '!'}"
    )
    print()

    improvements = 0
    if ferrari.hit_rate_at_1 > legacy.hit_rate_at_1:
        improvements += 1
    if ferrari.wasted_compute_episodes < legacy.wasted_compute_episodes:
        improvements += 1
    # Entropy: collapse is the only failure mode we worry about — it
    # being equal or higher is fine.
    if ferrari.selection_entropy >= 0.5 * legacy.selection_entropy:
        improvements += 1

    print(f"Improvements: {improvements}/3")
    return 0 if improvements >= 3 else 1


if __name__ == "__main__":
    sys.exit(main())
