"""FORGIA pezzo #134 — `EpisodicMemory.episodes_in_window(start, end)`."""
from __future__ import annotations

from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(eid: str, ts: float) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=ts,
    )


def test_in_window_returns_only_inside_range(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("old", 1000.0))
    mem.store(_ep("mid", 2000.0))
    mem.store(_ep("new", 3000.0))
    out = mem.episodes_in_window(1500.0, 2500.0)
    ids = {e.id for e in out}
    assert ids == {"mid"}


def test_in_window_empty_range(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", 1000.0))
    out = mem.episodes_in_window(2000.0, 3000.0)
    assert out == []


def test_in_window_inclusive_start_exclusive_end(tmp_path: Path):
    """[start, end) — start included, end excluded."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("at_start", 1000.0))
    mem.store(_ep("at_end", 2000.0))
    out = mem.episodes_in_window(1000.0, 2000.0)
    ids = {e.id for e in out}
    assert ids == {"at_start"}


def test_episodes_last_n_minutes(tmp_path: Path):
    """FORGIA pezzo #135: convenience wrapper for live windows."""
    import time
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    now = time.time()
    mem.store(_ep("recent", now - 30))   # 30s ago
    mem.store(_ep("hour_ago", now - 3700))  # 1h+ ago
    out = mem.episodes_last_n_minutes(5)
    ids = {e.id for e in out}
    assert "recent" in ids
    assert "hour_ago" not in ids
