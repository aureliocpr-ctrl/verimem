"""R50: Skill chain complexity = total skills needed to execute it
(self + all ancestors recursively)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Skill:
    id: str
    parent_skills: list[str] = field(default_factory=list)


def test_root_complexity_is_1():
    from engram.chain_complexity import compute_complexity
    skills = [_Skill("root")]
    out = compute_complexity("root", skills)
    assert out["complexity"] == 1


def test_chain_3_layers():
    from engram.chain_complexity import compute_complexity
    skills = [
        _Skill("a"),
        _Skill("b", parent_skills=["a"]),
        _Skill("c", parent_skills=["b"]),
    ]
    out = compute_complexity("c", skills)
    # c + b + a = 3
    assert out["complexity"] == 3


def test_diamond_dedup():
    from engram.chain_complexity import compute_complexity
    skills = [
        _Skill("root"),
        _Skill("a", parent_skills=["root"]),
        _Skill("b", parent_skills=["root"]),
        _Skill("c", parent_skills=["a", "b"]),
    ]
    out = compute_complexity("c", skills)
    # c, a, b, root = 4 (no double-count of root)
    assert out["complexity"] == 4


def test_missing_skill_returns_zero():
    from engram.chain_complexity import compute_complexity
    out = compute_complexity("ghost", [_Skill("real")])
    assert out["complexity"] == 0


def test_cycle_safe():
    from engram.chain_complexity import compute_complexity
    skills = [
        _Skill("a", parent_skills=["b"]),
        _Skill("b", parent_skills=["a"]),
    ]
    # Cyclical references shouldn't loop forever
    out = compute_complexity("a", skills)
    assert out["complexity"] >= 1


def test_payload_shape():
    from engram.chain_complexity import compute_complexity
    out = compute_complexity("x", [])
    for k in ("complexity", "ancestor_ids"):
        assert k in out
