"""Audit#2 2026-06-08 A-6: consolidation._persist_master committed the master
Episode (mem.store) BEFORE the unique-index-guarded master Fact (sm.store). On a
cross-process consolidation race the loser's sm.store(f) raises IntegrityError
(caught upstream) but the Episode is already committed -> orphan episode with no
referencing master fact, accumulating under parallel auto-consolidate. Fix:
store the guarded Fact FIRST so a lost race aborts before any Episode is written
(f references ep.id, a soft cross-DB id, so fact-first is safe).
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem import consolidation


class _FakeMem:
    def __init__(self):
        self.stored = []

    def store(self, ep):
        self.stored.append(ep)


class _FakeSmConflict:
    """Simulates losing the unique-index race on the master fact."""

    def store(self, f):
        raise sqlite3.IntegrityError("UNIQUE constraint failed: idx_facts_auto_master_unique")


def test_persist_master_no_orphan_episode_on_fact_conflict():
    mem = _FakeMem()
    cluster = {"topic": "proj/x", "topic_prefix": "proj/x",
               "fact_count": 2, "fact_ids": ["a", "b"]}
    master = {"topic": "proj/x", "proposition": "the consolidated master claim"}
    with pytest.raises(sqlite3.IntegrityError):
        consolidation._persist_master(_FakeSmConflict(), mem, cluster, master)
    assert mem.stored == [], "orphan episode committed before the fact conflict aborted"
