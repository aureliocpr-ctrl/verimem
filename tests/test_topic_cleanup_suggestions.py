"""Cycle #85 — topic cleanup suggestions tests (TDD strict RED).

P5 fix from cycle 2026-05-16 stress-test (fact 17eeb807d2d6):
topic naming proliferation senza tassonomia controllata. Plus
empirical: corpus health metrics (cycle #84) shows 86/836 = 10.3%
of facts have empty topic. Bigger problem than realized.

API:

  topic_cleanup_suggestions(semantic, *, max_suggestions=20,
                              sim_threshold=0.6)
    -> {
         n_facts_no_topic,
         suggestions: [
           {fact_id, proposition[:120], suggested_topic,
            similarity, votes: int},
           ...
         ],
       }

Logic:

  For each fact whose topic is empty/None, find its nearest live-
  topic neighbours (cosine on embedding) under sim_threshold. The
  topic that appears most often among the top-k neighbours becomes
  the suggestion. If no neighbours are close enough, the fact is
  skipped (orphan).

Pure-local, no LLM.
"""
from __future__ import annotations

import pytest

from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def corpus_with_orphans(tmp_path):
    """Seed: 5 facts under 'cyber/nexus' + 3 facts under 'engram/ops'
    + 2 orphan facts (no topic). The orphans are SEMANTICALLY CLOSE
    to one of the two clusters."""
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    # Cluster 1: cyber/nexus
    cyber_props = [
        "NEXUS cybersec platform vulnerability detection",
        "NEXUS detector for SQL injection on web targets",
        "NEXUS hunter module nuclei integration",
        "NEXUS scans for XSS and CORS misconfigurations",
        "NEXUS bug bounty platform multi-provider AI",
    ]
    for i, p in enumerate(cyber_props):
        sm.store(Fact(id=f"c{i}", topic="cyber/nexus", proposition=p,
                      confidence=0.9))
    # Cluster 2: engram/ops
    engram_props = [
        "Engram supersede tool for obsolete facts in memory",
        "HippoAgent memory store SQLite with WAL pragma",
        "Engram facts recall with cosine embedding similarity",
    ]
    for i, p in enumerate(engram_props):
        sm.store(Fact(id=f"e{i}", topic="engram/ops", proposition=p,
                      confidence=0.9))
    # Orphans (no topic) — text close to one cluster each
    sm.store(Fact(id="orph_cyber",
                  proposition="NEXUS detector for path traversal CWE-22",
                  topic="", confidence=0.5))
    sm.store(Fact(id="orph_engram",
                  proposition="Engram facts deduplicate via cosine similarity threshold",
                  topic="", confidence=0.5))
    return sm


# ---------------------------------------------------------------------------
# Basic suggestions
# ---------------------------------------------------------------------------

class TestSuggestions:
    def test_suggests_cluster_topic_for_orphans(self, corpus_with_orphans):
        from verimem.topic_cleanup_suggestions import topic_cleanup_suggestions
        r = topic_cleanup_suggestions(corpus_with_orphans, sim_threshold=0.3)
        assert r["n_facts_no_topic"] == 2
        suggestions_by_id = {s["fact_id"]: s for s in r["suggestions"]}
        # orph_cyber should be assigned cyber/nexus (its text is NEXUS-related)
        assert "orph_cyber" in suggestions_by_id
        assert suggestions_by_id["orph_cyber"]["suggested_topic"] == "cyber/nexus"
        # orph_engram should be engram/ops
        assert "orph_engram" in suggestions_by_id
        assert suggestions_by_id["orph_engram"]["suggested_topic"] == "engram/ops"

    def test_high_sim_threshold_excludes_distant_orphans(self, corpus_with_orphans):
        from verimem.topic_cleanup_suggestions import topic_cleanup_suggestions
        r = topic_cleanup_suggestions(corpus_with_orphans, sim_threshold=0.999)
        # With such a high threshold, no neighbour is close enough
        assert r["suggestions"] == []

    def test_suggestion_carries_similarity_and_votes(self, corpus_with_orphans):
        from verimem.topic_cleanup_suggestions import topic_cleanup_suggestions
        r = topic_cleanup_suggestions(corpus_with_orphans, sim_threshold=0.3)
        for s in r["suggestions"]:
            assert "similarity" in s
            assert 0.0 <= s["similarity"] <= 1.0
            assert "votes" in s
            assert s["votes"] >= 1
            assert "proposition" in s


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_no_orphans_returns_empty(self, tmp_path):
        from verimem.topic_cleanup_suggestions import topic_cleanup_suggestions
        sm = SemanticMemory(db_path=tmp_path / "sm.db")
        sm.store(Fact(id="a", topic="x", proposition="..."))
        r = topic_cleanup_suggestions(sm)
        assert r["n_facts_no_topic"] == 0
        assert r["suggestions"] == []

    def test_no_live_topics_no_suggestions(self, tmp_path):
        from verimem.topic_cleanup_suggestions import topic_cleanup_suggestions
        sm = SemanticMemory(db_path=tmp_path / "sm.db")
        # All facts orphan — no topic vocabulary to vote on
        sm.store(Fact(id="o1", topic="", proposition="alpha"))
        sm.store(Fact(id="o2", topic="", proposition="beta"))
        r = topic_cleanup_suggestions(sm)
        assert r["n_facts_no_topic"] == 2
        assert r["suggestions"] == []

    def test_max_suggestions_cap(self, corpus_with_orphans):
        from verimem.topic_cleanup_suggestions import topic_cleanup_suggestions
        r = topic_cleanup_suggestions(
            corpus_with_orphans, sim_threshold=0.3, max_suggestions=1,
        )
        assert len(r["suggestions"]) <= 1
