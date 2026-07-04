"""FORGIA pezzo #160 — `EpisodicMemory.skill_bundle_candidates(...)`.

Returns the list of skill-pair tuples ``(a, b, count)`` whose
co-occurrence count and relative overlap exceed the given thresholds.
Pairs are deduplicated (a, b) with ``a < b`` lexicographically and
sorted by descending count.
"""
from __future__ import annotations

import time
from pathlib import Path

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory


def _ep(eid: str, *, skills: list[str]) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome="success",
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=list(skills),
        created_at=time.time(),
    )


def test_skill_bundle_candidates_empty(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    assert mem.skill_bundle_candidates() == []


def test_skill_bundle_candidates_threshold_count(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # A∩B appears twice — below default min_count=3
    mem.store(_ep("e1", skills=["A", "B"]))
    mem.store(_ep("e2", skills=["A", "B"]))
    assert mem.skill_bundle_candidates(min_count=3) == []
    # Lower threshold pulls them in
    res = mem.skill_bundle_candidates(min_count=2, min_overlap=0.0)
    assert res == [("A", "B", 2)]


def test_skill_bundle_candidates_overlap_filter(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # A used 10×, B used 10×, A∩B = 3 → overlap = 3/10 = 0.30
    for i in range(7):
        mem.store(_ep(f"a{i}", skills=["A"]))
    for i in range(7):
        mem.store(_ep(f"b{i}", skills=["B"]))
    for i in range(3):
        mem.store(_ep(f"ab{i}", skills=["A", "B"]))
    # threshold 0.6 should reject (overlap=0.30)
    assert mem.skill_bundle_candidates(
        min_count=2, min_overlap=0.6,
    ) == []
    # threshold 0.2 should accept
    res = mem.skill_bundle_candidates(min_count=2, min_overlap=0.2)
    assert res == [("A", "B", 3)]


def test_skill_bundle_candidates_dedup_and_sort(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # (A,B) appears 3×, (A,C) appears 5× — both pass thresholds
    for i in range(3):
        mem.store(_ep(f"ab{i}", skills=["A", "B"]))
    for i in range(5):
        mem.store(_ep(f"ac{i}", skills=["A", "C"]))
    res = mem.skill_bundle_candidates(min_count=2, min_overlap=0.0)
    # sorted by count desc; tuple ordering canonical (a < b)
    assert res == [("A", "C", 5), ("A", "B", 3)]
    # No duplicate (B, A)
    seen = {(a, b) for (a, b, _) in res}
    assert ("B", "A") not in seen
