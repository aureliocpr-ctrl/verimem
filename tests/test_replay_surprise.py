"""Tests for the surprise term added to replay_priority.

Property under test: when two episodes are otherwise comparable
(same outcome, same age, same skills_used count), the one whose
num_steps deviates more from the skill's typical step count gets a
HIGHER replay priority — only when the surprise weight is on.

By default (surprise weight 0) the function behaves exactly as before.
"""
from __future__ import annotations

import time
from dataclasses import replace

import pytest

from engram import sleep as sleep_mod
from engram.config import CONFIG
from engram.episode import Episode, Trace
from engram.sleep import compute_skill_avg_steps, replay_priority


def _ep(*, skill: str, n_steps: int, age_s: float = 0.0,
        outcome: str = "success") -> Episode:
    """Tiny factory; all episodes use a single skill so the surprise term
    has a clean reference."""
    traces = [
        Trace(step=i, thought="t", action="a", action_input="ai", observation="o")
        for i in range(1, n_steps + 1)
    ]
    return Episode(
        traces=traces, outcome=outcome,
        skills_used=[skill],
        created_at=time.time() - age_s,
    )


# ---------------------------------------------------------------------------
# Surprise OFF (default): the function behaves like before — exactly the
# same score regardless of skill_avg_steps.
# ---------------------------------------------------------------------------


def test_surprise_off_is_no_op(monkeypatch):
    monkeypatch.setattr(
        sleep_mod, "CONFIG",
        replace(CONFIG, sleep_replay_priority_surprise=0.0),
    )
    typical = _ep(skill="sk1", n_steps=3)
    anomalous = _ep(skill="sk1", n_steps=15)
    avg = {"sk1": 3.0}
    now = time.time()

    p_t_no_surp = replay_priority(typical, now, 1.0, skill_avg_steps=None)
    p_t_with_surp = replay_priority(typical, now, 1.0, skill_avg_steps=avg)
    p_a_no_surp = replay_priority(anomalous, now, 1.0, skill_avg_steps=None)
    p_a_with_surp = replay_priority(anomalous, now, 1.0, skill_avg_steps=avg)

    assert p_t_no_surp == p_t_with_surp
    assert p_a_no_surp == p_a_with_surp


# ---------------------------------------------------------------------------
# Surprise ON: the anomalous episode beats the typical one, all else equal.
# ---------------------------------------------------------------------------


def test_surprise_lifts_anomalous_episode(monkeypatch):
    monkeypatch.setattr(
        sleep_mod, "CONFIG",
        replace(CONFIG, sleep_replay_priority_surprise=0.4),
    )
    typical = _ep(skill="sk1", n_steps=3, age_s=10.0)
    anomalous = _ep(skill="sk1", n_steps=15, age_s=10.0)  # 5x average
    avg = {"sk1": 3.0}
    now = time.time()
    max_age = 100.0

    p_typical = replay_priority(typical, now, max_age, skill_avg_steps=avg)
    p_anomalous = replay_priority(anomalous, now, max_age, skill_avg_steps=avg)

    assert p_anomalous > p_typical, (
        f"anomalous {p_anomalous} should outrank typical {p_typical}"
    )


# ---------------------------------------------------------------------------
# Episodes whose skills haven't accumulated stats get surprise=0 (no
# false signal when we can't yet measure typical behaviour).
# ---------------------------------------------------------------------------


def test_unknown_skill_has_zero_surprise(monkeypatch):
    monkeypatch.setattr(
        sleep_mod, "CONFIG",
        replace(CONFIG, sleep_replay_priority_surprise=0.4),
    )
    ep = _ep(skill="sk_new", n_steps=99)
    # avg map empty for this skill — should fall back as if surprise off.
    # Pass the same `now` twice so the recency term doesn't drift between
    # calls (microsecond-scale time.time() differences leaked otherwise).
    fixed_now = time.time()
    p_with = replay_priority(ep, fixed_now, 1.0, skill_avg_steps={})
    p_without = replay_priority(ep, fixed_now, 1.0, skill_avg_steps=None)
    assert p_with == p_without


# ---------------------------------------------------------------------------
# An episode using multiple skills — pick the SMALLEST relative deviation
# (the right skill explains the trace).
# ---------------------------------------------------------------------------


def test_multiple_skills_uses_smallest_deviation(monkeypatch):
    monkeypatch.setattr(
        sleep_mod, "CONFIG",
        replace(CONFIG, sleep_replay_priority_surprise=0.4),
    )
    # 3-step episode: typical for sk_short (avg 3), anomalous for sk_long
    # (avg 30). The combined surprise should reflect sk_short (the right
    # skill), so this episode is *not* deemed surprising.
    ep = Episode(
        traces=[Trace(step=i, thought="", action="", action_input="",
                      observation="") for i in range(1, 4)],
        outcome="success",
        skills_used=["sk_short", "sk_long"],
        created_at=time.time(),
    )
    avg = {"sk_short": 3.0, "sk_long": 30.0}

    p_with = replay_priority(ep, time.time(), 1.0, skill_avg_steps=avg)
    p_without = replay_priority(ep, time.time(), 1.0, skill_avg_steps=None)
    # Difference must be tiny because relative deviation for sk_short = 0.
    assert abs(p_with - p_without) < 0.05


# ---------------------------------------------------------------------------
# compute_skill_avg_steps — reads episodes once, returns the mean.
# ---------------------------------------------------------------------------


def test_compute_skill_avg_steps(tmp_data_dir):
    from engram.memory import EpisodicMemory
    mem = EpisodicMemory(db_path=tmp_data_dir / "ep.db")
    for n in (2, 4, 6):  # mean = 4
        mem.store(_ep(skill="sk1", n_steps=n))
    mem.store(_ep(skill="sk2", n_steps=10))
    out = compute_skill_avg_steps(mem, {"sk1", "sk2", "sk_unseen"})
    assert out["sk1"] == pytest.approx(4.0)
    assert out["sk2"] == pytest.approx(10.0)
    assert out["sk_unseen"] == 0.0  # no episodes recorded
