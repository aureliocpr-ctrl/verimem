"""Cycle #84 — corpus_health_metrics tests (TDD strict RED).

Unified dashboard aggregator over the semantic store. One MCP call
that surfaces everything a user needs to assess the *health* of
their HippoAgent corpus:

  - totals: n_facts (live), n_superseded, n_chains
  - taxonomy: top_topics by count, n_facts_no_topic (pollution)
  - freshness: n_recent_24h, n_recent_7d, n_stale_30d
  - lineage: avg_chain_length, max_chain_length

Pure-local, no LLM, no embedding calls (just counts + walks).

Schema:

  corpus_health_metrics(semantic) -> {
    n_total, n_live, n_superseded,
    n_chains, avg_chain_length, max_chain_length,
    top_topics: [{topic, count}, ...],
    n_facts_no_topic,
    n_recent_24h, n_recent_7d, n_stale_30d,
  }
"""
from __future__ import annotations

import time

import pytest

from engram.semantic import Fact, SemanticMemory


@pytest.fixture
def mem(tmp_path):
    return SemanticMemory(db_path=tmp_path / "semantic.db")


@pytest.fixture
def diverse_corpus(mem):
    """Seed a deliberately diverse corpus:
      - 10 live facts in topic A
      -  5 live facts in topic B
      -  2 superseded facts (one chain A→B→C)
      -  1 fact with empty topic (pollution)
      -  3 facts older than 30 days
    """
    now = time.time()
    day = 86400.0
    for i in range(10):
        mem.store(Fact(
            id=f"a{i}", topic="lessons/topicA",
            proposition=f"fact a{i}", confidence=0.9,
            created_at=now - i * 0.5 * day,
        ))
    for i in range(5):
        mem.store(Fact(
            id=f"b{i}", topic="project/x/topicB",
            proposition=f"fact b{i}", confidence=0.9,
            created_at=now - i * 0.5 * day,
        ))
    # 1 fact no topic
    mem.store(Fact(
        id="nopic", topic="", proposition="orphan", confidence=0.5,
        created_at=now - 1 * day,
    ))
    # 3 old facts (40d > 30d)
    for i in range(3):
        mem.store(Fact(
            id=f"old{i}", topic=f"archive/o{i}",
            proposition=f"old {i}", confidence=0.7,
            created_at=now - 40 * day,
        ))
    # 2 supersession chain a→b→c
    mem.supersede("a0", "a1", reason="step 1")
    mem.supersede("a1", "a2", reason="step 2")
    return mem


# ---------------------------------------------------------------------------
# Totals
# ---------------------------------------------------------------------------

class TestTotals:
    def test_total_counts(self, diverse_corpus):
        from engram.corpus_health_metrics import corpus_health_metrics
        m = corpus_health_metrics(diverse_corpus)
        # 10 + 5 + 1 (no topic) + 3 old = 19 total
        assert m["n_total"] == 19
        # 2 superseded (a0, a1)
        assert m["n_superseded"] == 2
        # live = total - superseded
        assert m["n_live"] == 17


# ---------------------------------------------------------------------------
# Chains
# ---------------------------------------------------------------------------

class TestChains:
    def test_chain_count_and_lengths(self, diverse_corpus):
        from engram.corpus_health_metrics import corpus_health_metrics
        m = corpus_health_metrics(diverse_corpus)
        # Chains anchored at distinct anchor: a0 walks a0→a1→a2 (len=3).
        # No other chains.
        assert m["n_chains"] >= 1
        assert m["max_chain_length"] == 3
        # Average length: 1 chain of length 3
        assert 2.5 <= m["avg_chain_length"] <= 3.0


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------

class TestTaxonomy:
    def test_top_topics_ordered_by_count(self, diverse_corpus):
        from engram.corpus_health_metrics import corpus_health_metrics
        m = corpus_health_metrics(diverse_corpus)
        topics = m["top_topics"]
        # Top topic = lessons/topicA, but supersessions a0→a1→a2 hide 2
        # superseded facts → 10 raw - 2 superseded = 8 live.
        # project/x/topicB stays at 5 (no supersessions).
        assert topics[0]["topic"] == "lessons/topicA"
        assert topics[0]["count"] == 8
        assert topics[1]["topic"] == "project/x/topicB"
        assert topics[1]["count"] == 5

    def test_facts_without_topic_flagged(self, diverse_corpus):
        from engram.corpus_health_metrics import corpus_health_metrics
        m = corpus_health_metrics(diverse_corpus)
        # 1 fact with empty topic — pollution metric
        assert m["n_facts_no_topic"] == 1


# ---------------------------------------------------------------------------
# Freshness
# ---------------------------------------------------------------------------

class TestFreshness:
    def test_recent_buckets(self, diverse_corpus):
        from engram.corpus_health_metrics import corpus_health_metrics
        m = corpus_health_metrics(diverse_corpus)
        # 10 a-facts span 0→4.5 days (0,0.5,1.0,1.5,...,4.5)
        # 24h: a0+a1+a2 (0d,0.5d,1.0d) + b0+b1+b2 + nopic
        # Approx: just assert > 0 and < total to avoid clock flakiness
        assert m["n_recent_24h"] > 0
        assert m["n_recent_24h"] <= m["n_total"]
        assert m["n_recent_7d"] > 0
        # 3 old facts at 40d
        assert m["n_stale_30d"] >= 3


