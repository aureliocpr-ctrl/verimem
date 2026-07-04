"""Cycle #88 — dashboard_overview_v2 tests."""
from __future__ import annotations

import time

import pytest

from engram.semantic import Fact, SemanticMemory


@pytest.fixture
def populated(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "sm.db")
    now = time.time()
    day = 86400.0
    sm.store(Fact(id="a1", topic="project/nexus/L0",
                   proposition="a1 fact nexus", confidence=0.9,
                   created_at=now - 1 * day))
    sm.store(Fact(id="a2", topic="project/nexus/L0",
                   proposition="a2 fact nexus old", confidence=0.9,
                   created_at=now - 40 * day))
    sm.store(Fact(id="b1", topic="project/beacon/v3",
                   proposition="b1 fact beacon", confidence=0.9,
                   created_at=now - 5 * day))
    sm.store(Fact(id="orph", topic="",
                   proposition="nexus orphan related text",
                   confidence=0.5, created_at=now - 2 * day))
    return sm


def test_returns_three_sections(populated):
    from engram.dashboard_overview_v2 import dashboard_overview_v2
    r = dashboard_overview_v2(populated)
    assert "health" in r
    assert "orphan_suggestions" in r
    assert "freshness_by_project" in r


def test_health_consistent(populated):
    from engram.dashboard_overview_v2 import dashboard_overview_v2
    r = dashboard_overview_v2(populated)
    h = r["health"]
    assert h["n_total"] == 4
    assert h["n_facts_no_topic"] == 1


def test_orphan_suggestions_present(populated):
    from engram.dashboard_overview_v2 import dashboard_overview_v2
    r = dashboard_overview_v2(populated, orphan_sim_threshold=0.3)
    s = r["orphan_suggestions"]
    assert s["n_facts_no_topic"] == 1
    assert isinstance(s["suggestions"], list)


def test_freshness_per_project_glob(populated):
    from engram.dashboard_overview_v2 import dashboard_overview_v2
    r = dashboard_overview_v2(
        populated,
        project_globs=["project/nexus/*", "project/beacon/*"],
        freshness_threshold_days=10,
    )
    fbp = r["freshness_by_project"]
    assert "project/nexus/*" in fbp
    assert "project/beacon/*" in fbp
    assert fbp["project/nexus/*"]["n_stale"] >= 1


def test_empty_globs_safe(populated):
    from engram.dashboard_overview_v2 import dashboard_overview_v2
    r = dashboard_overview_v2(populated)
    assert r["freshness_by_project"] == {}
