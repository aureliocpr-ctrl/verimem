"""FORGIA pezzo #274 — Wave 73: top used skills by episode count."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _FakeEp:
    skills_used: list[str] = field(default_factory=list)


def test_empty():
    from verimem.skills_top_used import top_used_skills

    out = top_used_skills(episodes=[])
    assert out["skills"] == []


def test_ranks_by_use_count():
    from verimem.skills_top_used import top_used_skills

    eps = [
        _FakeEp(["a", "b"]),
        _FakeEp(["a"]),
        _FakeEp(["a", "c"]),
    ]
    out = top_used_skills(episodes=eps)
    ids = [s["skill_id"] for s in out["skills"]]
    assert ids[0] == "a"


def test_counts_episodes_not_appearances():
    """Counted as 1 per episode even if skill listed multiple times."""
    from verimem.skills_top_used import top_used_skills

    eps = [_FakeEp(["a", "a", "a"])]
    out = top_used_skills(episodes=eps)
    a_record = next(s for s in out["skills"] if s["skill_id"] == "a")
    assert a_record["n_episodes"] == 1


def test_top_k():
    from verimem.skills_top_used import top_used_skills

    eps = [_FakeEp([f"s{i}"]) for i in range(10)]
    out = top_used_skills(episodes=eps, top_k=3)
    assert len(out["skills"]) == 3


def test_payload_shape():
    from verimem.skills_top_used import top_used_skills

    out = top_used_skills(episodes=[])
    for k in ("skills", "n_unique_skills"):
        assert k in out
