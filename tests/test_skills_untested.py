"""FORGIA pezzo #265 — Wave 64: find untested skills (trials==0)."""
from __future__ import annotations

from engram.skill import Skill


def test_empty_returns_empty():
    from engram.skills_untested import find_untested_skills

    out = find_untested_skills([])
    assert out["skills"] == []
    assert out["n_total"] == 0


def test_finds_zero_trials():
    from engram.skills_untested import find_untested_skills

    skills = [
        Skill(id="new", trials=0, successes=0),
        Skill(id="tested", trials=5, successes=3),
    ]
    out = find_untested_skills(skills)
    ids = [s["id"] for s in out["skills"]]
    assert ids == ["new"]


def test_status_filter():
    from engram.skills_untested import find_untested_skills

    skills = [
        Skill(id="c", trials=0, status="candidate"),
        Skill(id="p", trials=0, status="promoted"),
    ]
    out = find_untested_skills(skills, status="candidate")
    assert [s["id"] for s in out["skills"]] == ["c"]


def test_payload_shape():
    from engram.skills_untested import find_untested_skills

    out = find_untested_skills([])
    assert "skills" in out and "n_total" in out
