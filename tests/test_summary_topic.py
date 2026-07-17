"""Cycle #79 — hippo_summary_topic aggregator narrativo (TDD strict RED).

P4 + P6 fix from cycle 2026-05-16 stress-test (fact 17eeb807d2d6):

  P4: lineage non auto-expand on topic query (needs explicit
      hippo_lineage_trace).
  P6: scala 268 ep + 800 fact impossibile gestione manuale; serve
      aggregator narrativo per topic glob.

API design:

  summary_topic(topic_glob: str, *, max_facts=50, include_lineage=True,
                include_superseded=False)
                -> {
                    "topic_glob": "...",
                    "n_total": int,
                    "n_live": int,
                    "n_superseded": int,
                    "topics_seen": list[str],
                    "facts": list[dict],  # newest-first, capped
                    "lineage_episodes": list[str],  # union source_episodes
                    "supersession_chains": list[list[str]],  # per chain head
                  }

Glob → SQL LIKE conversion:
  - ``*`` → ``%`` (multi-char wildcard)
  - ``?`` → ``_`` (single-char wildcard)
  - exact match when no wildcard char present

Defaults:
  - ``include_lineage=True``: union source_episodes from all matched facts
  - ``include_superseded=False``: align with retrieval defaults from
    cycle #78
  - ``max_facts=50``: caps the returned ``facts`` payload (counts stay
    accurate via n_total/n_live)
"""
from __future__ import annotations

import time

import pytest

from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def mem(tmp_path):
    return SemanticMemory(db_path=tmp_path / "semantic.db")


@pytest.fixture
def populated(mem):
    """Seed: 3 fact in project/x/A, 2 in project/x/B, 1 in project/y/C."""
    base_ts = time.time()
    facts = [
        Fact(id="x_a_1", topic="project/x/A",
             proposition="alpha 1", confidence=0.9,
             source_episodes=["ep_1", "ep_2"], created_at=base_ts + 1),
        Fact(id="x_a_2", topic="project/x/A",
             proposition="alpha 2", confidence=0.8,
             source_episodes=["ep_2"], created_at=base_ts + 2),
        Fact(id="x_a_3", topic="project/x/A",
             proposition="alpha 3 latest", confidence=0.95,
             source_episodes=["ep_3"], created_at=base_ts + 3),
        Fact(id="x_b_1", topic="project/x/B",
             proposition="beta 1", confidence=0.7,
             source_episodes=["ep_1"], created_at=base_ts + 4),
        Fact(id="x_b_2", topic="project/x/B",
             proposition="beta 2", confidence=0.85,
             source_episodes=["ep_4", "ep_5"], created_at=base_ts + 5),
        Fact(id="y_c_1", topic="project/y/C",
             proposition="gamma 1", confidence=0.6,
             source_episodes=["ep_6"], created_at=base_ts + 6),
    ]
    for f in facts:
        mem.store(f)
    return mem


# ---------------------------------------------------------------------------
# Glob matching
# ---------------------------------------------------------------------------

class TestGlobMatch:
    def test_wildcard_subtree(self, populated):
        result = populated.summary_topic("project/x/*")
        assert result["n_total"] == 5
        assert result["n_live"] == 5
        assert result["n_superseded"] == 0
        topics = set(result["topics_seen"])
        assert topics == {"project/x/A", "project/x/B"}

    def test_exact_match_no_wildcard(self, populated):
        result = populated.summary_topic("project/y/C")
        assert result["n_total"] == 1
        assert result["topics_seen"] == ["project/y/C"]
        assert result["facts"][0]["id"] == "y_c_1"

    def test_global_wildcard_matches_all(self, populated):
        result = populated.summary_topic("project/*")
        assert result["n_total"] == 6
        assert set(result["topics_seen"]) == {
            "project/x/A", "project/x/B", "project/y/C",
        }

    def test_empty_when_no_match(self, populated):
        result = populated.summary_topic("doesnotexist/*")
        assert result["n_total"] == 0
        assert result["n_live"] == 0
        assert result["facts"] == []
        assert result["topics_seen"] == []
        assert result["lineage_episodes"] == []


# ---------------------------------------------------------------------------
# Facts payload
# ---------------------------------------------------------------------------

