"""Test offline per `episode_dedup`. CYCLE #9.

Strategia: usa EpisodicMemory con tmp_data_dir, popola pochi episodi
controllati, verifica che find_duplicate_groups + dedup_episodes
producano il risultato atteso.
"""
from __future__ import annotations

import time

import pytest

from engram.episode_dedup import dedup_episodes, find_duplicate_groups
from engram.memory import Episode, EpisodicMemory


@pytest.fixture
def memory(tmp_path):
    db_path = tmp_path / "ep.db"
    return EpisodicMemory(db_path=db_path)


def _ep(eid: str, task: str, answer: str, outcome: str = "success",
        created_at: float | None = None) -> Episode:
    """Crea un Episode minimale per i test (no traces)."""
    return Episode(
        id=eid,
        task_id=f"t-{eid}",
        task_text=task,
        final_answer=answer,
        outcome=outcome,
        tokens_used=0,
        skills_used=[],
        traces=[],
        created_at=created_at if created_at is not None else time.time(),
    )


def test_no_duplicates_empty_result(memory):
    memory.store(_ep("e1", "unique task A", "answer A"))
    memory.store(_ep("e2", "unique task B", "answer B"))
    groups = find_duplicate_groups(memory)
    assert groups == []


def test_finds_exact_triple_duplicates(memory):
    # 3 episodi con stessa (task_text, final_answer, outcome) → 1 gruppo
    memory.store(_ep("e1", "task X", "X-ans", "success", created_at=100.0))
    memory.store(_ep("e2", "task X", "X-ans", "success", created_at=200.0))
    memory.store(_ep("e3", "task X", "X-ans", "success", created_at=300.0))
    # 1 episodio diverso → non in gruppo
    memory.store(_ep("e4", "task Y", "Y-ans", "success"))

    groups = find_duplicate_groups(memory)
    assert len(groups) == 1
    g = groups[0]
    assert g["count"] == 3
    assert g["task_text"] == "task X"
    assert g["winner_id"] == "e3"  # most recent
    assert set(g["loser_ids"]) == {"e1", "e2"}


def test_different_answer_not_grouped(memory):
    """Stesso task ma answer diversi → 2 gruppi distinti (size 1 ciascuno
    → entrambi filtrati out)."""
    memory.store(_ep("e1", "task X", "ans-A"))
    memory.store(_ep("e2", "task X", "ans-B"))
    groups = find_duplicate_groups(memory)
    assert groups == []


def test_different_outcome_not_grouped(memory):
    memory.store(_ep("e1", "task X", "ans", outcome="success"))
    memory.store(_ep("e2", "task X", "ans", outcome="failure"))
    groups = find_duplicate_groups(memory)
    assert groups == []


def test_dedup_dry_run_does_not_delete(memory):
    for i in range(5):
        memory.store(_ep(f"e{i}", "X", "ans", created_at=float(i)))
    report = dedup_episodes(memory, apply=False)
    assert report["dry_run"] is True
    assert report["episodes_total"] == 5
    assert report["groups_found"] == 1
    assert report["episodes_to_remove"] == 4
    assert report["applied_removed"] == 0
    # Niente è stato cancellato
    with memory._connect() as c:
        assert c.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 5


def test_dedup_apply_deletes_losers_keeps_winner(memory):
    for i in range(5):
        memory.store(_ep(f"e{i}", "X", "ans", created_at=float(i)))
    report = dedup_episodes(memory, apply=True)
    assert report["dry_run"] is False
    assert report["applied_removed"] == 4
    # Solo e4 (winner most recent) sopravvive
    with memory._connect() as c:
        rows = c.execute("SELECT id FROM episodes").fetchall()
        ids = [r["id"] for r in rows]
        assert ids == ["e4"]


def test_dedup_respects_max_remove_cap(memory):
    for i in range(10):
        memory.store(_ep(f"e{i}", "X", "ans", created_at=float(i)))
    # 9 losers, cap=3 → solo 3 vengono rimossi, 6 skipped
    report = dedup_episodes(memory, apply=True, max_remove=3)
    assert report["applied_removed"] == 3
    assert report["applied_skipped_cap"] == 6
    with memory._connect() as c:
        n = c.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        assert n == 7


def test_preview_groups_sorted_by_count_desc(memory):
    # gruppo grande: 4 di X
    for i in range(4):
        memory.store(_ep(f"x{i}", "X", "ans", created_at=float(i)))
    # gruppo medio: 2 di Y
    memory.store(_ep("y1", "Y", "ans", created_at=10.0))
    memory.store(_ep("y2", "Y", "ans", created_at=11.0))
    report = dedup_episodes(memory, apply=False)
    counts = [g["count"] for g in report["preview_groups"]]
    assert counts == [4, 2]
