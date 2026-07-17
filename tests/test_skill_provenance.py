"""FORGIA pezzo #271 — Wave 70: skill provenance episode lookup."""
from __future__ import annotations

from dataclasses import dataclass

from verimem.skill import Skill


@dataclass
class _FakeEp:
    id: str
    task_text: str = ""
    outcome: str = "success"


class _FakeMemory:
    def __init__(self, eps):
        self._by_id = {e.id: e for e in eps}

    def get(self, eid):
        return self._by_id.get(eid)


class _FakeSkillsStore:
    def __init__(self, skills):
        self._by_id = {s.id: s for s in skills}

    def get(self, sid):
        return self._by_id.get(sid)


class _FakeAgent:
    def __init__(self, skills, eps):
        self.skills = _FakeSkillsStore(skills)
        self.memory = _FakeMemory(eps)


def test_unknown_skill():
    from verimem.skill_provenance import skill_provenance

    out = skill_provenance(skill_id="ZZZ", agent=_FakeAgent([], []))
    assert out["found"] is False


def test_empty_provenance():
    from verimem.skill_provenance import skill_provenance

    skills = [Skill(id="x", provenance_episodes=[])]
    a = _FakeAgent(skills, [])
    out = skill_provenance(skill_id="x", agent=a)
    assert out["found"] is True
    assert out["episodes"] == []
    assert out["n_provenance_ids"] == 0


def test_returns_provenance():
    from verimem.skill_provenance import skill_provenance

    eps = [_FakeEp("e1", task_text="task1"),
           _FakeEp("e2", task_text="task2")]
    skills = [Skill(id="x", provenance_episodes=["e1", "e2"])]
    a = _FakeAgent(skills, eps)
    out = skill_provenance(skill_id="x", agent=a)
    ids = [e["id"] for e in out["episodes"]]
    assert "e1" in ids
    assert "e2" in ids


def test_separates_missing_provenance():
    from verimem.skill_provenance import skill_provenance

    eps = [_FakeEp("e1", task_text="t")]
    skills = [Skill(id="x", provenance_episodes=["e1", "ghost"])]
    a = _FakeAgent(skills, eps)
    out = skill_provenance(skill_id="x", agent=a)
    assert "ghost" in out["missing"]


def test_payload_shape():
    from verimem.skill_provenance import skill_provenance

    out = skill_provenance(skill_id="x", agent=_FakeAgent([], []))
    for k in ("skill_id", "found", "episodes", "missing",
                "n_provenance_ids"):
        assert k in out
