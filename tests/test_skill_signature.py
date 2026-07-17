"""R47: Canonical skill signature for dedup detection."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Skill:
    id: str
    trigger: str = ""
    body: str = ""
    parent_skills: list[str] = field(default_factory=list)


def test_same_body_same_signature():
    from verimem.skill_signature import compute_signature
    s1 = _Skill("a", trigger="X", body="do X then Y")
    s2 = _Skill("b", trigger="X", body="do X then Y")
    assert compute_signature(s1) == compute_signature(s2)


def test_different_body_different_signature():
    from verimem.skill_signature import compute_signature
    s1 = _Skill("a", body="do X")
    s2 = _Skill("a", body="do Y")
    assert compute_signature(s1) != compute_signature(s2)


def test_whitespace_normalization():
    from verimem.skill_signature import compute_signature
    s1 = _Skill("a", body="do  X\n  then Y")
    s2 = _Skill("a", body="do X then Y")
    # Whitespace shouldn't matter
    assert compute_signature(s1) == compute_signature(s2)


def test_case_insensitive_trigger():
    from verimem.skill_signature import compute_signature
    s1 = _Skill("a", trigger="WordPress RCE", body="x")
    s2 = _Skill("b", trigger="wordpress rce", body="x")
    assert compute_signature(s1) == compute_signature(s2)


def test_find_duplicate_skills():
    from verimem.skill_signature import find_duplicate_skills
    skills = [
        _Skill("s1", body="exploit X"),
        _Skill("s2", body="exploit X"),
        _Skill("s3", body="completely different"),
    ]
    out = find_duplicate_skills(skills)
    assert len(out["duplicate_groups"]) == 1
    assert out["duplicate_groups"][0]["n_dupes"] == 2


def test_payload_shape():
    from verimem.skill_signature import find_duplicate_skills
    out = find_duplicate_skills([])
    for k in ("duplicate_groups", "n_skills_scanned"):
        assert k in out
