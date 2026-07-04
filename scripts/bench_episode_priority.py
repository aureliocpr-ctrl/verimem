"""Bench: episode priority — Ferrari vs legacy [0] vs token-overlap.

Three dimensions declared BEFORE measuring (FORGIA discipline):

  1. Top-pick alignment with ground-truth informativity:
     Define `informativity = cosine(task, episode) * recency_factor`
     as the synthetic ground truth. For each task, the "best" failure
     to surface is the one with max informativity. Measure how often
     each policy picks it.

       - legacy:        always picks `candidates[0]` (arbitrary order)
       - token-overlap: picks max lowercase-token-overlap
       - ferrari:       `consider_episodes` (cosine + recency_weight)

  2. Mean informativity of the picked episode:
     Average across tasks of the informativity score of whichever
     episode each policy picked. Higher = more useful for the LLM.

  3. Robustness against task wording shift (REASONABLENESS, not maximum):
     Run the same tasks both as the original embedding AND as a
     paraphrase (perturbed embedding). Measure pick stability.
     CAVEAT: legacy[0] and token-overlap will both score 1.0 here
     trivially — legacy ignores the query, token-overlap depends only
     on the title. That's not a virtue, it's stupidity-invariance.
     The Ferrari should be stable enough (≥ 0.5) WITHOUT being trivially
     stable. Anything above 50% means cosmetic paraphrase doesn't
     destabilise the pick.

The Ferrari policy must beat both legacy and token-overlap on (1) and (2),
and stay reasonably stable (≥ 0.5) on (3).
"""
from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.episode import Episode
from engram.selection import consider_episodes


@dataclass
class PolicyOutcome:
    name: str
    n_top_picks: int
    n_total: int
    mean_informativity: float
    stability_under_paraphrase: float

    def render(self) -> str:
        return (
            f"  {self.name:<14} "
            f"top={self.n_top_picks:>3}/{self.n_total}  "
            f"mean_info={self.mean_informativity:.3f}  "
            f"stable={self.stability_under_paraphrase:.3f}"
        )


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def _make_pool(
    n_candidates: int, dim: int, now: float, rng: np.random.Generator,
) -> tuple[list[Episode], dict[str, np.ndarray]]:
    """A pool of past failures with varied (recency, content)."""
    eps: list[Episode] = []
    embs: dict[str, np.ndarray] = {}
    for i in range(n_candidates):
        # Age uniformly between 1 minute and 60 days
        age_s = float(rng.integers(60, 60 * 86400))
        emb = _unit(rng.standard_normal(dim).astype(np.float32))
        # Token soup proxy for the title — used by token-overlap policy.
        # Each failure carries 4 random vocabulary tokens.
        title = " ".join(f"w{int(rng.integers(0, 50))}" for _ in range(4))
        ep = Episode(
            id=f"f{i:02d}",
            task_id="t", task_text=title,
            outcome="failure",
            created_at=now - age_s,
        )
        eps.append(ep)
        embs[ep.id] = emb
    return eps, embs


def _informativity(
    task_emb: np.ndarray, ep_emb: np.ndarray, ep: Episode, now: float,
    tau_s: float,
) -> float:
    cos = float(np.clip(np.dot(_unit(task_emb), _unit(ep_emb)), 0.0, 1.0))
    age = max(0.0, now - ep.created_at)
    rec = math.exp(-age / tau_s)
    return cos * rec


def _legacy_pick(eps: list[Episode]) -> Episode:
    return eps[0]


def _token_overlap_pick(eps: list[Episode], task_text: str) -> Episode:
    f_tokens = set(task_text.lower().split())
    return max(
        eps,
        key=lambda ep: len(f_tokens & set(ep.task_text.lower().split())),
    )


