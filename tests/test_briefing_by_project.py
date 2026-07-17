"""Cycle #80 — hippo_briefing_by_project tests (TDD strict RED).

P1 fix from cycle 2026-05-16 stress-test (fact c019d5a21be6):
engram-proactive UserPromptSubmit hook uses cosine top-3 only —
too narrow when user mentions a SPECIFIC project (e.g. "nexus",
"beacon"). Need a tool that PULLS together:

  - hippo_summary_topic(f"project/{name}/*") for fact roll-up
  - recent episodes whose lineage touches those facts
  - top supersession chains visible in the project

into a single dict + a narrative summary string suitable for the
proactive hook payload.

API design:

  briefing_by_project(project, *, max_facts=20, n_episodes=5)
    -> {
        project: str,
        topic_glob: str,                 # f"project/{project}/*"
        n_total: int, n_live: int, n_superseded: int,
        topics_seen: list[str],
        facts: list[dict],
        related_episodes: list[dict],    # newest-first, capped
        supersession_chains: list[list[str]],
        summary: str,                    # human-readable narrative
       }

Defaults:
  - max_facts=20 (more than summary_topic default 50 cap is overkill
    for a context-builder payload)
  - n_episodes=5 most-recent episodes whose id ∈ lineage_episodes

Resolves P1: the SessionStart cosine top-3 hook reaches at most
3 facts; this tool reaches every fact under the project's topic
subtree.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import pytest

from verimem.semantic import Fact, SemanticMemory


@dataclass
class _FakeEpisode:
    id: str = "ep-x"
    task_text: str = "demo"
    final_answer: str = "..."
    outcome: str = "success"
    created_at: float = field(default_factory=time.time)


class _FakeEpisodicMemory:
    def __init__(self):
        self._eps: dict[str, _FakeEpisode] = {}

    def get(self, eid: str) -> _FakeEpisode | None:
        return self._eps.get(eid)

    def all(self, limit: int | None = None):
        items = sorted(self._eps.values(), key=lambda e: -e.created_at)
        return items[:limit] if limit else items


@dataclass
class _Agent:
    semantic: SemanticMemory
    memory: _FakeEpisodicMemory


@pytest.fixture
def populated(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    em = _FakeEpisodicMemory()
    base = time.time()
    # 3 facts under project/nexus/L0-*
    sm.store(Fact(id="o1", topic="project/nexus/L0-inv",
                  proposition="NEXUS 33 subpackage", confidence=0.97,
                  source_episodes=["ep_nexus_1"], created_at=base + 1))
    sm.store(Fact(id="o2", topic="project/nexus/L1-mode",
                  proposition="20 MODE catalog", confidence=1.0,
                  source_episodes=["ep_nexus_1", "ep_nexus_2"],
                  created_at=base + 2))
    sm.store(Fact(id="o3", topic="project/nexus/L2-DEEP-1",
                  proposition="60+ fasi reali", confidence=1.0,
                  source_episodes=["ep_nexus_3"], created_at=base + 3))
    # 1 fact under project/beacon
    sm.store(Fact(id="d1", topic="project/beacon/L0",
                  proposition="Project Beacon v3 9256 LOC", confidence=0.98,
                  source_episodes=["ep_dom_1"], created_at=base + 4))
    # Episodes — 3 nexus-related + 1 beacon + 1 unrelated
    for eid, ts in [("ep_nexus_1", base + 1.5),
                    ("ep_nexus_2", base + 2.5),
                    ("ep_nexus_3", base + 3.5),
                    ("ep_dom_1", base + 4.5),
                    ("ep_unrelated", base + 5.0)]:
        em._eps[eid] = _FakeEpisode(id=eid, created_at=ts)
    return _Agent(semantic=sm, memory=em)


# ---------------------------------------------------------------------------
# Basic
# ---------------------------------------------------------------------------

class TestBasic:
    def test_filters_to_project_topics(self, populated):
        from verimem.briefing_by_project import briefing_by_project
        r = briefing_by_project(populated, project="nexus")
        assert r["project"] == "nexus"
        assert r["topic_glob"] == "project/nexus/*"
        assert r["n_total"] == 3
        assert r["n_live"] == 3
        ids = {f["id"] for f in r["facts"]}
        assert ids == {"o1", "o2", "o3"}
        # No beacon fact leaks
        assert "d1" not in ids

    def test_returns_distinct_topics_seen(self, populated):
        from verimem.briefing_by_project import briefing_by_project
        r = briefing_by_project(populated, project="nexus")
        assert set(r["topics_seen"]) == {
            "project/nexus/L0-inv",
            "project/nexus/L1-mode",
            "project/nexus/L2-DEEP-1",
        }


# ---------------------------------------------------------------------------
# Related episodes
# ---------------------------------------------------------------------------

class TestRelatedEpisodes:
    def test_includes_only_episodes_touched_by_project_facts(self, populated):
        from verimem.briefing_by_project import briefing_by_project
        r = briefing_by_project(populated, project="nexus")
        ep_ids = {ep["id"] for ep in r["related_episodes"]}
        # Lineage union of o1/o2/o3 = {ep_nexus_1, ep_nexus_2, ep_nexus_3}.
        assert ep_ids == {"ep_nexus_1", "ep_nexus_2", "ep_nexus_3"}
        assert "ep_dom_1" not in ep_ids
        assert "ep_unrelated" not in ep_ids

    def test_episodes_newest_first(self, populated):
        from verimem.briefing_by_project import briefing_by_project
        r = briefing_by_project(populated, project="nexus")
        eps = r["related_episodes"]
        assert [e["id"] for e in eps] == [
            "ep_nexus_3", "ep_nexus_2", "ep_nexus_1",
        ]

    def test_n_episodes_cap(self, populated):
        from verimem.briefing_by_project import briefing_by_project
        r = briefing_by_project(populated, project="nexus", n_episodes=2)
        assert len(r["related_episodes"]) == 2

    def test_no_facts_no_episodes(self, populated):
        from verimem.briefing_by_project import briefing_by_project
        r = briefing_by_project(populated, project="nonexistent")
        assert r["n_total"] == 0
        assert r["related_episodes"] == []


# ---------------------------------------------------------------------------
# Summary string
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_mentions_project_and_counts(self, populated):
        from verimem.briefing_by_project import briefing_by_project
        r = briefing_by_project(populated, project="nexus")
        s = r["summary"]
        assert isinstance(s, str) and len(s) > 0
        assert "nexus" in s.lower()
        assert "3" in s   # n_live = 3 facts

    def test_summary_for_empty_project_is_clear(self, populated):
        from verimem.briefing_by_project import briefing_by_project
        r = briefing_by_project(populated, project="nonexistent")
        s = r["summary"].lower()
        assert "nonexistent" in s
        assert "0" in s   # zero facts


# ---------------------------------------------------------------------------
# Supersession chains pass-through
# ---------------------------------------------------------------------------

class TestSupersession:
    def test_chains_surface_in_briefing(self, populated):
        from verimem.briefing_by_project import briefing_by_project
        # Create chain: o1 -> o3 (o3 supersedes o1)
        populated.semantic.supersede("o1", "o3", reason="L0 refined")
        r = briefing_by_project(populated, project="nexus")
        assert r["n_live"] == 2          # o1 hidden
        assert r["n_superseded"] == 1
        assert any(
            chain and chain[0] == "o1" and chain[-1] == "o3"
            for chain in r["supersession_chains"]
        )
