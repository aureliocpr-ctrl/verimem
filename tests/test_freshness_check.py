"""Cycle #82 — facts_freshness_check tests (TDD strict RED).

Use case (generalized from NEXUS BUG#1 kev-feed obsoleto):
Any topic-namespace accumulates measurements/claims over time.
Older facts can become stale silently. Manually inspecting 800
facts is unfeasible. We need an automated tool that surfaces:

  - "stale" facts: created_at older than threshold_days AND not
    explicitly superseded
  - "auto-supersede candidates": stale fact + newer fact in same
    topic-glob with cosine similarity >= sim_threshold

The newer fact is the natural replacement; the user reviews and
calls hippo_fact_supersede or supersede_chain to commit.

API:

  facts_freshness_check(topic_glob, *, threshold_days=30,
                         sim_threshold=0.85, max_results=50)
    -> {
        topic_glob,
        threshold_days,
        sim_threshold,
        n_scanned,                 # facts under glob (live only)
        n_stale,                   # older than threshold, no chain
        n_auto_supersede_candidates,
        stale: [
          {id, topic, created_at, age_days, proposition[:120]},
          ...
        ],
        candidates: [
          {old_id, new_id, similarity, old_age_days, ...},
          ...
        ],
       }
"""
from __future__ import annotations

import time

import pytest

from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def mem(tmp_path):
    return SemanticMemory(db_path=tmp_path / "semantic.db")


@pytest.fixture
def aged_corpus(mem):
    """3 old facts (60d), 2 fresh facts (5d) in project/x/*, with the
    fresh ones SEMANTICALLY CLOSE to the first 2 old ones (auto-
    supersede candidates)."""
    now = time.time()
    day = 86400.0
    facts = [
        # Old fact 1 — semantically close to fresh_1
        Fact(id="old_1", topic="project/x/detectors",
             proposition="NEXUS has 144 detectors as of cycle 20",
             confidence=0.8, created_at=now - 60 * day),
        # Old fact 2 — semantically close to fresh_2
        Fact(id="old_2", topic="project/x/loc",
             proposition="NEXUS has 225000 lines of code v6.3.0",
             confidence=0.8, created_at=now - 60 * day),
        # Old fact 3 — no fresh equivalent, just stale
        Fact(id="old_3", topic="project/x/misc",
             proposition="NEXUS was launched in March 2026 Termux",
             confidence=0.95, created_at=now - 60 * day),
        # Fresh fact 1 — close to old_1 (detector count)
        Fact(id="fresh_1", topic="project/x/detectors",
             proposition="NEXUS has 543 detectors verified ls wc",
             confidence=1.0, created_at=now - 5 * day),
        # Fresh fact 2 — close to old_2 (LOC count)
        Fact(id="fresh_2", topic="project/x/loc",
             proposition="NEXUS has 448000 lines of code current",
             confidence=1.0, created_at=now - 5 * day),
    ]
    for f in facts:
        mem.store(f)
    return mem


# ---------------------------------------------------------------------------
# Basic stale detection
# ---------------------------------------------------------------------------

