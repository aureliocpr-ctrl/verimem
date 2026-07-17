"""Tests for FORGIA pezzo #19: salience in sleep replay priority.

`compute_salience` (pezzo #6) caches a per-episode prediction-error
score (0..1) at store time. The sleep replay scoring was using a
binary `outcome=='failure'` flag and ignored this richer signal.

This pezzo wires `episode.salience_score` into `replay_priority` via
`CONFIG.sleep_replay_priority_salience`, default 0.0 (opt-in).

Four measurable invariants:

  1. WEIGHT 0 PRESERVES LEGACY: with weight=0.0, replay_priority
     returns exactly the legacy formula.

  2. WEIGHT > 0 BOOSTS HIGH-SALIENCE: with weight>0, an episode
     with high salience scores higher than one with low salience
     all else equal.

  3. SUCCESS WITH HIGH SALIENCE BEATS BANAL FAILURE: a "surprising
     success" can outrank a banal failure when the salience weight
     is high enough — generalising the binary failure flag.

  4. CONTINUOUS, NOT BINARY: salience contributes proportionally —
     differences of 0.1 in salience produce differences of 0.1 ×
     weight in priority.
"""
from __future__ import annotations

import time

import pytest

from verimem.config import CONFIG
from verimem.episode import Episode, Trace
from verimem.sleep import replay_priority

# Anchor a fixed "now" so floats line up across episodes built at
# different microsecond offsets within the same test.
_NOW = 1_700_000_000.0


def _ep(*, ep_id: str, outcome: str = "success",
        salience: float = 0.5, age_hours: float = 0.0,
        skills_used: list[str] | None = None) -> Episode:
    return Episode(
        id=ep_id, task_id="t", task_text="x",
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="A",
                      action_input="", observation="o")],
        tokens_used=1,
        skills_used=skills_used or [],
        created_at=_NOW - age_hours * 3600.0,
        salience_score=salience,
    )


@pytest.fixture
def config_override():
    saved: dict = {}

    def setter(field: str, value) -> None:
        if field not in saved:
            saved[field] = getattr(CONFIG, field)
        object.__setattr__(CONFIG, field, value)

    yield setter
    for field, value in saved.items():
        object.__setattr__(CONFIG, field, value)


# ---------- Test 1: weight 0 = legacy ----------------------------------


def test_salience_weight_zero_preserves_legacy(config_override):
    """salience_weight=0 must give the same priority as not adding the
    salience term at all — bytes-for-bytes legacy."""
    config_override("sleep_replay_priority_salience", 0.0)
    config_override("sleep_replay_priority_surprise", 0.0)

    ep_a = _ep(ep_id="a", salience=0.0)
    ep_b = _ep(ep_id="b", salience=1.0)
    now = _NOW
    pa = replay_priority(ep_a, now, max_age=3600.0)
    pb = replay_priority(ep_b, now, max_age=3600.0)
    assert pa == pb, (
        f"with weight=0, salience must not influence priority: "
        f"a={pa}, b={pb}"
    )


# ---------- Test 2: weight > 0 boosts high salience -------------------


def test_salience_weight_boosts_high_salience(config_override):
    """With weight>0, high-salience episodes outrank low-salience ones."""
    config_override("sleep_replay_priority_salience", 0.5)
    config_override("sleep_replay_priority_surprise", 0.0)

    ep_low = _ep(ep_id="lo", salience=0.1)
    ep_high = _ep(ep_id="hi", salience=0.9)
    now = _NOW
    p_lo = replay_priority(ep_low, now, max_age=3600.0)
    p_hi = replay_priority(ep_high, now, max_age=3600.0)
    assert p_hi > p_lo, (
        f"high-salience should outrank low: lo={p_lo}, hi={p_hi}"
    )


# ---------- Test 3: surprising success beats banal failure ------------


def test_surprising_success_can_beat_banal_failure(config_override):
    """A success with very high salience can outrank a banal failure
    when the salience weight is large enough."""
    config_override("sleep_replay_priority_salience", 1.5)
    config_override("sleep_replay_priority_failure", 0.6)
    config_override("sleep_replay_priority_recent", 0.3)
    config_override("sleep_replay_priority_diverse", 0.1)
    config_override("sleep_replay_priority_surprise", 0.0)

    surprising_success = _ep(
        ep_id="ss", outcome="success", salience=1.0, age_hours=0.0,
    )
    banal_failure = _ep(
        ep_id="bf", outcome="failure", salience=0.05, age_hours=0.0,
    )
    now = _NOW
    p_ss = replay_priority(surprising_success, now, max_age=3600.0)
    p_bf = replay_priority(banal_failure, now, max_age=3600.0)
    assert p_ss > p_bf, (
        f"surprising success should beat banal failure: ss={p_ss}, bf={p_bf}"
    )


# ---------- Test 4: linearity of salience contribution ----------------


def test_salience_contribution_is_linear(config_override):
    """Doubling salience while keeping all else equal should add
    `weight × Δsalience` to the priority."""
    config_override("sleep_replay_priority_salience", 0.4)
    config_override("sleep_replay_priority_failure", 0.0)
    config_override("sleep_replay_priority_recent", 0.0)
    config_override("sleep_replay_priority_diverse", 0.0)
    config_override("sleep_replay_priority_surprise", 0.0)

    ep_a = _ep(ep_id="a", salience=0.2)
    ep_b = _ep(ep_id="b", salience=0.5)
    now = _NOW
    pa = replay_priority(ep_a, now, max_age=3600.0)
    pb = replay_priority(ep_b, now, max_age=3600.0)
    # Other weights are 0; only salience contributes.
    expected_diff = 0.4 * (0.5 - 0.2)
    assert abs((pb - pa) - expected_diff) < 1e-6, (
        f"non-linear salience: pb-pa={pb-pa:.4f}, expected={expected_diff:.4f}"
    )
