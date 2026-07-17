"""Tests for `verimem.selection` — Bayesian skill choice.

The selection primitive replaces three scattered heuristics:
  • `WakeAgent._retrieve_skills` (top-k cosine, ignores fitness)
  • `WakeAgent._try_compiled_macro` (binary fitness gate ≥ 0.80)
  • `WakeAgent._forward_replay_block` (binary `skills[0].fitness ≥ N`)

Replacement: ONE call combining (relevance, posterior fitness,
exploration bonus) — Thompson-sampled Beta posterior weighted by
cosine relevance.

Why Thompson over UCB or epsilon-greedy:
  • The Beta posterior is already in `Skill.fitness_*` properties
    (skill.py:74-99). Thompson is the natural sampling primitive —
    UCB requires an arbitrary confidence parameter, epsilon-greedy
    discards information. Thompson gets calibrated exploration *for free*
    from the posterior variance: an unproved skill (trials=0) has
    a wide Beta(1,1) so it samples high more often.
  • Thompson is principled, deterministic-with-seed, and one numpy line.

Three measurable dimensions (declared BEFORE results — see FORGIA.md):
  1. Hit-rate@1 must improve on tasks with a known success-twin.
  2. Tokens wasted on `fitness_lower_bound < 0.30` skills must drop.
  3. Selection entropy must stay ≥ 0.5 — no skill collapse.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from verimem import embedding
from verimem.selection import Choice, consider_skills, select_top
from verimem.skill import Skill


def _make_skill(
    name: str,
    *,
    trials: int = 0,
    successes: int = 0,
    learned_embedding: list[float] | None = None,
) -> Skill:
    s = Skill(
        id=name, name=name, trigger=name, body="x",
        trials=trials, successes=successes,
        learned_embedding=learned_embedding,
    )
    return s


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


# ---------- Test 1: fitness changes the ranking, not just cosine ----------


def test_high_fitness_beats_similarity_alone_in_expectation():
    """Skill A: cosine 0.92, fitness 0.30 (lots of failures).
    Skill B: cosine 0.85, fitness 0.85 (lots of successes).

    Top-k cosine alone picks A. Bayesian-weighted picks B in
    expectation — its posterior mass is concentrated on a high
    success rate; A's is concentrated low. The cosine difference
    (0.07) is much smaller than the fitness difference (0.55).
    """
    task_emb = _unit(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    a_emb = _unit(np.array([0.92, np.sqrt(1 - 0.92**2), 0.0], dtype=np.float32))
    b_emb = _unit(np.array([0.85, np.sqrt(1 - 0.85**2), 0.0], dtype=np.float32))

    a = _make_skill("a", trials=20, successes=6, learned_embedding=a_emb.tolist())
    b = _make_skill("b", trials=20, successes=17, learned_embedding=b_emb.tolist())

    rng = np.random.default_rng(42)
    wins_b = 0
    n_trials = 200
    for _ in range(n_trials):
        choices = consider_skills([a, b], task_emb, rng=rng)
        winner = choices[0].skill
        if winner.id == "b":
            wins_b += 1

    # B should win the lion's share — posterior mass is overwhelmingly
    # concentrated on a higher success rate, far outweighing the small
    # cosine gap.
    assert wins_b >= 0.80 * n_trials, (
        f"high-fitness skill won only {wins_b}/{n_trials} times — "
        "fitness isn't actually steering the choice"
    )


# ---------- Test 2: untested skills retain exploration probability --------


def test_unexplored_skill_gets_exploration_chance():
    """A new skill (trials=0) has a wide Beta(1,1) posterior — uniform
    over [0,1]. It must occasionally win against a moderately-good
    proven skill, otherwise we're full-exploitation and can't learn.

    Sanity invariant: under Thompson sampling, an unexplored skill
    with comparable cosine wins ~50% of the time vs a proven skill
    with mean ~0.7 (because Beta(1,1) samples > 0.7 ~30% of the time,
    and similarities are equal).
    """
    task_emb = _unit(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    same = _unit(np.array([0.90, np.sqrt(1 - 0.90**2), 0.0], dtype=np.float32))

    new_skill = _make_skill("new", learned_embedding=same.tolist())  # trials=0
    proven = _make_skill(
        "proven", trials=30, successes=21, learned_embedding=same.tolist(),
    )

    rng = np.random.default_rng(7)
    wins_new = 0
    n_trials = 400
    for _ in range(n_trials):
        choices = consider_skills([new_skill, proven], task_emb, rng=rng)
        if choices[0].skill.id == "new":
            wins_new += 1

    # Beta(1,1) > 0.7 has probability 0.3 — the new skill should win
    # roughly that fraction of the time (give or take noise).
    assert 0.20 * n_trials < wins_new < 0.45 * n_trials, (
        f"unexplored-skill win rate {wins_new}/{n_trials} outside "
        "exploration band — primitive may have collapsed to greedy"
    )


# ---------- Test 3: determinism with the same seed ------------------------


def test_determinism_with_seed():
    """Same skills + same seed = same Choice list, every time."""
    task_emb = _unit(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    skills = [
        _make_skill(
            f"s{i}", trials=5 + i, successes=2 + i,
            learned_embedding=_unit(np.array(
                [0.7 + i * 0.05, 0.5, 0.0], dtype=np.float32,
            )).tolist(),
        )
        for i in range(5)
    ]

    out1 = consider_skills(skills, task_emb, rng=np.random.default_rng(1234))
    out2 = consider_skills(skills, task_emb, rng=np.random.default_rng(1234))

    assert [c.skill.id for c in out1] == [c.skill.id for c in out2]
    assert [round(c.score, 8) for c in out1] == [round(c.score, 8) for c in out2]


# ---------- Test 4: degenerate to top-k-cosine when evidence is huge ------


def test_degenerates_to_top_cosine_when_evidence_is_overwhelming():
    """Three skills, all with `trials=200, successes=180` → posterior
    is essentially Dirac at 0.90 ± a hair. With identical posteriors,
    score = relevance * theta ≈ relevance * 0.9. Ranking degenerates
    to top-k cosine.

    This guarantees backward compatibility with the existing
    `_retrieve_skills` behaviour when the library is mature.
    """
    task_emb = _unit(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    embs = [
        _unit(np.array([c, np.sqrt(1 - c**2), 0.0], dtype=np.float32))
        for c in (0.95, 0.85, 0.75)
    ]
    skills = [
        _make_skill(
            f"s{i}", trials=200, successes=180,
            learned_embedding=embs[i].tolist(),
        )
        for i in range(3)
    ]

    # Repeat 50 times — the most-cosine skill should win every time
    # (or near-every; posterior variance is tiny).
    rng = np.random.default_rng(99)
    wins_top = 0
    for _ in range(50):
        choices = consider_skills(skills, task_emb, rng=rng)
        if choices[0].skill.id == "s0":
            wins_top += 1
    assert wins_top >= 45, (
        f"top-cosine skill only won {wins_top}/50 in degenerate posterior — "
        "primitive isn't honouring the evidence floor"
    )


# ---------- Test 5: empty input ------------------------------------------


def test_empty_input_returns_empty():
    out = consider_skills([], _unit(np.ones(3, dtype=np.float32)))
    assert out == []


# ---------- Test 6: relevance dominates when posteriors equal -------------


def test_zero_relevance_skill_loses_even_with_high_fitness():
    """A skill that's orthogonal to the task should not be chosen,
    no matter how high its proven fitness. The Hippocampus doesn't
    activate engrams that don't match the cue."""
    task_emb = _unit(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    related = _unit(np.array([0.99, 0.14, 0.0], dtype=np.float32))
    orthogonal = _unit(np.array([0.0, 1.0, 0.0], dtype=np.float32))

    related_s = _make_skill(
        "related", trials=10, successes=5, learned_embedding=related.tolist(),
    )
    orthogonal_s = _make_skill(
        "orthogonal", trials=100, successes=99,
        learned_embedding=orthogonal.tolist(),
    )

    rng = np.random.default_rng(0)
    wins_related = 0
    n_trials = 100
    for _ in range(n_trials):
        out = consider_skills([related_s, orthogonal_s], task_emb, rng=rng)
        if out[0].skill.id == "related":
            wins_related += 1
    # Cosine ≈ 0.99 vs 0 is unbeatable.
    assert wins_related >= 0.95 * n_trials


# ---------- Test 7: shape of Choice records ------------------------------


def test_choice_records_carry_relevance_theta_and_score():
    """Choice is the observability hook — debug, dashboards, lineage
    tracking depend on these fields."""
    task_emb = _unit(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    skill_emb = _unit(np.array([0.8, 0.6, 0.0], dtype=np.float32))
    s = _make_skill(
        "x", trials=10, successes=7, learned_embedding=skill_emb.tolist(),
    )

    out = consider_skills([s], task_emb, rng=np.random.default_rng(0))
    assert len(out) == 1
    c = out[0]
    assert isinstance(c, Choice)
    assert c.skill.id == "x"
    assert 0.0 <= c.relevance <= 1.0
    assert 0.0 <= c.theta <= 1.0
    assert math.isclose(c.score, c.relevance * c.theta, rel_tol=1e-6)


# ---------- Test 8: select_top trivial slice -------------------------------


def test_select_top_returns_first_k_skills():
    task_emb = _unit(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    skills = [
        _make_skill(
            f"s{i}", trials=10, successes=8,
            learned_embedding=_unit(np.array(
                [0.9 - i * 0.1, 0.4, 0.0], dtype=np.float32,
            )).tolist(),
        )
        for i in range(5)
    ]
    choices = consider_skills(skills, task_emb, rng=np.random.default_rng(1))
    top2 = select_top(choices, k=2)
    assert len(top2) == 2
    assert top2[0].id == choices[0].skill.id
    assert top2[1].id == choices[1].skill.id


# ---------- Test 9: skills with no learned_embedding fall back via encoder -


def test_canonical_encoding_used_when_no_learned_embedding():
    """A skill that's never been used by Hebbian update has
    `learned_embedding = None`. The selector must NOT crash — it
    falls back to encoding the name+trigger via the supplied encoder.
    """
    task_emb = embedding.encode("read a configuration file")
    skills = [
        _make_skill("read_config"),  # learned_embedding=None
        _make_skill("write_config"),  # learned_embedding=None
    ]

    out = consider_skills(
        skills, task_emb,
        encoder=embedding.encode,
        rng=np.random.default_rng(0),
    )
    assert len(out) == 2
    # Both got a valid relevance, no crash.
    for c in out:
        assert 0.0 <= c.relevance <= 1.0


# ---------- Test 10: missing encoder + missing learned_embedding fails fast -


def test_missing_encoder_and_no_embedding_raises():
    """If a skill has no learned_embedding AND no encoder is provided,
    we MUST raise — silent zero-embedding bias is exactly the kind of
    'silent failure' the FORGIA forbids."""
    task_emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    s = _make_skill("nope")  # learned_embedding=None
    with pytest.raises(ValueError, match="encoder"):
        consider_skills([s], task_emb)