class TestFactsPayload:
    def test_facts_newest_first(self, populated):
        result = populated.summary_topic("project/x/A")
        ids = [f["id"] for f in result["facts"]]
        # x_a_3 has highest created_at, x_a_1 lowest
        assert ids == ["x_a_3", "x_a_2", "x_a_1"]

    def test_max_facts_cap(self, populated):
        result = populated.summary_topic("project/*", max_facts=2)
        assert len(result["facts"]) == 2
        # Counts stay accurate even when cap kicks in
        assert result["n_total"] == 6
        assert result["n_live"] == 6

    def test_facts_carry_essentials(self, populated):
        result = populated.summary_topic("project/x/A", max_facts=1)
        f = result["facts"][0]
        for key in (
            "id", "topic", "proposition", "confidence", "created_at",
            "source_episodes", "superseded_by",
        ):
            assert key in f, f"missing key {key!r}"
        assert f["topic"] == "project/x/A"


# ---------------------------------------------------------------------------
# Lineage episodes (union)
# ---------------------------------------------------------------------------

class TestLineageEpisodes:
    def test_union_episodes_default(self, populated):
        result = populated.summary_topic("project/x/*")
        # x_a_1 → [ep_1, ep_2]; x_a_2 → [ep_2]; x_a_3 → [ep_3];
        # x_b_1 → [ep_1]; x_b_2 → [ep_4, ep_5].
        # Union = {ep_1, ep_2, ep_3, ep_4, ep_5}.
        assert set(result["lineage_episodes"]) == {
            "ep_1", "ep_2", "ep_3", "ep_4", "ep_5",
        }

    def test_lineage_disabled_returns_empty(self, populated):
        result = populated.summary_topic(
            "project/x/*", include_lineage=False,
        )
        assert result["lineage_episodes"] == []


# ---------------------------------------------------------------------------
# Supersession chains
# ---------------------------------------------------------------------------

class TestSupersessionChains:
    def test_excludes_superseded_by_default(self, populated):
        populated.supersede("x_a_1", "x_a_3", reason="x_a_3 obsoletes x_a_1")
        result = populated.summary_topic("project/x/A")
        assert result["n_total"] == 3   # raw count incl. superseded
        assert result["n_live"] == 2
        assert result["n_superseded"] == 1
        ids_in_facts = {f["id"] for f in result["facts"]}
        assert "x_a_1" not in ids_in_facts
        assert "x_a_3" in ids_in_facts

    def test_include_superseded_returns_all(self, populated):
        populated.supersede("x_a_1", "x_a_3", reason="X")
        result = populated.summary_topic(
            "project/x/A", include_superseded=True,
        )
        assert result["n_total"] == 3
        ids_in_facts = {f["id"] for f in result["facts"]}
        assert {"x_a_1", "x_a_2", "x_a_3"} <= ids_in_facts

    def test_chain_payload_a_to_b_to_c(self, populated):
        # x_a_1 -> x_a_2 -> x_a_3 (chain of 3)
        populated.supersede("x_a_1", "x_a_2", reason="step 1")
        populated.supersede("x_a_2", "x_a_3", reason="step 2")
        result = populated.summary_topic("project/x/A")
        chains = result["supersession_chains"]
        # Expect at least one chain anchored at x_a_1 leading to x_a_3
        flat = [c for c in chains if c and c[0] == "x_a_1"]
        assert flat, f"no chain anchored at x_a_1, got {chains}"
        assert flat[0][-1] == "x_a_3"
        assert len(flat[0]) == 3


# ---------------------------------------------------------------------------
# Glob edge cases
# ---------------------------------------------------------------------------

class TestGlobEscaping:
    def test_underscore_in_topic_does_not_match_question_mark(self, mem):
        """SQL LIKE has its own wildcards; the glob translation must
        only enable ``*`` and ``?`` characters and treat the rest as
        literal (escape LIKE-special chars `%` and `_` in user input)."""
        a = Fact(id="ax", topic="project_x", proposition="...", confidence=0.5)
        b = Fact(id="bx", topic="projectABx", proposition="...", confidence=0.5)
        mem.store(a)
        mem.store(b)
        # Literal "project_x" must match only ``ax``, NOT ``projectABx``.
        result = mem.summary_topic("project_x")
        ids = {f["id"] for f in result["facts"]}
        assert ids == {"ax"}
