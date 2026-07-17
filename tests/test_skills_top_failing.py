"""FORGIA pezzo #266 — Wave 65: top failing skills batch."""
from __future__ import annotations

from dataclasses import dataclass, field

from verimem.skill import Skill


@dataclass
class _FakeEp:
    outcome: str = "success"
    skills_used: list[str] = field(default_factory=list)


def test_empty():
    from verimem.skills_top_failing import top_failing_skills

    out = top_failing_skills(skills=[], episodes=[])
    assert out["skills"] == []


def test_ranks_by_failure_count():
    from verimem.skills_top_failing import top_failing_skills

    skills = [Skill(id="a"), Skill(id="b")]
    eps = [
        _FakeEp("failure", ["a"]),
        _FakeEp("failure", ["a"]),
        _FakeEp("failure", ["b"]),
    ]
    out = top_failing_skills(skills=skills, episodes=eps)
    ids = [s["skill_id"] for s in out["skills"]]
    assert ids[0] == "a"


def test_excludes_no_failures():
    from verimem.skills_top_failing import top_failing_skills

    skills = [Skill(id="a"), Skill(id="b")]
    eps = [
        _FakeEp("success", ["a"]),
        _FakeEp("failure", ["b"]),
    ]
    out = top_failing_skills(skills=skills, episodes=eps)
    ids = [s["skill_id"] for s in out["skills"]]
    assert "a" not in ids
    assert "b" in ids


def test_top_k():
    from verimem.skills_top_failing import top_failing_skills

    skills = [Skill(id=f"s{i}") for i in range(10)]
    eps = [_FakeEp("failure", [f"s{i}"]) for i in range(10)]
    out = top_failing_skills(skills=skills, episodes=eps, top_k=3)
    assert len(out["skills"]) == 3
