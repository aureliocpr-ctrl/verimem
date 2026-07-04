"""FORGIA pezzo #248 — Wave 47: recall + forward planning combo.

Lightweight version of hippo_reason: for each top recall skill,
also build a forward trajectory from there. The user gets
'top 3 candidate skills, and for each: what comes next in a chain'.

Less heavy than full reason_about_task (no STRIPS, no analogy);
faster, smaller payload.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engram.skill import Skill


@dataclass
class _FakeEp:
    skills_used: list[str] = field(default_factory=list)


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._skills = skills

    def all(self, status=None) -> list[Skill]:
        return list(self._skills)

    def retrieve(self, task, k=3, task_embedding=None):
        # Simple token-match recall: split on whitespace AND _.
        import re
        task_tokens = set(re.findall(r"[a-z0-9]+", task.lower()))
        scored: list[tuple[Skill, float]] = []
        for s in self._skills:
            t = set(re.findall(r"[a-z0-9]+", (s.name or "").lower()))
            if t & task_tokens:
                scored.append((s, len(t & task_tokens) / max(len(t | task_tokens), 1)))
        scored.sort(key=lambda x: -x[1])
        return scored[:k]


class _FakeMemory:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self._eps = eps

    def all(self, limit=None):
        return list(self._eps)


class _FakeAgent:
    def __init__(self, skills: list[Skill], eps: list[_FakeEp]) -> None:
        self.skills = _FakeSkillsStore(skills)
        self.memory = _FakeMemory(eps)


def test_empty_returns_empty_recalls():
    from engram.recall_chain import recall_chain

    a = _FakeAgent([], [])
    out = recall_chain(task="anything", agent=a)
    assert out["task"] == "anything"
    assert out["recalls"] == []


def test_returns_recall_with_forward_plans():
    from engram.recall_chain import recall_chain

    skills = [
        Skill(id="A", name="alpha skill"),
        Skill(id="B", name="beta skill"),
    ]
    eps = [_FakeEp(["A", "B"])] * 3
    a = _FakeAgent(skills, eps)
    out = recall_chain(task="alpha", agent=a, forward_depth=1)
    assert len(out["recalls"]) >= 1
    top = out["recalls"][0]
    assert "skill_id" in top
    assert "forward_plans" in top


def test_no_episodes_recall_only():
    """No episodes → forward_plans empty for each recall."""
    from engram.recall_chain import recall_chain

    skills = [Skill(id="A", name="alpha")]
    a = _FakeAgent(skills, [])
    out = recall_chain(task="alpha", agent=a)
    assert out["recalls"]
    assert out["recalls"][0]["forward_plans"] == []


def test_k_recall_respected():
    from engram.recall_chain import recall_chain

    skills = [Skill(id=f"s{i}", name=f"task skill{i}") for i in range(5)]
    a = _FakeAgent(skills, [])
    out = recall_chain(task="task", agent=a, k_recall=2)
    assert len(out["recalls"]) <= 2


def test_payload_shape_complete():
    from engram.recall_chain import recall_chain

    a = _FakeAgent([], [])
    out = recall_chain(task="x", agent=a)
    for k in ("task", "recalls", "n_episodes_used"):
        assert k in out
