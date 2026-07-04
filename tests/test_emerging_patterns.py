"""R21: Emerging patterns — task signatures rising in frequency.

Compare recent window vs historical baseline. Pattern emerges when
recent rate > historical rate * threshold.
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str = "success"
    created_at: float = 0.0


def test_empty_returns_empty():
    from engram.emerging_patterns import find_emerging_patterns
    out = find_emerging_patterns([])
    assert out["emerging"] == []


def test_pattern_rising_recent():
    from engram.emerging_patterns import find_emerging_patterns

    now = time.time()
    # 1 old WordPress, 5 recent WordPress → emerging
    eps = [
        _Ep("old1", "WordPress exploit", created_at=now - 86400 * 60),
    ]
    eps += [
        _Ep(f"new{i}", "WordPress exploit", created_at=now - 86400 * 3)
        for i in range(5)
    ]
    out = find_emerging_patterns(
        eps, now=now, recent_window_days=7, history_window_days=60,
        min_recent_count=2,
    )
    sigs = [p["signature"] for p in out["emerging"]]
    # WordPress signature should appear
    assert any("wordpress" in s.lower() or "exploit" in s.lower() for s in sigs)


def test_stable_pattern_not_emerging():
    from engram.emerging_patterns import find_emerging_patterns
    now = time.time()
    # Same rate in both windows
    eps = (
        [_Ep(f"old{i}", "exploit X", created_at=now - 86400 * 30)
         for i in range(5)]
        + [_Ep(f"new{i}", "exploit X", created_at=now - 86400 * 3)
           for i in range(5)]
    )
    out = find_emerging_patterns(
        eps, now=now, recent_window_days=7, history_window_days=60,
    )
    # Should not be marked as emerging (5/5 ratio = no rise)
    assert out["emerging"] == [] or all(
        p["growth_ratio"] < 2.0 for p in out["emerging"]
    )


def test_payload_keys():
    from engram.emerging_patterns import find_emerging_patterns
    out = find_emerging_patterns([])
    for k in ("emerging", "n_episodes_scanned", "recent_window_days"):
        assert k in out


def test_entry_keys():
    from engram.emerging_patterns import find_emerging_patterns
    now = time.time()
    eps = [
        _Ep(f"r{i}", "new attack", created_at=now - 86400 * 2)
        for i in range(5)
    ]
    out = find_emerging_patterns(eps, now=now, min_recent_count=2)
    if out["emerging"]:
        for k in ("signature", "recent_count", "historical_count",
                  "growth_ratio"):
            assert k in out["emerging"][0]


def test_min_recent_count_filter():
    from engram.emerging_patterns import find_emerging_patterns
    now = time.time()
    eps = [_Ep("solo", "rare task", created_at=now - 86400)]
    out = find_emerging_patterns(eps, now=now, min_recent_count=3)
    # 1 < 3 → no emerging
    assert out["emerging"] == []
