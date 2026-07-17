"""R25: Memory compaction — dedup near-duplicate facts.

Pairwise compare facts. If jaccard(propA, propB) >= threshold,
they're considered duplicates — return clusters.

The caller can choose to keep one and prune the rest, or merge into
a consolidated fact.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = ""
    confidence: float = 0.9
    created_at: float = 0.0


def test_empty_returns_no_dupes():
    from verimem.memory_compaction import find_duplicates
    out = find_duplicates([])
    assert out["duplicate_clusters"] == []


def test_unique_facts_no_dupes():
    from verimem.memory_compaction import find_duplicates
    facts = [
        _Fact("f1", "WordPress is vulnerable"),
        _Fact("f2", "Linux kernel update available"),
        _Fact("f3", "Aurelio prefers TypeScript"),
    ]
    out = find_duplicates(facts, sim_threshold=0.8)
    assert out["duplicate_clusters"] == []


def test_duplicates_clustered():
    from verimem.memory_compaction import find_duplicates
    facts = [
        _Fact("f1", "WordPress 5.8 is vulnerable to CVE-X"),
        _Fact("f2", "WordPress 5.8 is vulnerable to CVE-X exploit"),
        _Fact("f3", "WordPress 5.8 vulnerable CVE-X"),
    ]
    out = find_duplicates(facts, sim_threshold=0.6)
    assert len(out["duplicate_clusters"]) >= 1
    cluster = out["duplicate_clusters"][0]
    assert cluster["n_dupes"] >= 2


def test_payload_shape():
    from verimem.memory_compaction import find_duplicates
    out = find_duplicates([])
    for k in ("duplicate_clusters", "n_facts_scanned", "n_duplicate_pairs"):
        assert k in out


def test_cluster_keys():
    from verimem.memory_compaction import find_duplicates
    facts = [
        _Fact("f1", "WordPress vulnerable CVE"),
        _Fact("f2", "WordPress CVE vulnerable"),
    ]
    out = find_duplicates(facts, sim_threshold=0.5)
    if out["duplicate_clusters"]:
        c = out["duplicate_clusters"][0]
        for k in ("representative_id", "fact_ids", "n_dupes",
                  "max_similarity"):
            assert k in c


def test_singleton_not_a_cluster():
    from verimem.memory_compaction import find_duplicates
    facts = [_Fact("solo", "unique fact alone")]
    out = find_duplicates(facts)
    # Singleton → not a duplicate
    assert out["duplicate_clusters"] == []