# ---------------------------------------------------------------------------
# Empty corpus
# ---------------------------------------------------------------------------

class TestEmpty:
    def test_empty_corpus_zero_safe(self, mem):
        from engram.corpus_health_metrics import corpus_health_metrics
        m = corpus_health_metrics(mem)
        assert m["n_total"] == 0
        assert m["n_live"] == 0
        assert m["n_superseded"] == 0
        assert m["n_chains"] == 0
        assert m["avg_chain_length"] == 0
        assert m["max_chain_length"] == 0
        assert m["top_topics"] == []
        assert m["n_facts_no_topic"] == 0
        assert m["n_recent_24h"] == 0
        assert m["n_recent_7d"] == 0
        assert m["n_stale_30d"] == 0


# ---------------------------------------------------------------------------
# Embedding consistency (guard post model-migration)
# ---------------------------------------------------------------------------

class TestEmbeddingConsistency:
    """Invariante: ogni fatto recall-eligible deve essere all'EMBEDDING MODEL
    attivo (stesso modello + stessa dim/byte-length). Un fatto eligible a un
    modello/dim vecchi e' SILENZIOSAMENTE escluso dal recall (model-gate +
    byte-filter) — il fallimento che una migrazione incompleta produce. La
    metrica lo rende visibile: n_embedding_dark > 0 = corpus inconsistente."""

    def test_empty_corpus_consistency_is_zero(self, mem):
        from engram.corpus_health_metrics import corpus_health_metrics
        m = corpus_health_metrics(mem)
        assert m["n_recall_eligible"] == 0
        assert m["n_embedding_dark"] == 0
        assert m["active_embedding_model"]  # non vuoto

    def test_counts_dark_eligible_not_superseded(self, mem):
        import sqlite3

        from engram import embedding
        from engram.corpus_health_metrics import corpus_health_metrics
        active = embedding.model_signature()
        # 2 fatti sani: mem.store encoda al modello ATTIVO + tagga embedding_model
        mem.store(Fact(id="ok1", topic="t", proposition="fatto sano uno",
                       confidence=0.9, status="model_claim"))
        mem.store(Fact(id="ok2", topic="t", proposition="fatto sano due",
                       confidence=0.9, status="model_claim"))
        now = time.time()
        with sqlite3.connect(mem.db_path) as c:
            # recall-eligible MA modello vecchio + dim sbagliata -> BUIO (conta)
            c.execute(
                "INSERT INTO facts (id, proposition, topic, confidence,"
                " source_episodes, created_at, embedding, status, embedding_model)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                ("dark1", "fatto buio col modello vecchio", "t", 0.8, "", now,
                 b"\x00" * 16, "model_claim", "old/model-384"),
            )
            # superseded: il recall lo esclude comunque -> NON conta come buio
            c.execute(
                "INSERT INTO facts (id, proposition, topic, confidence,"
                " source_episodes, created_at, embedding, status, embedding_model,"
                " superseded_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
                ("darksup", "buio ma superseded", "t", 0.8, "", now,
                 b"\x00" * 16, "model_claim", "old/model-384", "dark1"),
            )
        m = corpus_health_metrics(mem)
        assert m["active_embedding_model"] == active
        assert m["n_embedding_dark"] == 1, m       # solo dark1 (non il superseded)
        assert m["n_recall_eligible"] == 3, m      # ok1, ok2, dark1


# ---------------------------------------------------------------------------
# Recallable vs quarantined (honest headline)
# ---------------------------------------------------------------------------

class TestRecallableVsQuarantined:
    """Headline onesto: di n_total, quanti il recall puo' DAVVERO restituire
    (n_recallable) e quanti sono trattenuti come quarantined (claim non
    verificati)? Sul corpus live il '44% quarantined' deve leggersi 'rumore
    tenuto fuori dal recall', NON 'conoscenza pronta'. Senza questo split,
    n_live=n_total-superseded inganna (conta anche i quarantinati)."""

    def test_quarantined_and_recallable_split(self, mem):
        from engram.corpus_health_metrics import corpus_health_metrics
        # 3 sani recallable (modello attivo, model_claim)
        for i in range(3):
            mem.store(Fact(id=f"ok{i}", topic="t", proposition=f"sano {i}",
                           confidence=0.9, status="model_claim"))
        # 2 quarantinati (non verificati, esclusi dal recall)
        for i in range(2):
            mem.store(Fact(id=f"q{i}", topic="t", proposition=f"quarantena {i}",
                           confidence=0.5, status="quarantined"))
        m = corpus_health_metrics(mem)
        assert m["n_total"] == 5
        assert m["n_quarantined"] == 2
        # recallable = eligible AND embedded@active = solo i 3 sani
        assert m["n_recallable"] == 3
        # invariante: recallable non supera mai eligible
        assert m["n_recallable"] <= m["n_recall_eligible"]

    def test_empty_corpus_recallable_quarantined_zero(self, mem):
        from engram.corpus_health_metrics import corpus_health_metrics
        m = corpus_health_metrics(mem)
        assert m["n_quarantined"] == 0
        assert m["n_recallable"] == 0