class TestStaleDetection:
    def test_flags_facts_older_than_threshold(self, aged_corpus):
        from verimem.freshness_check import facts_freshness_check
        r = facts_freshness_check(
            aged_corpus, "project/x/*", threshold_days=30,
        )
        stale_ids = {s["id"] for s in r["stale"]}
        # 3 old facts (60d > 30d), 2 fresh (5d < 30d)
        assert stale_ids == {"old_1", "old_2", "old_3"}
        assert r["n_stale"] == 3
        assert r["n_scanned"] == 5

    def test_includes_age_days_in_stale_payload(self, aged_corpus):
        from verimem.freshness_check import facts_freshness_check
        r = facts_freshness_check(aged_corpus, "project/x/*")
        for s in r["stale"]:
            # Allow some clock slack — fixture sets age 60d
            assert 58.0 < s["age_days"] < 62.0

    def test_no_stale_when_threshold_high(self, aged_corpus):
        from verimem.freshness_check import facts_freshness_check
        r = facts_freshness_check(
            aged_corpus, "project/x/*", threshold_days=365,
        )
        assert r["n_stale"] == 0
        assert r["stale"] == []

    def test_already_superseded_facts_skip(self, aged_corpus):
        from verimem.freshness_check import facts_freshness_check
        # Manually supersede old_3 so it shouldn't appear as stale
        aged_corpus.supersede("old_3", "fresh_1", reason="manual chain")
        r = facts_freshness_check(
            aged_corpus, "project/x/*", threshold_days=30,
        )
        stale_ids = {s["id"] for s in r["stale"]}
        assert "old_3" not in stale_ids
        # Plus n_scanned uses LIVE count from summary_topic semantics
        assert r["n_scanned"] == 4
        # old_1 and old_2 still stale
        assert stale_ids == {"old_1", "old_2"}


# ---------------------------------------------------------------------------
# Auto-supersede candidate detection
# ---------------------------------------------------------------------------

class TestAutoSupersedeCandidates:
    def test_pairs_old_with_close_newer_fact(self, aged_corpus):
        from verimem.freshness_check import facts_freshness_check
        r = facts_freshness_check(
            aged_corpus, "project/x/*",
            threshold_days=30, sim_threshold=0.4,
            # Lower similarity threshold so fixture text passes
            # (real embeddings vary; 0.4 is safe for the topic pairs).
        )
        cand_pairs = {(c["old_id"], c["new_id"]) for c in r["candidates"]}
        # old_1 (detector count old) should pair with fresh_1 (newer
        # detector count). old_2 with fresh_2.
        assert ("old_1", "fresh_1") in cand_pairs
        assert ("old_2", "fresh_2") in cand_pairs
        # old_3 has no semantically-close fresh counterpart → no pair
        old_3_in = any(c["old_id"] == "old_3" for c in r["candidates"])
        assert not old_3_in

    def test_high_sim_threshold_yields_zero_candidates(self, aged_corpus):
        from verimem.freshness_check import facts_freshness_check
        r = facts_freshness_check(
            aged_corpus, "project/x/*",
            threshold_days=30, sim_threshold=0.999,
        )
        assert r["candidates"] == []
        assert r["n_auto_supersede_candidates"] == 0

    def test_each_old_paired_with_best_newer_only(self, aged_corpus):
        from verimem.freshness_check import facts_freshness_check
        r = facts_freshness_check(
            aged_corpus, "project/x/*", threshold_days=30, sim_threshold=0.2,
        )
        # Each old fact should appear AT MOST ONCE in candidates (best
        # newer match wins) — otherwise the supersede chain proposal
        # would be ambiguous.
        old_ids = [c["old_id"] for c in r["candidates"]]
        assert len(old_ids) == len(set(old_ids))

    def test_candidates_include_similarity_score(self, aged_corpus):
        from verimem.freshness_check import facts_freshness_check
        r = facts_freshness_check(
            aged_corpus, "project/x/*", threshold_days=30, sim_threshold=0.3,
        )
        for c in r["candidates"]:
            assert "similarity" in c
            assert 0.0 <= c["similarity"] <= 1.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_glob_returns_zero_everything(self, aged_corpus):
        from verimem.freshness_check import facts_freshness_check
        r = facts_freshness_check(
            aged_corpus, "nonexistent/*", threshold_days=30,
        )
        assert r["n_scanned"] == 0
        assert r["n_stale"] == 0
        assert r["stale"] == []
        assert r["candidates"] == []

    def test_max_results_caps_stale_list(self, aged_corpus):
        from verimem.freshness_check import facts_freshness_check
        r = facts_freshness_check(
            aged_corpus, "project/x/*",
            threshold_days=30, max_results=2,
        )
        assert len(r["stale"]) <= 2
        # Count remains accurate
        assert r["n_stale"] == 3
