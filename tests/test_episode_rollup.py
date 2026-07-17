"""R13: Episode rollup — compress old episodes into family summaries.

When the episode log grows large, take episodes older than threshold,
cluster by task signature, and produce 1 rollup summary per cluster.

Future use: the rollup can be re-injected into semantic facts ("we
ran X 12 times in 2024, 80% success rate") → cheap to recall.
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str
    tokens_used: int = 0
    created_at: float = 0.0


def test_empty_returns_empty():
    from verimem.episode_rollup import rollup_old_episodes
    out = rollup_old_episodes([])
    assert out["rollups"] == []
    assert out["n_episodes_rolled"] == 0


def test_recent_episodes_not_rolled():
    from verimem.episode_rollup import rollup_old_episodes
    now = time.time()
    eps = [
        _Ep(f"e{i}", "WordPress RCE", "success",
            created_at=now - 86400)  # 1 day ago
        for i in range(10)
    ]
    out = rollup_old_episodes(eps, now=now, older_than_days=30)
    # All too recent → no rollup
    assert out["rollups"] == []


def test_old_cluster_rolled():
    from verimem.episode_rollup import rollup_old_episodes
    now = time.time()
    eps = [
        _Ep(f"e{i}", "WordPress RCE", "success",
            created_at=now - 86400 * 60)  # 60 days old
        for i in range(10)
    ]
    out = rollup_old_episodes(eps, now=now, older_than_days=30)
    assert len(out["rollups"]) == 1
    r = out["rollups"][0]
    assert r["n_episodes"] == 10
    assert r["n_success"] == 10


def test_rollup_counts_outcomes():
    from verimem.episode_rollup import rollup_old_episodes
    now = time.time()
    eps = (
        [_Ep(f"s{i}", "exploit X", "success",
             created_at=now - 86400 * 60) for i in range(7)]
        + [_Ep(f"f{i}", "exploit X", "failure",
               created_at=now - 86400 * 60) for i in range(3)]
    )
    out = rollup_old_episodes(eps, now=now, older_than_days=30)
    assert len(out["rollups"]) == 1
    r = out["rollups"][0]
    assert r["n_success"] == 7
    assert r["n_failure"] == 3


def test_min_cluster_size_filter():
    from verimem.episode_rollup import rollup_old_episodes
    now = time.time()
    eps = [
        _Ep("e1", "rare task", "success", created_at=now - 86400 * 60),
        _Ep("e2", "rare task", "success", created_at=now - 86400 * 60),
    ]
    out = rollup_old_episodes(
        eps, now=now, older_than_days=30, min_cluster_size=5,
    )
    # Too small → no rollup
    assert out["rollups"] == []


def test_rollup_includes_summary():
    from verimem.episode_rollup import rollup_old_episodes
    now = time.time()
    eps = [_Ep(f"e{i}", "exploit X", "success",
               created_at=now - 86400 * 60) for i in range(5)]
    out = rollup_old_episodes(eps, now=now, older_than_days=30)
    r = out["rollups"][0]
    assert "summary" in r
    assert "exploit" in r["summary"].lower() or "x" in r["summary"].lower()


def test_payload_shape():
    from verimem.episode_rollup import rollup_old_episodes
    out = rollup_old_episodes([])
    for k in ("rollups", "n_episodes_rolled", "n_clusters"):
        assert k in out
