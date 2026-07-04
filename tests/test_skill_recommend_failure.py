"""R41: For a failure episode, recommend alternative skills.

Given a failed episode + the skills it used, find OTHER skills with
similar trigger but NOT used in the failure → candidates to try next.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str
    skills_used: list[str] = field(default_factory=list)


@dataclass
class _Skill:
    id: str
    trigger: str = ""
    status: str = "promoted"


def test_empty_returns_no_recommendation():
    from engram.skill_recommend_failure import recommend_alternatives
    target = _Ep("f", "task", "failure", [])
    out = recommend_alternatives(target, skills=[])
    assert out["recommendations"] == []


def test_recommends_unused_matching_skill():
    from engram.skill_recommend_failure import recommend_alternatives
    target = _Ep("f", "WordPress RCE acme.io", "failure",
                 skills_used=["bad_skill"])
    skills = [
        _Skill("bad_skill", trigger="WordPress RCE"),
        _Skill("alt_skill", trigger="WordPress RCE alternative"),
        _Skill("unrelated", trigger="firmware fuzz"),
    ]
    out = recommend_alternatives(target, skills=skills)
    ids = [r["skill_id"] for r in out["recommendations"]]
    assert "alt_skill" in ids
    assert "bad_skill" not in ids
    assert "unrelated" not in ids


def test_no_match_returns_empty():
    from engram.skill_recommend_failure import recommend_alternatives
    target = _Ep("f", "novel task", "failure", [])
    skills = [_Skill("x", trigger="completely different")]
    out = recommend_alternatives(target, skills=skills)
    assert out["recommendations"] == []


def test_retired_excluded():
    from engram.skill_recommend_failure import recommend_alternatives
    target = _Ep("f", "WordPress RCE", "failure", [])
    skills = [_Skill("dead", trigger="WordPress RCE", status="retired")]
    out = recommend_alternatives(target, skills=skills)
    assert out["recommendations"] == []


def test_payload_shape():
    from engram.skill_recommend_failure import recommend_alternatives
    target = _Ep("f", "x", "failure", [])
    out = recommend_alternatives(target, skills=[])
    for k in ("recommendations", "n_skills_scanned"):
        assert k in out


def test_entry_keys():
    from engram.skill_recommend_failure import recommend_alternatives
    target = _Ep("f", "X", "failure", [])
    skills = [_Skill("s1", trigger="X")]
    out = recommend_alternatives(target, skills=skills)
    if out["recommendations"]:
        for k in ("skill_id", "match_score"):
            assert k in out["recommendations"][0]
