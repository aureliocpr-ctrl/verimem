"""FORGIA pezzo #273 — Wave 72: last N skills by created_at."""
from __future__ import annotations

from verimem.skill import Skill


def test_empty():
    from verimem.skill_recent import skills_recent

    out = skills_recent([])
    assert out["skills"] == []


def test_newest_first():
    from verimem.skill_recent import skills_recent

    skills = [
        Skill(id="old", created_at=100.0),
        Skill(id="new", created_at=300.0),
        Skill(id="mid", created_at=200.0),
    ]
    out = skills_recent(skills)
    ids = [s["id"] for s in out["skills"]]
    assert ids == ["new", "mid", "old"]


def test_top_k():
    from verimem.skill_recent import skills_recent

    skills = [Skill(id=f"s{i}", created_at=float(i)) for i in range(10)]
    out = skills_recent(skills, top_k=3)
    assert len(out["skills"]) == 3


def test_status_filter():
    from verimem.skill_recent import skills_recent

    skills = [
        Skill(id="c", status="candidate", created_at=100),
        Skill(id="p", status="promoted", created_at=200),
    ]
    out = skills_recent(skills, status="promoted")
    assert [s["id"] for s in out["skills"]] == ["p"]


def test_payload_shape():
    from verimem.skill_recent import skills_recent

    out = skills_recent([])
    for k in ("skills", "n_total"):
        assert k in out
