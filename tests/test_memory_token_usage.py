"""FORGIA pezzo #137 — `EpisodicMemory.token_usage_summary()`."""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(eid: str, tokens: int) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=tokens, skills_used=[],
        created_at=time.time(),
    )


def test_token_usage_empty(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    s = mem.token_usage_summary()
    assert s["total"] == 0.0
    assert s["max"] == 0.0
    assert s["n_with_tokens"] == 0.0


def test_token_usage_aggregates(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", 100))
    mem.store(_ep("e2", 200))
    mem.store(_ep("e3", 300))
    s = mem.token_usage_summary()
    assert s["total"] == 600.0
    assert s["mean"] == 200.0
    assert s["max"] == 300.0
    assert s["n_with_tokens"] == 3.0
