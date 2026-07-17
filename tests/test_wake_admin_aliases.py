"""FORGIA pezzo #149 — WakeAgent admin alias tests.

Pezzi #142, #146, #147, #148 added thin delegates on WakeAgent:
- skill_usage_histogram
- outcome_breakdown
- steps_summary
- token_usage_summary

Each is a one-liner that delegates to memory. Tests pin the contract.
"""
from __future__ import annotations

import time
from pathlib import Path

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.skill import SkillLibrary
from verimem.wake import WakeAgent


def _ep(eid, *, outcome="success", skills=None, n_steps=1, tokens=10) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=eid,
        outcome=outcome, final_answer="ok",
        traces=[
            Trace(step=i, thought="t", action="a",
                  action_input="", observation="o")
            for i in range(1, n_steps + 1)
        ],
        tokens_used=tokens, skills_used=skills or [],
        created_at=time.time(),
    )


def _agent(tmp_path: Path) -> WakeAgent:
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    return WakeAgent(memory=mem, skills=skills)


def test_skill_usage_histogram(tmp_path: Path):
    agent = _agent(tmp_path)
    agent.memory.store(_ep("e1", skills=["A", "B"]))
    agent.memory.store(_ep("e2", skills=["A"]))
    h = agent.skill_usage_histogram()
    assert h == {"A": 2, "B": 1}


def test_outcome_breakdown(tmp_path: Path):
    agent = _agent(tmp_path)
    agent.memory.store(_ep("s1", outcome="success"))
    agent.memory.store(_ep("s2", outcome="success"))
    agent.memory.store(_ep("f1", outcome="failure"))
    b = agent.outcome_breakdown()
    assert b["success"] == 2
    assert b["failure"] == 1


def test_steps_summary(tmp_path: Path):
    agent = _agent(tmp_path)
    agent.memory.store(_ep("e1", n_steps=2))
    agent.memory.store(_ep("e2", n_steps=4))
    s = agent.steps_summary()
    assert s["min"] == 2.0
    assert s["max"] == 4.0
    assert s["mean"] == 3.0


def test_token_usage_summary(tmp_path: Path):
    agent = _agent(tmp_path)
    agent.memory.store(_ep("e1", tokens=100))
    agent.memory.store(_ep("e2", tokens=200))
    s = agent.token_usage_summary()
    assert s["total"] == 300.0
    assert s["mean"] == 150.0
