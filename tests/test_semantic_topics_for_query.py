"""FORGIA pezzo #180 — `SemanticMemory.topics_for_query(query, k)`.

Returns the topic distribution `{topic: weight}` over the top-K
facts most similar to `query`. Building block for schema-driven
skill priming (Preston & Eichenbaum 2013): the prefrontal cortex
pre-activates schemas before a task starts, biasing downstream
skill retrieval.
"""
from __future__ import annotations

from pathlib import Path

from verimem.semantic import Fact, SemanticMemory


def test_topics_for_query_empty(tmp_path: Path):
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    assert sem.topics_for_query("anything") == {}


def test_topics_for_query_returns_distribution(tmp_path: Path):
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    # Token-overlap with the query "network protocol handshake" must
    # be obvious so the bag-of-tokens stub embedder picks the right
    # facts deterministically.
    sem.store(Fact(proposition="network protocol handshake",
                    topic="networking", confidence=0.9))
    sem.store(Fact(proposition="network packet routing",
                    topic="networking", confidence=0.8))
    sem.store(Fact(proposition="bubble sort comparison",
                    topic="algorithms", confidence=0.9))
    topics = sem.topics_for_query("network protocol handshake", k=3)
    # All three facts considered; networking should dominate.
    assert "networking" in topics
    assert topics["networking"] > 0.0
    assert sum(topics.values()) > 0.0


def test_topics_for_query_normalised_weights_sum_to_one(tmp_path: Path):
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    sem.store(Fact(proposition="x", topic="t1", confidence=0.5))
    sem.store(Fact(proposition="y", topic="t2", confidence=0.5))
    topics = sem.topics_for_query("x y", k=2)
    s = sum(topics.values())
    # Allow tiny float slop.
    assert abs(s - 1.0) < 1e-6


def test_topics_for_query_respects_k(tmp_path: Path):
    """k=1 considers only the single most-similar fact."""
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    sem.store(Fact(proposition="cosine similarity measure", topic="math"))
    sem.store(Fact(proposition="latency budget", topic="systems"))
    sem.store(Fact(proposition="bubble sort algorithm", topic="algorithms"))
    topics = sem.topics_for_query("cosine similarity", k=1)
    # The closest fact is the cosine one; only `math` should appear.
    assert list(topics.keys()) == ["math"]
