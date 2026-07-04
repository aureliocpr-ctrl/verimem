"""FORGIA pezzo #169 — `EpisodicMemory.negative_bundle_candidates`.

Lateral inhibition (Földiák 1990): skill-pairs whose joint usage
predicts FAILURE more than success. The duale negativo del bundle
abstraction (#160). Returns ``[(a, b, count, fail_ratio), ...]``
(a < b) sorted by descending fail_ratio.

Heuristic: a pair (a,b) is a negative bundle iff
- count >= min_count (evidence)
- fail_ratio = failures / (failures+successes) >= min_fail_ratio
"""
from __future__ import annotations

import time
from pathlib import Path

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory


def _ep(eid: str, *, skills: list[str], outcome: str) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=list(skills),
        created_at=time.time(),
    )


def test_negative_bundle_empty_memory(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    assert mem.negative_bundle_candidates() == []


def test_negative_bundle_pure_failure(tmp_path: Path):
    """Pair appearing only in failures with min_count met."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    for i in range(4):
        mem.store(_ep(f"f{i}", skills=["A", "B"], outcome="failure"))
    res = mem.negative_bundle_candidates(min_count=3, min_fail_ratio=0.7)
    assert len(res) == 1
    a, b, count, ratio = res[0]
    assert (a, b) == ("A", "B")
    assert count == 4
    assert ratio == 1.0


def test_negative_bundle_mixed_outcomes(tmp_path: Path):
    """Pair appears in both success and failure; ratio above threshold."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # 4 failures, 1 success → ratio 0.80
    for i in range(4):
        mem.store(_ep(f"f{i}", skills=["A", "B"], outcome="failure"))
    mem.store(_ep("s1", skills=["A", "B"], outcome="success"))
    res = mem.negative_bundle_candidates(min_count=3, min_fail_ratio=0.7)
    assert len(res) == 1
    a, b, count, ratio = res[0]
    assert count == 5
    assert abs(ratio - 0.8) < 1e-9


def test_negative_bundle_below_ratio_filtered(tmp_path: Path):
    """Mixed but ratio below threshold → filtered out."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # 2 failures, 3 successes → ratio 0.40
    for i in range(2):
        mem.store(_ep(f"f{i}", skills=["A", "B"], outcome="failure"))
    for i in range(3):
        mem.store(_ep(f"s{i}", skills=["A", "B"], outcome="success"))
    assert mem.negative_bundle_candidates(
        min_count=3, min_fail_ratio=0.7,
    ) == []


def test_negative_bundle_sort_by_fail_ratio_desc(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # Pair (A,B) → 5/5 failures (ratio 1.0)
    for i in range(5):
        mem.store(_ep(f"ab{i}", skills=["A", "B"], outcome="failure"))
    # Pair (A,C) → 4/5 failures (ratio 0.80)
    for i in range(4):
        mem.store(_ep(f"acf{i}", skills=["A", "C"], outcome="failure"))
    mem.store(_ep("acs", skills=["A", "C"], outcome="success"))
    res = mem.negative_bundle_candidates(min_count=3, min_fail_ratio=0.7)
    assert [(t[0], t[1]) for t in res] == [("A", "B"), ("A", "C")]
    assert res[0][3] > res[1][3]
