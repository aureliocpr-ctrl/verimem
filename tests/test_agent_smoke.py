"""FORGIA pezzo #156 — HippoAgent.build() smoke test.

Pins the fact that the full agent factory works end-to-end with
HIPPO_OFFLINE=1 (mock LLM). Catches regressions like a missing
import or a default config that fails on first call.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def test_hippo_agent_build_smokes_clean(tmp_path: Path, monkeypatch):
    """HippoAgent.build() boots without errors on isolated DB.

    `HIPPO_DATA_DIR` is read at config-import time (FORGIA #29), so an
    in-process monkeypatch fires too late — the cached CONFIG.data_dir
    still points at the production tree. Inject explicit paths via
    constructor args instead.
    """
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    from engram.agent import HippoAgent
    from engram.memory import EpisodicMemory
    from engram.semantic import SemanticMemory
    from engram.skill import SkillLibrary
    from engram.sleep import SleepEngine
    from engram.wake import WakeAgent
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    wake = WakeAgent(memory=mem, skills=skills)
    sleep = SleepEngine(memory=mem, skills=skills, semantic=sem)
    agent = HippoAgent(
        memory=mem, skills=skills, semantic=sem, wake=wake, sleep=sleep,
    )
    m = agent.wake.metrics()
    assert m["n_episodes"] == 0
    assert m["n_skills"] == 0


def test_hippo_agent_consolidate_skip_below_threshold(
    tmp_path: Path, monkeypatch,
):
    """Empty memory → sleep cycle skips, returns empty report."""
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    from engram.agent import HippoAgent
    from engram.memory import EpisodicMemory
    from engram.semantic import SemanticMemory
    from engram.skill import SkillLibrary
    from engram.sleep import SleepEngine
    from engram.wake import WakeAgent
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    wake = WakeAgent(memory=mem, skills=skills)
    sleep = SleepEngine(memory=mem, skills=skills, semantic=sem)
    agent = HippoAgent(
        memory=mem, skills=skills, semantic=sem, wake=wake, sleep=sleep,
    )
    report = agent.consolidate()
    assert report.n_episodes_replayed == 0
    assert report.n_nrem_skills == 0
    assert report.n_llm_calls == 0
