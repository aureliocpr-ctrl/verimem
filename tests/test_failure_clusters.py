"""R38: Cluster failed episodes by task signature.

Focus only on failures: which families are we stuck on?
Output sorted by cluster size descending.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str
    final_answer: str = ""


def test_empty_returns_empty():
    from engram.failure_clusters import cluster_failures
    out = cluster_failures([])
    assert out["clusters"] == []


def test_success_excluded():
    from engram.failure_clusters import cluster_failures
    eps = [
        _Ep("s1", "WordPress RCE", "success"),
        _Ep("s2", "WordPress RCE", "success"),
    ]
    out = cluster_failures(eps)
    assert out["clusters"] == []


def test_failure_clusters():
    from engram.failure_clusters import cluster_failures
    eps = [
        _Ep(f"f{i}", "WordPress nmap", "failure") for i in range(5)
    ] + [
        _Ep(f"x{i}", "WordPress nmap", "success") for i in range(3)
    ]
    out = cluster_failures(eps, min_cluster_size=3)
    assert len(out["clusters"]) >= 1
    assert out["clusters"][0]["n_failures"] == 5


def test_min_cluster_size_filter():
    from engram.failure_clusters import cluster_failures
    eps = [_Ep(f"f{i}", "small failure", "failure") for i in range(2)]
    out = cluster_failures(eps, min_cluster_size=5)
    assert out["clusters"] == []


def test_payload_shape():
    from engram.failure_clusters import cluster_failures
    out = cluster_failures([])
    for k in ("clusters", "n_failures_scanned"):
        assert k in out


def test_cluster_keys():
    from engram.failure_clusters import cluster_failures
    eps = [_Ep(f"f{i}", "X", "failure") for i in range(3)]
    out = cluster_failures(eps, min_cluster_size=2)
    if out["clusters"]:
        for k in ("signature", "n_failures", "episode_ids",
                  "common_error_tokens"):
            assert k in out["clusters"][0]
