"""R20: Find skill bottlenecks.

A "bottleneck" skill: has many children that are stuck as candidates,
AND has low fitness itself. Promoting/fixing it unlocks downstream.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Skill:
    id: str
    name: str = "n"
    parent_skills: list[str] = field(default_factory=list)
    trials: int = 0
    successes: int = 0
    status: str = "candidate"


def test_empty_returns_no_bottlenecks():
    from verimem.skill_bottleneck import find_bottlenecks
    out = find_bottlenecks([])
    assert out["bottlenecks"] == []


def test_finds_low_fitness_with_many_children():
    from verimem.skill_bottleneck import find_bottlenecks
    skills = [
        _Skill("root", trials=10, successes=3, status="candidate"),
        _Skill("c1", parent_skills=["root"], status="candidate",
               trials=5, successes=1),
        _Skill("c2", parent_skills=["root"], status="candidate",
               trials=5, successes=1),
        _Skill("c3", parent_skills=["root"], status="candidate",
               trials=5, successes=1),
    ]
    out = find_bottlenecks(skills, min_blocked_children=2,
                           max_fitness_threshold=0.5)
    ids = [b["skill_id"] for b in out["bottlenecks"]]
    assert "root" in ids


def test_skip_when_already_promoted():
    from verimem.skill_bottleneck import find_bottlenecks
    skills = [
        _Skill("root", trials=10, successes=3, status="promoted"),
        _Skill("c1", parent_skills=["root"], status="candidate",
               trials=5, successes=1),
        _Skill("c2", parent_skills=["root"], status="candidate",
               trials=5, successes=1),
    ]
    out = find_bottlenecks(skills)
    ids = [b["skill_id"] for b in out["bottlenecks"]]
    # Already promoted, not a bottleneck (children waiting for OTHER reason)
    assert "root" not in ids


def test_no_bottleneck_when_children_few():
    from verimem.skill_bottleneck import find_bottlenecks
    skills = [
        _Skill("root", trials=10, successes=3, status="candidate"),
        _Skill("c1", parent_skills=["root"], status="candidate",
               trials=5, successes=1),
    ]
    out = find_bottlenecks(skills, min_blocked_children=5)
    assert out["bottlenecks"] == []


def test_payload_shape():
    from verimem.skill_bottleneck import find_bottlenecks
    out = find_bottlenecks([])
    for k in ("bottlenecks", "n_total_skills"):
        assert k in out


def test_entry_keys():
    from verimem.skill_bottleneck import find_bottlenecks
    skills = [
        _Skill("root", trials=10, successes=2, status="candidate"),
        _Skill("c1", parent_skills=["root"], status="candidate"),
        _Skill("c2", parent_skills=["root"], status="candidate"),
        _Skill("c3", parent_skills=["root"], status="candidate"),
    ]
    out = find_bottlenecks(skills, min_blocked_children=2)
    if out["bottlenecks"]:
        for k in ("skill_id", "fitness", "n_blocked_children",
                  "blocked_child_ids"):
            assert k in out["bottlenecks"][0]
