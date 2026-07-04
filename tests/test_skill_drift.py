"""R29: Skill drift detection — skill behaving differently than past.

For each skill, compare success_rate in recent_window vs historical.
Drift = |recent_rate - historical_rate| > threshold.

Use case: alert when a previously-reliable skill starts failing
(e.g. CVE got patched), or when a candidate suddenly clicks.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class _Ep:
    id: str
    outcome: str
    skills_used: list[str] = field(default_factory=list)
    created_at: float = 0.0


def test_empty_no_drift():
    from engram.skill_drift import detect_skill_drift
    out = detect_skill_drift([])
    assert out["drifts"] == []


def test_skill_with_drop_in_success():
    from engram.skill_drift import detect_skill_drift
    now = time.time()
    # Historical: 5 success
    hist = [_Ep(f"h{i}", "success", ["s1"], created_at=now - 86400 * 60)
            for i in range(5)]
    # Recent: 5 failure
    recent = [_Ep(f"r{i}", "failure", ["s1"], created_at=now - 86400 * 3)
              for i in range(5)]
    out = detect_skill_drift(
        hist + recent, now=now, recent_window_days=14,
        history_window_days=120, min_uses=3,
    )
    drift_ids = [d["skill_id"] for d in out["drifts"]]
    assert "s1" in drift_ids


def test_stable_skill_no_drift():
    from engram.skill_drift import detect_skill_drift
    now = time.time()
    eps = (
        [_Ep(f"o{i}", "success", ["stable"], created_at=now - 86400 * 60)
         for i in range(5)]
        + [_Ep(f"n{i}", "success", ["stable"], created_at=now - 86400 * 3)
           for i in range(5)]
    )
    out = detect_skill_drift(eps, now=now, recent_window_days=14,
                              history_window_days=120, min_uses=3)
    # Both windows 100% success → no drift
    assert "stable" not in [d["skill_id"] for d in out["drifts"]]


def test_drift_direction_field():
    from engram.skill_drift import detect_skill_drift
    now = time.time()
    hist = [_Ep(f"h{i}", "success", ["s1"], created_at=now - 86400 * 60)
            for i in range(5)]
    recent = [_Ep(f"r{i}", "failure", ["s1"], created_at=now - 86400 * 3)
              for i in range(5)]
    out = detect_skill_drift(
        hist + recent, now=now, recent_window_days=14,
        history_window_days=120, min_uses=3,
    )
    if out["drifts"]:
        d = out["drifts"][0]
        assert d["direction"] in {"improving", "degrading"}
        # Drop in success → degrading
        assert d["direction"] == "degrading"


def test_payload_shape():
    from engram.skill_drift import detect_skill_drift
    out = detect_skill_drift([])
    for k in ("drifts", "n_episodes_scanned"):
        assert k in out


def test_drift_entry_keys():
    from engram.skill_drift import detect_skill_drift
    now = time.time()
    hist = [_Ep(f"h{i}", "success", ["s1"], created_at=now - 86400 * 60)
            for i in range(5)]
    recent = [_Ep(f"r{i}", "failure", ["s1"], created_at=now - 86400 * 3)
              for i in range(5)]
    out = detect_skill_drift(
        hist + recent, now=now, recent_window_days=14,
        history_window_days=120, min_uses=3,
    )
    if out["drifts"]:
        for k in ("skill_id", "historical_rate", "recent_rate",
                  "drift", "direction"):
            assert k in out["drifts"][0]
