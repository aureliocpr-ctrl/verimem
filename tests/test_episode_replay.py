"""FORGIA pezzo #256 — Wave 55: episode replay render.

Render an episode as readable markdown for chat-UI display.
Shows: task, outcome, skills used, tokens, answer, and any
trajectory metadata available.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class _FakeEp:
    id: str = "ep1"
    task_text: str = ""
    final_answer: str = ""
    outcome: str = "success"
    skills_used: list[str] = field(default_factory=list)
    tokens_used: int = 0
    num_steps: int = 1
    created_at: float = field(default_factory=time.time)


def test_returns_string():
    from verimem.episode_replay import render_episode_replay

    out = render_episode_replay(_FakeEp())
    assert isinstance(out, str)


def test_includes_task_text():
    from verimem.episode_replay import render_episode_replay

    ep = _FakeEp(task_text="compute the answer")
    out = render_episode_replay(ep)
    assert "compute the answer" in out


def test_shows_outcome():
    from verimem.episode_replay import render_episode_replay

    s = render_episode_replay(_FakeEp(outcome="success"))
    f = render_episode_replay(_FakeEp(outcome="failure"))
    assert ("✓" in s or "success" in s.lower())
    assert ("✗" in f or "failure" in f.lower())


def test_lists_skills_used():
    from verimem.episode_replay import render_episode_replay

    ep = _FakeEp(skills_used=["skill_a", "skill_b"])
    out = render_episode_replay(ep)
    assert "skill_a" in out
    assert "skill_b" in out


def test_includes_final_answer():
    from verimem.episode_replay import render_episode_replay

    ep = _FakeEp(final_answer="42")
    out = render_episode_replay(ep)
    assert "42" in out


def test_shows_tokens_when_nonzero():
    from verimem.episode_replay import render_episode_replay

    ep = _FakeEp(tokens_used=1500)
    out = render_episode_replay(ep)
    assert "1500" in out


def test_handles_empty_episode():
    from verimem.episode_replay import render_episode_replay

    out = render_episode_replay(_FakeEp(id="empty"))
    assert isinstance(out, str)
    assert len(out) > 0
