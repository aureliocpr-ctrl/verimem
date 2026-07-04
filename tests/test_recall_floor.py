"""Tests for the min_similarity floor in EpisodicMemory.recall.

Property: when min_similarity > 0, episodes whose cosine to the query
falls below the floor are dropped. The floor applies in BOTH paths —
unfiltered (uses the in-memory matrix) and outcome-filtered (uses a
SQL scan). Default floor 0.0 preserves legacy behaviour.
"""
from __future__ import annotations

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory


def _ep(eid: str, task: str, outcome: str = "success") -> Episode:
    return Episode(
        id=eid, task_id="t", task_text=task, outcome=outcome,
        traces=[Trace(step=1, thought="", action="a", action_input="",
                      observation="o")],
    )


def test_default_floor_zero_returns_top_k_regardless(tmp_data_dir):
    """Legacy behaviour preserved: floor=0 returns top-k even when sim
    is low across the board."""
    mem = EpisodicMemory(db_path=tmp_data_dir / "ep.db")
    mem.store(_ep("a", "fix calculator add bug"))
    mem.store(_ep("b", "the moon orbits earth at 384400 km"))
    mem.store(_ep("c", "pasta carbonara recipe step by step"))

    # Query is "fix bug" — only "a" is really similar; "b" and "c"
    # are unrelated content.
    out = mem.recall("fix bug in arithmetic", k=3)
    assert len(out) == 3  # legacy: returns 3


def test_floor_drops_irrelevant_results(tmp_data_dir):
    """A modest floor drops the unrelated-content matches."""
    mem = EpisodicMemory(db_path=tmp_data_dir / "ep.db")
    mem.store(_ep("a", "fix calculator add bug return wrong sign"))
    mem.store(_ep("b", "the moon orbits earth at 384400 km"))
    mem.store(_ep("c", "pasta carbonara recipe step by step"))

    out = mem.recall(
        "fix bug arithmetic calculator", k=3, min_similarity=0.30,
    )
    # The arithmetic episode should survive, the moon and pasta should be cut.
    ids = [ep.id for ep, _ in out]
    assert "a" in ids
    assert "b" not in ids
    assert "c" not in ids


def test_floor_works_with_outcome_filter(tmp_data_dir):
    """The filtered path (outcome-specific SQL scan) honours the same floor."""
    mem = EpisodicMemory(db_path=tmp_data_dir / "ep.db")
    mem.store(_ep("a", "fix calculator add bug", outcome="success"))
    mem.store(_ep("b", "spaghetti recipe", outcome="success"))

    out = mem.recall(
        "fix arithmetic", k=3, outcome_filter="success", min_similarity=0.30,
    )
    ids = [ep.id for ep, _ in out]
    assert "a" in ids
    assert "b" not in ids


def test_floor_returns_empty_when_nothing_clears_it(tmp_data_dir):
    """Aggressive floor + no related content: empty result, not noise."""
    mem = EpisodicMemory(db_path=tmp_data_dir / "ep.db")
    mem.store(_ep("a", "the moon orbits earth"))
    mem.store(_ep("b", "pasta carbonara recipe"))

    out = mem.recall(
        "fix arithmetic bug", k=3, min_similarity=0.50,
    )
    assert out == []
