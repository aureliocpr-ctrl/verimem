"""FORGIA pezzo #226 — Wave 25: episode clustering by task_text.

Group episodes by token-Jaccard on `task_text`. No embeddings —
pure string token overlap. Useful for:
  - "quali task ho già fatto?" (deduplicating obvious near-misses)
  - finding the cluster the current task belongs to
  - skill compilation: episodes in the same cluster are good
    candidates for a derived skill

Greedy single-link clustering: first unvisited episode seeds a
cluster, all unvisited episodes within Jaccard ≥ threshold join.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _FakeEp:
    id: str
    task_text: str = ""


def test_empty_returns_empty_clusters():
    from verimem.episode_clusters import cluster_episodes

    out = cluster_episodes([])
    assert out["clusters"] == []


def test_singletons_when_disjoint():
    from verimem.episode_clusters import cluster_episodes

    eps = [
        _FakeEp("e1", "alpha beta gamma"),
        _FakeEp("e2", "delta epsilon zeta"),
        _FakeEp("e3", "totally different words"),
    ]
    out = cluster_episodes(eps, threshold=0.5)
    # Each is its own singleton.
    assert len(out["clusters"]) == 3
    assert all(len(c["members"]) == 1 for c in out["clusters"])


def test_two_episodes_cluster_together():
    from verimem.episode_clusters import cluster_episodes

    eps = [
        _FakeEp("e1", "deploy web app"),
        _FakeEp("e2", "deploy web application"),  # high overlap
        _FakeEp("e3", "completely unrelated"),
    ]
    out = cluster_episodes(eps, threshold=0.4)
    # e1 and e2 share {deploy, web} = 2 of {deploy, web, app, application} = 4
    # → Jaccard 0.5; threshold 0.4 → cluster.
    cluster_sizes = sorted(len(c["members"]) for c in out["clusters"])
    assert cluster_sizes == [1, 2]


def test_threshold_strict_breaks_clusters():
    from verimem.episode_clusters import cluster_episodes

    eps = [
        _FakeEp("e1", "alpha beta"),
        _FakeEp("e2", "alpha gamma"),  # only 1 token shared
    ]
    out_strict = cluster_episodes(eps, threshold=0.9)
    # 1/3 = 0.33 << 0.9 → singletons.
    assert len(out_strict["clusters"]) == 2


def test_clusters_sorted_by_size_desc():
    from verimem.episode_clusters import cluster_episodes

    eps = [
        _FakeEp("a1", "apple banana"),
        _FakeEp("a2", "apple banana"),
        _FakeEp("a3", "apple banana"),
        _FakeEp("z1", "zebra ant"),
    ]
    out = cluster_episodes(eps, threshold=0.5)
    sizes = [len(c["members"]) for c in out["clusters"]]
    assert sizes == sorted(sizes, reverse=True)


def test_payload_per_cluster_complete():
    from verimem.episode_clusters import cluster_episodes

    eps = [_FakeEp("e1", "alpha beta")]
    out = cluster_episodes(eps)
    cluster = out["clusters"][0]
    assert "members" in cluster
    assert "size" in cluster
    assert cluster["size"] == 1


def test_top_k_clusters_respected():
    from verimem.episode_clusters import cluster_episodes

    eps = [_FakeEp(f"e{i}", f"unique{i}") for i in range(10)]
    out = cluster_episodes(eps, top_k=3)
    assert len(out["clusters"]) == 3


def test_payload_shape_complete():
    from verimem.episode_clusters import cluster_episodes

    out = cluster_episodes([])
    for k in ("clusters", "n_episodes", "threshold"):
        assert k in out
