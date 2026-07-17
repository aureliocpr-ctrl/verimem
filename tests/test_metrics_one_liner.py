"""FORGIA pezzo #247 — Wave 46: compact metrics one-liner.

Single string summary of the whole memory system. Useful for
status-bar displays, CI greppable output, and SessionStart context.

Format: `HippoAgent: E ep (S✓/F✗), N facts, K skills (P prom),
T tok last 7d`
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from verimem.skill import Skill


@dataclass
class _FakeEp:
    outcome: str = "success"
    tokens_used: int = 0
    created_at: float = 0.0


class _FakeSemantic:
    def __init__(self, n: int = 0) -> None:
        self._n = n

    def count(self) -> int:
        return self._n


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._skills = skills

    def all(self, status: str | None = None) -> list[Skill]:
        if status is None:
            return list(self._skills)
        return [s for s in self._skills if s.status == status]

    def count(self) -> int:
        return len(self._skills)


class _FakeMemory:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self._eps = eps

    def all(self, limit: int | None = None):
        return list(self._eps if limit is None else self._eps[:limit])

    def count(self) -> int:
        return len(self._eps)


class _FakeAgent:
    def __init__(
        self, eps: list[_FakeEp], skills: list[Skill], n_facts: int,
    ) -> None:
        self.memory = _FakeMemory(eps)
        self.skills = _FakeSkillsStore(skills)
        self.semantic = _FakeSemantic(n_facts)


def test_returns_string():
    from verimem.metrics_one_liner import metrics_one_liner

    out = metrics_one_liner(agent=_FakeAgent([], [], 0))
    assert isinstance(out, str)


def test_includes_episode_count():
    from verimem.metrics_one_liner import metrics_one_liner

    eps = [_FakeEp("success"), _FakeEp("failure"), _FakeEp("success")]
    out = metrics_one_liner(agent=_FakeAgent(eps, [], 0))
    assert "3" in out


def test_includes_success_failure_breakdown():
    from verimem.metrics_one_liner import metrics_one_liner

    eps = [
        _FakeEp("success"), _FakeEp("success"),
        _FakeEp("failure"),
    ]
    out = metrics_one_liner(agent=_FakeAgent(eps, [], 0))
    # 2 success, 1 failure should both appear.
    assert "2" in out
    assert "1" in out


def test_includes_skills_count():
    from verimem.metrics_one_liner import metrics_one_liner

    skills = [
        Skill(id="a", status="promoted"),
        Skill(id="b", status="candidate"),
        Skill(id="c", status="promoted"),
    ]
    out = metrics_one_liner(agent=_FakeAgent([], skills, 0))
    # 3 total, 2 promoted.
    assert "3" in out


def test_includes_facts_count():
    from verimem.metrics_one_liner import metrics_one_liner

    out = metrics_one_liner(agent=_FakeAgent([], [], 42))
    assert "42" in out


def test_includes_tokens_in_window():
    from verimem.metrics_one_liner import metrics_one_liner

    now = time.time()
    eps = [
        _FakeEp("success", tokens_used=1000, created_at=now),
        _FakeEp("success", tokens_used=2000, created_at=now - 86400 * 2),
        _FakeEp("success", tokens_used=5000,
                created_at=now - 86400 * 100),  # outside window
    ]
    out = metrics_one_liner(agent=_FakeAgent(eps, [], 0))
    # 3000 in last 7d (1000 + 2000).
    assert "3000" in out


def test_handles_empty_agent():
    from verimem.metrics_one_liner import metrics_one_liner

    out = metrics_one_liner(agent=_FakeAgent([], [], 0))
    assert "HippoAgent" in out
    assert "0" in out
