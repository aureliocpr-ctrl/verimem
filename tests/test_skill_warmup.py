"""R24: Skill warmup — predict which skills will be needed for upcoming tasks.

Given a list of upcoming tasks, score skills by aggregate match score.
Return ranked skills to "preload" (keep warm in attention/cache).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Skill:
    id: str
    trigger: str = ""
    status: str = "promoted"
    parent_skills: list[str] = field(default_factory=list)


def test_empty_returns_empty():
    from verimem.skill_warmup import predict_warmup_skills
    out = predict_warmup_skills(upcoming_tasks=[], skills=[])
    assert out["warmup"] == []


def test_warmup_picks_matching_skills():
    from verimem.skill_warmup import predict_warmup_skills
    skills = [
        _Skill("recon", trigger="WordPress fingerprint detection"),
        _Skill("exploit", trigger="WordPress RCE exploit"),
        _Skill("unrelated", trigger="firmware ARM buffer overflow"),
    ]
    upcoming = [
        "WordPress fingerprint task",
        "WordPress RCE attack",
    ]
    out = predict_warmup_skills(upcoming_tasks=upcoming, skills=skills)
    ids = [s["skill_id"] for s in out["warmup"]]
    assert "recon" in ids or "exploit" in ids
    assert "unrelated" not in ids


def test_aggregate_score_across_tasks():
    from verimem.skill_warmup import predict_warmup_skills
    skills = [
        _Skill("common", trigger="WordPress general purpose"),
        _Skill("specific", trigger="firmware ARM"),
    ]
    # 3 tasks about WordPress → common gets high aggregate
    upcoming = ["WordPress task A", "WordPress task B", "WordPress task C"]
    out = predict_warmup_skills(upcoming_tasks=upcoming, skills=skills)
    if out["warmup"]:
        assert out["warmup"][0]["skill_id"] == "common"


def test_retired_excluded():
    from verimem.skill_warmup import predict_warmup_skills
    skills = [
        _Skill("active", trigger="WordPress RCE", status="promoted"),
        _Skill("dead", trigger="WordPress RCE", status="retired"),
    ]
    out = predict_warmup_skills(
        upcoming_tasks=["WordPress RCE"], skills=skills,
    )
    ids = [s["skill_id"] for s in out["warmup"]]
    assert "dead" not in ids


def test_payload_shape():
    from verimem.skill_warmup import predict_warmup_skills
    out = predict_warmup_skills(upcoming_tasks=[], skills=[])
    for k in ("warmup", "n_skills_scanned", "n_tasks"):
        assert k in out


def test_entry_keys():
    from verimem.skill_warmup import predict_warmup_skills
    skills = [_Skill("s1", trigger="WordPress")]
    out = predict_warmup_skills(upcoming_tasks=["WordPress task"],
                                skills=skills)
    if out["warmup"]:
        for k in ("skill_id", "score"):
            assert k in out["warmup"][0]
