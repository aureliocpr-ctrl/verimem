"""FORGIA pezzo #236 — Wave 35: per-skill deep inspect.

Orchestrator: takes one skill_id and returns EVERYTHING the user
might want to know about it in a single call:
  - basic fields (name, status, trials, etc)
  - health diagnostic + suggested_action
  - path (predecessors + successors)
  - failure audit
  - structural analogues
  - n_episodes_used

For debug ("perché questo skill si comporta così?") and curation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from verimem.skill import Skill


@dataclass
class _FakeEp:
    id: str = ""
    task_text: str = ""
    outcome: str = "success"
    created_at: float = 0.0
    skills_used: list[str] = field(default_factory=list)


class _FakeSkillsStore:
    def __init__(self, skills: list[Skill]) -> None:
        self._by_id = {s.id: s for s in skills}

    def get(self, sid: str) -> Skill | None:
        return self._by_id.get(sid)

    def all(self, status: str | None = None) -> list[Skill]:
        return list(self._by_id.values())


class _FakeMemory:
    def __init__(self, eps: list[_FakeEp]) -> None:
        self._eps = eps

    def all(self, limit: int | None = None) -> list[_FakeEp]:
        return list(self._eps if limit is None else self._eps[:limit])


class _FakeAgent:
    def __init__(self, skills: list[Skill], eps: list[_FakeEp]) -> None:
        self.skills = _FakeSkillsStore(skills)
        self.memory = _FakeMemory(eps)


def test_unknown_skill_returns_not_found():
    from verimem.skill_inspect import skill_inspect

    a = _FakeAgent([], [])
    out = skill_inspect(skill_id="ZZZ", agent=a)
    assert out["found"] is False


def test_known_skill_full_payload():
    from verimem.skill_inspect import skill_inspect

    target = Skill(
        id="T", name="target_skill", trials=10, successes=8,
        status="promoted",
    )
    a = _FakeAgent([target], [])
    out = skill_inspect(skill_id="T", agent=a)
    assert out["found"] is True
    # All sections present.
    for k in ("basic", "health", "path", "failure_audit",
                "analogues"):
        assert k in out


def test_basic_fields_returned():
    from verimem.skill_inspect import skill_inspect

    s = Skill(id="T", name="target_skill", trials=5, successes=4,
              status="candidate")
    a = _FakeAgent([s], [])
    out = skill_inspect(skill_id="T", agent=a)
    assert out["basic"]["id"] == "T"
    assert out["basic"]["name"] == "target_skill"
    assert out["basic"]["status"] == "candidate"
    assert out["basic"]["trials"] == 5


def test_health_section_present():
    from verimem.skill_inspect import skill_inspect

    s = Skill(id="T", name="t", trials=0, successes=0)
    a = _FakeAgent([s], [])
    out = skill_inspect(skill_id="T", agent=a)
    assert "suggested_action" in out["health"]


def test_path_section_present():
    from verimem.skill_inspect import skill_inspect

    s = Skill(id="T", name="t")
    a = _FakeAgent([s], [_FakeEp(skills_used=["A", "T", "B"])])
    out = skill_inspect(skill_id="T", agent=a)
    assert "predecessors" in out["path"]
    assert "successors" in out["path"]


def test_failure_audit_section_present():
    from verimem.skill_inspect import skill_inspect

    s = Skill(id="T", name="t")
    eps = [_FakeEp(id="e1", outcome="failure", skills_used=["T"])]
    a = _FakeAgent([s], eps)
    out = skill_inspect(skill_id="T", agent=a)
    assert out["failure_audit"]["n_failures"] == 1