def _ferrari_pick(
    eps: list[Episode], task_emb: np.ndarray,
    embs: dict[str, np.ndarray], now: float,
) -> Episode:
    choices = consider_episodes(
        eps, task_emb, episode_embeddings=embs, now=now,
        recency_weight=0.3, recency_tau_s=7 * 86400,
    )
    return choices[0].episode


def _evaluate(
    policy_name: str,
    pick_fn,
    tasks: list[tuple[str, np.ndarray, np.ndarray]],  # (text, emb, paraphrase_emb)
    pool: list[Episode],
    embs: dict[str, np.ndarray],
    now: float,
) -> PolicyOutcome:
    tau_s = 7 * 86400
    n_top = 0
    info_sum = 0.0
    stable = 0
    for task_text, task_emb, para_emb in tasks:
        # Ground-truth optimal pick
        scored = [
            (_informativity(task_emb, embs[ep.id], ep, now, tau_s), ep)
            for ep in pool
        ]
        scored.sort(key=lambda x: -x[0])
        gt_best = scored[0][1]

        picked = pick_fn(task_text, task_emb)
        if picked.id == gt_best.id:
            n_top += 1
        info_sum += _informativity(task_emb, embs[picked.id], picked, now, tau_s)

        para_picked = pick_fn(task_text, para_emb)
        if para_picked.id == picked.id:
            stable += 1

    return PolicyOutcome(
        name=policy_name,
        n_top_picks=n_top,
        n_total=len(tasks),
        mean_informativity=info_sum / len(tasks),
        stability_under_paraphrase=stable / len(tasks),
    )


def main() -> int:
    rng = np.random.default_rng(seed=20260508)
    dim = 32
    n_candidates = 8
    n_tasks = 300
    now = time.time()

    pool, embs = _make_pool(n_candidates, dim, now, rng)

    tasks: list[tuple[str, np.ndarray, np.ndarray]] = []
    for _ in range(n_tasks):
        t_emb = _unit(rng.standard_normal(dim).astype(np.float32))
        # Paraphrase = same task with small perturbation
        para = _unit(t_emb + 0.15 * rng.standard_normal(dim).astype(np.float32))
        title = " ".join(f"w{int(rng.integers(0, 50))}" for _ in range(4))
        tasks.append((title, t_emb, para))

    legacy = _evaluate(
        "legacy[0]",
        lambda title, e: _legacy_pick(pool),
        tasks, pool, embs, now,
    )
    token = _evaluate(
        "token-overlap",
        lambda title, e: _token_overlap_pick(pool, title),
        tasks, pool, embs, now,
    )
    ferrari = _evaluate(
        "ferrari",
        lambda title, e: _ferrari_pick(pool, e, embs, now),
        tasks, pool, embs, now,
    )

    print()
    print(f"Bench: episode priority on {n_tasks} synthetic tasks "
          f"(pool of {n_candidates} failures)")
    print()
    print(legacy.render())
    print(token.render())
    print(ferrari.render())

    print()
    print("Verdict (3 dimensions, declared up front):")
    print(
        f"  top@1:        ferrari {ferrari.n_top_picks} vs "
        f"legacy {legacy.n_top_picks} vs token {token.n_top_picks}"
    )
    print(
        f"  mean_info:    ferrari {ferrari.mean_informativity:.3f} vs "
        f"legacy {legacy.mean_informativity:.3f} vs token {token.mean_informativity:.3f}"
    )
    print(
        f"  stability:    ferrari {ferrari.stability_under_paraphrase:.3f} vs "
        f"legacy {legacy.stability_under_paraphrase:.3f} vs token {token.stability_under_paraphrase:.3f}"
    )

    ferrari_wins = (
        ferrari.n_top_picks > max(legacy.n_top_picks, token.n_top_picks)
        and ferrari.mean_informativity > max(legacy.mean_informativity, token.mean_informativity)
        and ferrari.stability_under_paraphrase >= 0.5
    )
    return 0 if ferrari_wins else 1


if __name__ == "__main__":
    sys.exit(main())
