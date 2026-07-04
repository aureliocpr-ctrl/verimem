"""Bayesian skill selection — one primitive replacing three heuristics.

Today the wake loop decides which skill to inject by stacking three
disconnected gates:

  1. `WakeAgent._retrieve_skills`   — top-k cosine, ignores fitness
  2. `WakeAgent._try_compiled_macro` — binary `fitness_mean ≥ 0.80`
  3. `WakeAgent._forward_replay_block` — binary `fitness_mean ≥ N`

That stack lies about how it decides: a skill with cosine 0.92 and
fitness 0.30 beats a skill with cosine 0.85 and fitness 0.85, because
similarity decides ranking and fitness only acts as a binary cutoff.
There is no place in the system where relevance and reliability meet.

This module is that place.

For each candidate skill, draw θ from `Beta(α + successes, β + failures)`
— Thompson sampling on the same posterior that already powers
`Skill.fitness_mean`, `fitness_lower_bound`, `fitness_variance`
(see skill.py:74-99). Then compose:

    score = cosine(task, skill_embedding) * θ

Both factors live in [0, 1]; their product does too. The semantics
follow the intuition you would defend out loud:

  • a skill must be relevant AND reliable to win;
  • either is necessary; neither is sufficient.

Why Thompson rather than UCB1 or epsilon-greedy:
  The Beta posterior already carries the right amount of exploration —
  an untested skill (Beta(1,1) under uniform prior) samples uniformly on
  [0,1], so it gets natural optimism without an arbitrary `c` knob.
  As trials accumulate, the posterior tightens and exploration fades on
  its own. Thompson is also one numpy line per skill; UCB1 needs a
  log-trials denominator and a tuned constant.

Determinism is the caller's responsibility — pass a seeded
`np.random.default_rng(seed)` to fix the output.
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .config import CONFIG
from .episode import Episode
from .skill import Skill


@dataclass(frozen=True)
class Choice:
    """One skill's evaluation in a consideration set.

    Frozen so the ranked list can be shared with observability sinks
    (dashboards, lineage tracking, episode notes) without
    spooky-action-at-a-distance mutation. Carrying `relevance` and
    `theta` separately — not just the combined `score` — is what
    lets the dashboard show *why* a skill was picked, not just that
    it was.
    """
    skill: Skill
    relevance: float       # cosine similarity, clipped to [0, 1]
    theta: float           # Thompson sample from Beta posterior
    score: float           # the combined product


def _unit_norm(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def _skill_embedding(
    skill: Skill,
    encoder: Callable[[str], np.ndarray] | None,
) -> np.ndarray:
    """Resolve the vector to compare against the task embedding.

    Prefer the Hebbian-learned vector when present (that's the whole
    point of having one). Otherwise fall back to encoding
    `name + "\\n" + trigger` — exactly the convention
    `WakeAgent._skill_similarity` already uses, kept symmetric here so
    a skill's score doesn't change when this primitive replaces the
    legacy retrieval call.

    Raises ValueError when neither path is available. The earlier code
    silently returned a zero vector in that case, which is exactly the
    kind of silent failure the FORGIA forbids — a skill with no
    embedding and no encoder is not relevance-zero, it is
    *unevaluable*, and saying so is more honest than scoring it 0.
    """
    if skill.learned_embedding is not None:
        return np.asarray(skill.learned_embedding, dtype=np.float32)
    if encoder is None:
        raise ValueError(
            f"skill {skill.id!r} has no learned_embedding and no encoder "
            "was supplied — refusing to score with a zero vector"
        )
    return encoder(f"{skill.name}\n{skill.trigger}")


def consider_skills(
    skills: list[Skill],
    task_embedding: np.ndarray,
    *,
    encoder: Callable[[str], np.ndarray] | None = None,
    rng: np.random.Generator | None = None,
    prior_alpha: float | None = None,
    prior_beta: float | None = None,
) -> list[Choice]:
    """Score every candidate, return Choices ranked by score descending.

    Defaults for `prior_alpha`/`prior_beta` come from CONFIG so a test
    that adjusts the prior also affects this primitive — the same
    convention `Skill.fitness_mean` already follows. Passing them
    explicitly is supported for sensitivity studies.

    Empty input → empty output. No crashes; the wake loop handles the
    empty case at the call site.
    """
    if not skills:
        return []

    rng = rng if rng is not None else np.random.default_rng()
    alpha = (
        prior_alpha
        if prior_alpha is not None
        else CONFIG.fitness_prior_alpha
    )
    beta_p = (
        prior_beta
        if prior_beta is not None
        else CONFIG.fitness_prior_beta
    )

    task_n = _unit_norm(np.asarray(task_embedding, dtype=np.float32))

    out: list[Choice] = []
    for s in skills:
        skill_n = _unit_norm(_skill_embedding(s, encoder))
        # Cosine, clipped to [0, 1]. A negative cosine means the skill
        # embedding points opposite the task — that is irrelevance,
        # not anti-relevance, so 0 is the right floor.
        relevance = float(np.clip(np.dot(task_n, skill_n), 0.0, 1.0))
        theta = float(rng.beta(
            alpha + s.successes,
            beta_p + (s.trials - s.successes),
        ))
        out.append(Choice(
            skill=s, relevance=relevance, theta=theta,
            score=relevance * theta,
        ))

    out.sort(key=lambda c: -c.score)
    return out


def select_top(choices: list[Choice], k: int) -> list[Skill]:
    """Trivial slice of the ranked Choice list.

    Kept as a separate function so callers that want richer policies
    — diversity-aware selection, exploration-weighted re-ranking,
    cost-budgeted picking — can compose them against the same Choice
    list without rewriting the scoring step.
    """
    return [c.skill for c in choices[:k]]


# ----- Episode priority — gemello of `consider_skills` -------------------
#
# Episodes are NOT Bernoulli trials with a Beta posterior — they're single
# events. So the math here is composition, not sampling: combine cosine
# relevance with an exponential-decay recency factor.
#
# Used by the wake loop to pick the most informative failure / success
# twin from a candidate pool, replacing three places where the legacy
# code did `failed_for_skill[0]` (arbitrary) or token-overlap heuristics.


@dataclass(frozen=True)
class EpisodeChoice:
    """One episode's evaluation. Frozen for the same reason as `Choice`:
    the wake-loop dashboard reads these without fear of mutation."""
    episode: Episode
    relevance: float       # cosine similarity to the query, [0, 1]
    recency: float         # exp decay, [0, 1] (1 = right now, 0 = ancient)
    score: float           # `relevance + recency_weight * recency`


def _recency_factor(
    episode_created_at: float, now: float, tau_s: float,
) -> float:
    """Exponential decay: 1.0 right now, 1/e after `tau_s` seconds.

    Clamped at [0, 1] so that an episode created in the future (clock
    skew, replay) doesn't get an inflated score. The convention used
    by the sleep-cycle's `replay_priority_recent` is the same — keeps
    the two selectors comparable.
    """
    age = max(0.0, now - episode_created_at)
    return math.exp(-age / tau_s) if tau_s > 0 else 0.0


def consider_episodes(
    episodes: list[Episode],
    query_embedding: np.ndarray,
    *,
    episode_embeddings: dict[str, np.ndarray],
    now: float | None = None,
    recency_weight: float | None = None,
    recency_tau_s: float | None = None,
) -> list[EpisodeChoice]:
    """Score every candidate episode and return ranked descending.

    Pure function. No randomness — episodes don't have a posterior to
    sample from, only a deterministic affine score
    `relevance + recency_weight * recency`.

    `episode_embeddings` MUST contain an entry for every episode in
    `episodes`. We don't compute embeddings here on purpose — the
    caller already has them in scope (the wake loop already encoded
    the failure / success episodes for the divergence pipeline) so
    re-encoding would be wasteful. Missing entry ⇒ `KeyError` rather
    than a silent zero-vector default; FORGIA forbids that fallback.

    `recency_weight` and `recency_tau_s` default to CONFIG values so
    a global tuning knob propagates here without callers needing to
    pass them. `now` defaults to `time.time()` — pass an explicit
    value in tests to make the result deterministic.
    """
    if not episodes:
        return []

    rec_w = (
        recency_weight
        if recency_weight is not None
        else getattr(CONFIG, "episode_priority_recency_weight", 0.3)
    )
    tau_s = (
        recency_tau_s
        if recency_tau_s is not None
        else getattr(CONFIG, "episode_priority_recency_tau_s", 7 * 86400)
    )
    now = now if now is not None else time.time()

    q = _unit_norm(np.asarray(query_embedding, dtype=np.float32))

    out: list[EpisodeChoice] = []
    for ep in episodes:
        if ep.id not in episode_embeddings:
            raise KeyError(
                f"missing embedding for episode {ep.id!r} — "
                "consider_episodes refuses to fall back to a zero vector"
            )
        emb = _unit_norm(episode_embeddings[ep.id].astype(np.float32))
        relevance = float(np.clip(np.dot(q, emb), 0.0, 1.0))
        recency = _recency_factor(ep.created_at, now, tau_s)
        out.append(EpisodeChoice(
            episode=ep, relevance=relevance, recency=recency,
            score=relevance + rec_w * recency,
        ))

    out.sort(key=lambda c: -c.score)
    return out


__all__ = [
    "Choice",
    "EpisodeChoice",
    "consider_episodes",
    "consider_skills",
    "select_top",
]
