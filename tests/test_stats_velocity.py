"""R44: Memory growth velocity — episodes/day, facts/day rolling rate."""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Item:
    id: str
    created_at: float = 0.0


def test_empty_returns_zero_velocity():
    from verimem.stats_velocity import compute_velocity
    out = compute_velocity(episodes=[], facts=[])
    assert out["episodes_per_day"] == 0.0
    assert out["facts_per_day"] == 0.0


def test_velocity_from_recent_items():
    from verimem.stats_velocity import compute_velocity
    now = time.time()
    eps = [_Item(f"e{i}", created_at=now - i * 86400) for i in range(7)]
    out = compute_velocity(episodes=eps, facts=[], window_days=7, now=now)
    # 7 episodes in 7 days = ~1 per day
    assert 0.5 < out["episodes_per_day"] < 2.0


def test_only_recent_window_counted():
    from verimem.stats_velocity import compute_velocity
    now = time.time()
    # 1 recent + 10 old
    eps = (
        [_Item("recent", created_at=now)]
        + [_Item(f"old{i}", created_at=now - 86400 * 365)
           for i in range(10)]
    )
    out = compute_velocity(episodes=eps, facts=[], window_days=7, now=now)
    # Only 1 in 7-day window
    assert out["episodes_per_day"] < 0.2  # ~1/7


def test_payload_keys():
    from verimem.stats_velocity import compute_velocity
    out = compute_velocity(episodes=[], facts=[])
    for k in ("episodes_per_day", "facts_per_day", "n_episodes_recent",
              "n_facts_recent", "window_days"):
        assert k in out


def test_window_days_respected():
    from verimem.stats_velocity import compute_velocity
    now = time.time()
    eps = [_Item(f"e{i}", created_at=now - i * 86400) for i in range(30)]
    out = compute_velocity(episodes=eps, facts=[], window_days=10, now=now)
    assert out["window_days"] == 10
    assert out["n_episodes_recent"] <= 11  # at most window+1 due to threshold


def test_zero_window_handled():
    from verimem.stats_velocity import compute_velocity
    now = time.time()
    eps = [_Item("e1", created_at=now)]
    out = compute_velocity(episodes=eps, facts=[], window_days=0.001, now=now)
    # Tiny window should still not crash
    assert out["episodes_per_day"] >= 0
