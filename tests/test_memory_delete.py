"""FORGIA pezzo #109 — `EpisodicMemory.delete(episode_id)`."""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(eid: str) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome="success", final_answer="ok",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=time.time(),
    )


def test_delete_existing_episode_returns_true(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1"))
    mem.store(_ep("e2"))
    assert mem.count() == 2
    assert mem.delete("e1") is True
    assert mem.count() == 1
    assert mem.get("e1") is None
    assert mem.get("e2") is not None


def test_delete_unknown_returns_false(tmp_path: Path):
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("e1"))
    assert mem.delete("nope") is False
    assert mem.count() == 1


def test_delete_invalidates_index(tmp_path: Path):
    """Recall after delete must not return the deleted episode."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    mem.store(_ep("alpha"))
    mem.store(_ep("beta"))
    # Touch the recall path so the in-memory index is built.
    _ = mem.recall("alpha", k=2, track_access=False)
    mem.delete("alpha")
    hits = mem.recall("alpha", k=2, track_access=False)
    out_ids = {ep.id for ep, _ in hits}
    assert "alpha" not in out_ids


def test_wake_agent_recent_episodes(tmp_path: Path):
    """FORGIA pezzo #132: WakeAgent.recent_episodes returns K most recent."""
    from verimem.skill import SkillLibrary
    from verimem.wake import WakeAgent
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    # Store 5 episodes; recent_episodes(3) returns latest 3.
    for i in range(5):
        mem.store(_ep(f"e{i}"))
        # Tiny sleep equivalent: bump created_at via fresh stores.
    agent = WakeAgent(memory=mem, skills=skills)
    recent = agent.recent_episodes(k=3)
    assert len(recent) == 3


def test_wake_agent_delete_episode(tmp_path: Path):
    """FORGIA pezzo #114: WakeAgent.delete_episode delegates to memory."""
    from verimem.skill import SkillLibrary
    from verimem.wake import WakeAgent
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    mem.store(_ep("e1"))
    mem.store(_ep("e2"))
    agent = WakeAgent(memory=mem, skills=skills)
    assert agent.delete_episode("e1") is True
    assert agent.delete_episode("nope") is False
    assert mem.count() == 1


def test_delete_by_task_text_removes_all_matches(tmp_path: Path):
    """FORGIA pezzo #111: bulk delete by task_text."""
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    e1 = Episode(id="e1", task_id="t1", task_text="duplicated task",
                 outcome="success", final_answer="ok",
                 traces=[Trace(step=1, thought="t", action="a",
                                action_input="", observation="o")],
                 tokens_used=1, skills_used=[],
                 created_at=time.time())
    e2 = Episode(id="e2", task_id="t2", task_text="duplicated task",
                 outcome="success", final_answer="ok",
                 traces=[Trace(step=1, thought="t", action="a",
                                action_input="", observation="o")],
                 tokens_used=1, skills_used=[],
                 created_at=time.time())
    e3 = Episode(id="e3", task_id="t3", task_text="other task",
                 outcome="success", final_answer="ok",
                 traces=[Trace(step=1, thought="t", action="a",
                                action_input="", observation="o")],
                 tokens_used=1, skills_used=[],
                 created_at=time.time())
    mem.store(e1)
    mem.store(e2)
    mem.store(e3)
    n = mem.delete_by_task_text("duplicated task")
    assert n == 2
    assert mem.count() == 1
    remaining = list(mem.all())
    assert len(remaining) == 1
    assert remaining[0].task_text == "other task"
