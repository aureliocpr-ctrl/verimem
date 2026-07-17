"""Regression test per `SemanticMemory.list_facts` — cycle #10.

Bug originale: il metodo non esisteva, 28 chiamate `a.semantic.list_facts(...)`
in mcp_server.py fallivano silenziosamente (try/except: pass) → 28 MCP tool
ritornavano facts=[] vuoti.
"""
from __future__ import annotations

import time

import pytest

from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def sem(tmp_path):
    db = tmp_path / "sem.db"
    return SemanticMemory(db_path=db)


def _f(prop: str, topic: str = "x", created_at: float | None = None) -> Fact:
    return Fact(
        proposition=prop, topic=topic, confidence=0.8,
        source_episodes=[],
        created_at=created_at if created_at is not None else time.time(),
    )


def test_list_facts_method_exists_and_returns_list(sem):
    assert hasattr(sem, "list_facts")
    assert callable(sem.list_facts)
    result = sem.list_facts()
    assert isinstance(result, list)


def test_list_facts_returns_all_when_within_limit(sem):
    for i in range(5):
        sem.store(_f(f"prop {i}", created_at=float(i)))
    facts = sem.list_facts()
    assert len(facts) == 5


def test_list_facts_respects_limit(sem):
    for i in range(10):
        sem.store(_f(f"p {i}", created_at=float(i)))
    facts = sem.list_facts(limit=3)
    assert len(facts) == 3


def test_list_facts_respects_offset(sem):
    for i in range(5):
        sem.store(_f(f"prop {i}", created_at=float(i)))
    page1 = sem.list_facts(limit=2, offset=0)
    page2 = sem.list_facts(limit=2, offset=2)
    ids1 = {f.id for f in page1}
    ids2 = {f.id for f in page2}
    assert ids1.isdisjoint(ids2)
    assert len(page1) == 2
    assert len(page2) == 2


def test_list_facts_sorted_desc_by_created_at(sem):
    sem.store(_f("old", created_at=100.0))
    sem.store(_f("new", created_at=200.0))
    facts = sem.list_facts()
    assert facts[0].proposition == "new"
    assert facts[1].proposition == "old"


def test_list_facts_topic_filter(sem):
    sem.store(_f("a", topic="t1"))
    sem.store(_f("b", topic="t2"))
    sem.store(_f("c", topic="t1"))
    t1_facts = sem.list_facts(topic="t1")
    assert len(t1_facts) == 2
    assert {f.topic for f in t1_facts} == {"t1"}


def test_list_facts_empty_db(sem):
    facts = sem.list_facts()
    assert facts == []


def test_list_facts_signature_matches_mcp_call_shape(sem):
    """mcp_server.py uses: a.semantic.list_facts(limit=10000, offset=0).
    Quel call-shape preciso DEVE funzionare."""
    sem.store(_f("x"))
    # Stesso chiamata del MCP handler
    facts = sem.list_facts(limit=10000, offset=0)
    assert len(facts) == 1
