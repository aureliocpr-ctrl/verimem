"""Tests for the historical-fragility annotations in the forward replay block.

The contract: when the forward replay block is rendered for a skill that
has past failures, each step of the predicted action sequence is annotated
with "⚠×N" where N is the count of past failures that diverged at *that*
step. Only counts ≥ 2 are surfaced (one-off bad luck doesn't earn a mark).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from verimem.episode import Episode, Trace
from verimem.skill import Skill
from verimem.wake import WakeAgent, WakeConfig


def _trace(step: int, action: str, action_input: str, observation: str) -> Trace:
    return Trace(step=step, thought="", action=action,
                 action_input=action_input, observation=observation)


@pytest.fixture
def wake_agent(tmp_data_dir):
    """A WakeAgent with mock LLM and a fresh skill library."""
    from verimem.memory import EpisodicMemory
    from verimem.skill import SkillLibrary
    return WakeAgent(
        memory=EpisodicMemory(db_path=tmp_data_dir / "ep.db"),
        skills=SkillLibrary(
            dir_path=tmp_data_dir / "skills",
            db_path=tmp_data_dir / "skills_index.db",
        ),
        llm=MagicMock(),
        config=WakeConfig(),
    )


def test_repeated_divergence_step_gets_warning_mark(wake_agent):
    """Two past failures both diverged at step 2 of the success path.
    The forward replay block must show "⚠×2" on the step 2 action.
    """
    # Skill with promoted status and a fitness above the forward replay
    # threshold so the block actually renders.
    skill = Skill(
        id="sk_bug",
        name="bugfix_arith",
        trigger="fix arithmetic bug",
        body="patch return statement",
        status="promoted",
        trials=10, successes=8,
    )
    # Promote-style trials/successes are enough — fitness_mean
    # works out to (8 + 2) / (10 + 4) ≈ 0.71 which is above the
    # default forward_replay_min_fitness=0.5.

    success = Episode(
        id="ep_ok",
        task_id="bugfix",
        task_text="fix add",
        outcome="success",
        skills_used=[skill.id],
        traces=[
            _trace(1, "fs_read_file", "calc.py",
                   "def add(a, b):\n    return a - b"),
            _trace(2, "apply_edit", "patch", "edit applied"),
            _trace(3, "submit_solution", "ok", "done"),
        ],
    )
    # Two failures, BOTH diverging at step 2 (chose fs_write_file
    # instead of apply_edit under the same observation).
    failure_a = Episode(
        id="ep_fa",
        task_id="bugfix",
        task_text="fix add a",
        outcome="failure",
        skills_used=[skill.id],
        traces=[
            _trace(1, "fs_read_file", "calc.py",
                   "def add(a, b):\n    return a - b"),
            _trace(2, "fs_write_file", "patch", "edit applied"),  # divergence
            _trace(3, "submit_solution", "tried", "failed"),
        ],
    )
    failure_b = Episode(
        id="ep_fb",
        task_id="bugfix",
        task_text="fix add b",
        outcome="failure",
        skills_used=[skill.id],
        traces=[
            _trace(1, "fs_read_file", "calc.py",
                   "def add(a, b):\n    return a - b"),
            _trace(2, "rewrite_file", "patch", "edit applied"),  # divergence too
            _trace(3, "submit_solution", "tried", "failed"),
        ],
    )

    episodes = [(success, 0.9), (failure_a, 0.85), (failure_b, 0.85)]

    block = wake_agent._forward_replay_block(
        task="fix arithmetic bug in calc.py",
        skills=[skill],
        episodes=episodes,
    )

    # Both failures diverged at success step 2 → "⚠×2" must appear.
    assert "⚠" in block
    assert "×2" in block
    assert "apply_edit⚠×2" in block
    # The legend must explain what the mark means.
    assert "historical divergence" in block.lower()


def test_single_divergence_does_not_earn_mark(wake_agent):
    """One failure diverging at a step produces ⚠×1 — but our threshold
    is N >= 2, so no mark should appear.
    """
    skill = Skill(
        id="sk_bug2", name="bugfix", trigger="fix bug", body="patch",
        status="promoted", trials=10, successes=8,
    )
    success = Episode(
        id="ep_ok2", task_id="t", task_text="t", outcome="success",
        skills_used=[skill.id],
        traces=[
            _trace(1, "fs_read_file", "x.py", "obs1"),
            _trace(2, "apply_edit", "p", "obs2"),
            _trace(3, "submit_solution", "ok", "done"),
        ],
    )
    failure = Episode(
        id="ep_f", task_id="t", task_text="t", outcome="failure",
        skills_used=[skill.id],
        traces=[
            _trace(1, "fs_read_file", "x.py", "obs1"),
            _trace(2, "rewrite_file", "p", "obs2"),
            _trace(3, "submit_solution", "ok", "done"),
        ],
    )
    episodes = [(success, 0.9), (failure, 0.85)]

    block = wake_agent._forward_replay_block(
        task="fix bug", skills=[skill], episodes=episodes,
    )

    # Single divergence — no mark at threshold N>=2.
    assert "⚠" not in block
