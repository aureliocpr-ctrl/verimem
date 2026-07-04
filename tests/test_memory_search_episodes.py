"""FORGIA pezzo #195 — `EpisodicMemory.search_episodes(query, ...)`."""
from __future__ import annotations

import time
from pathlib import Path

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory


def _ep(eid: str, text: str, *, outcome: str = "success",
         created_at: float | None = None) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=text,
        outcome=outcome, final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                       action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=created_at if created_at is not None else time.time(),
    )


def test_search_episodes_substring_case_insensitive(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", "compute Factorial of 10"))
    mem.store(_ep("e2", "send email about FACTORIAL"))
    mem.store(_ep("e3", "reverse hello"))
    out = mem.search_episodes("factorial")
    ids = {e.id for e in out}
    assert ids == {"e1", "e2"}


def test_search_episodes_outcome_filter(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", "task X", outcome="success"))
    mem.store(_ep("e2", "task X again", outcome="failure"))
    out = mem.search_episodes("task", outcome="failure")
    assert [e.id for e in out] == ["e2"]


def test_search_episodes_empty_query_returns_recent_capped(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    base = 1000.0
    for i in range(5):
        mem.store(_ep(f"e{i}", f"text {i}", created_at=base + i))
    out = mem.search_episodes("", limit=3)
    # newest first → e4, e3, e2
    assert [e.id for e in out] == ["e4", "e3", "e2"]


def test_search_episodes_no_match_returns_empty(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1", "anything"))
    assert mem.search_episodes("nope") == []
