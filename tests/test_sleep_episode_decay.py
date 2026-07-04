"""Tests for FORGIA pezzo #9: cabling decay_prune (pezzo #7) into sleep.

Pezzo #7 implemented `EpisodicMemory.decay_prune(threshold)` but the
sleep cycle didn't call it — primitives sitting unused. Pezzo #9 wires
it in as a sleep stage and tests the integration end-to-end.

Three measurable invariants:

  1. Sleep cycle runs `_stage_episode_decay` when enabled, populating
     `report.n_episodes_decayed` with the count of pruned episodes.

  2. The cap `episode_decay_max_per_cycle` protects against unbounded
     delete: even with 1000 stale episodes, one cycle prunes ≤ cap.

  3. Disabling via `CONFIG.episode_decay_enabled = False` preserves
     legacy behaviour — no episodes touched.
"""
from __future__ import annotations

import dataclasses
import time

import pytest

from engram import config as config_mod
from engram.config import CONFIG
from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.skill import SkillLibrary
from engram.sleep import SleepEngine, SleepReport


def _patch_config(monkeypatch, **fields) -> None:
    """Frozen-dataclass-safe CONFIG mutation: replace the binding."""
    new = dataclasses.replace(CONFIG, **fields)
    monkeypatch.setattr(config_mod, "CONFIG", new)
    from engram import memory as memory_mod
    from engram import sleep as sleep_mod
    monkeypatch.setattr(sleep_mod, "CONFIG", new)
    monkeypatch.setattr(memory_mod, "CONFIG", new)


def _ancient(id_: str, age_days: float = 90.0) -> Episode:
    return Episode(
        id=id_, task_id="t", task_text=f"old task {id_}",
        outcome="success", final_answer="ok",
        created_at=time.time() - age_days * 86400,
        traces=[Trace(
            step=1, thought="x", action="x", action_input="{}",
            observation="x",
        )],
    )


def _build_engine(tmp_path) -> SleepEngine:
    skills = SkillLibrary(
        dir_path=tmp_path / "skills_dir", db_path=tmp_path / "sk.db",
    )
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    sem = SemanticMemory(db_path=tmp_path / "sm.db")
    return SleepEngine(memory=mem, skills=skills, semantic=sem,
                       llm=None, seed=42)


# ---------- Test 1: stage runs and reports count ------------------------


def test_sleep_runs_episode_decay_stage_when_enabled(tmp_path, monkeypatch):
    _patch_config(
        monkeypatch,
        episode_decay_enabled=True,
        episode_decay_threshold=0.30,
        episode_decay_max_per_cycle=100,
        sleep_min_episodes=2,
    )
    engine = _build_engine(tmp_path)
    # Populate with 5 ancient episodes (all should fall below threshold)
    for i in range(5):
        engine.memory.store(_ancient(f"ancient_{i}", age_days=120.0))

    # The sleep cycle's other stages need an LLM; we only want to test
    # the decay stage directly.
    report = SleepReport()
    engine._stage_episode_decay(report)

    assert report.n_episodes_decayed >= 5, (
        f"_stage_episode_decay didn't prune the 5 ancient episodes "
        f"(reported {report.n_episodes_decayed})"
    )
    assert engine.memory.count() == 0


# ---------- Test 2: cap respected ---------------------------------------


def test_episode_decay_respects_max_per_cycle_cap(tmp_path, monkeypatch):
    _patch_config(
        monkeypatch,
        episode_decay_enabled=True,
        episode_decay_threshold=0.30,
        episode_decay_max_per_cycle=10,  # cap at 10 per cycle
        sleep_min_episodes=2,
    )
    engine = _build_engine(tmp_path)
    for i in range(50):
        engine.memory.store(_ancient(f"ancient_{i:02d}", age_days=120.0))

    report = SleepReport()
    engine._stage_episode_decay(report)

    # At most `max_per_cycle` should have been pruned
    assert report.n_episodes_decayed <= 10
    # Remaining count = 50 - pruned
    assert engine.memory.count() == 50 - report.n_episodes_decayed


# ---------- Test 3: disabled flag preserves legacy behaviour ------------


def test_episode_decay_disabled_skips_pruning(tmp_path, monkeypatch):
    _patch_config(
        monkeypatch,
        episode_decay_enabled=False,
        sleep_min_episodes=2,
    )
    engine = _build_engine(tmp_path)
    for i in range(5):
        engine.memory.store(_ancient(f"ancient_{i}", age_days=120.0))

    report = SleepReport()
    engine._stage_episode_decay(report)
    assert report.n_episodes_decayed == 0
    assert engine.memory.count() == 5


# ---------- Test 4: integration - hot episodes preserved ----------------


def test_full_decay_stage_preserves_hot_episodes(tmp_path, monkeypatch):
    """Mixed corpus: 3 ancient + 2 hot. Decay stage prunes only the
    ancient ones."""
    _patch_config(
        monkeypatch,
        episode_decay_enabled=True,
        episode_decay_threshold=0.30,
        episode_decay_max_per_cycle=100,
        sleep_min_episodes=2,
    )
    engine = _build_engine(tmp_path)
    for i in range(3):
        engine.memory.store(_ancient(f"ancient_{i}", age_days=120.0))
    # Hot episodes — recently accessed, high salience
    for i in range(2):
        ep = Episode(
            id=f"hot_{i}", task_id="t", task_text="active task",
            outcome="success", final_answer="ok",
            created_at=time.time() - 1.0,  # 1s old
            last_accessed_at=time.time() - 1.0,
            access_count=5,
            salience_score=0.8,
            traces=[Trace(
                step=1, thought="x", action="x", action_input="{}",
                observation="x",
            )],
        )
        engine.memory.store(ep)

    report = SleepReport()
    engine._stage_episode_decay(report)
    assert report.n_episodes_decayed == 3  # ancients only
    surviving = {ep.id for ep in engine.memory.all()}
    assert "hot_0" in surviving
    assert "hot_1" in surviving
