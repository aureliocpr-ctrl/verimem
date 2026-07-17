"""FORGIA pezzo #262 — Wave 61: filter episodes by skill+outcome.

Filter episodes that include a target skill in skills_used, with
optional outcome filter. Companion to existing episodes_by_skill
but with outcome filter for diagnostic flows.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class _FakeEp:
    id: str = ""
    task_text: str = ""
    outcome: str = "success"
    skills_used: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


def test_empty_returns_empty():
    from verimem.episodes_with_skill import episodes_with_skill

    out = episodes_with_skill(skill_id="x", episodes=[])
    assert out["episodes"] == []
    assert out["n_total"] == 0


def test_skill_not_in_any_episode():
    from verimem.episodes_with_skill import episodes_with_skill

    eps = [
        _FakeEp("e1", skills_used=["a"]),
        _FakeEp("e2", skills_used=["b"]),
    ]
    out = episodes_with_skill(skill_id="ZZZ", episodes=eps)
    assert out["episodes"] == []


def test_filter_includes_skill():
    from verimem.episodes_with_skill import episodes_with_skill

    eps = [
        _FakeEp("e1", skills_used=["a", "b"]),
        _FakeEp("e2", skills_used=["c"]),
        _FakeEp("e3", skills_used=["a"]),
    ]
    out = episodes_with_skill(skill_id="a", episodes=eps)
    ids = [e["id"] for e in out["episodes"]]
    assert "e1" in ids
    assert "e3" in ids
    assert "e2" not in ids


def test_outcome_filter():
    from verimem.episodes_with_skill import episodes_with_skill

    eps = [
        _FakeEp("e1", outcome="success", skills_used=["x"]),
        _FakeEp("e2", outcome="failure", skills_used=["x"]),
    ]
    out_succ = episodes_with_skill(
        skill_id="x", episodes=eps, outcome="success",
    )
    assert [e["id"] for e in out_succ["episodes"]] == ["e1"]

    out_fail = episodes_with_skill(
        skill_id="x", episodes=eps, outcome="failure",
    )
    assert [e["id"] for e in out_fail["episodes"]] == ["e2"]


def test_sorted_recent_first():
    from verimem.episodes_with_skill import episodes_with_skill

    eps = [
        _FakeEp("old", skills_used=["x"], created_at=100.0),
        _FakeEp("new", skills_used=["x"], created_at=200.0),
    ]
    out = episodes_with_skill(skill_id="x", episodes=eps)
    assert [e["id"] for e in out["episodes"]] == ["new", "old"]


def test_top_k_respected():
    from verimem.episodes_with_skill import episodes_with_skill

    eps = [_FakeEp(f"e{i}", skills_used=["x"]) for i in range(10)]
    out = episodes_with_skill(skill_id="x", episodes=eps, top_k=3)
    assert len(out["episodes"]) == 3


def test_payload_shape_complete():
    from verimem.episodes_with_skill import episodes_with_skill

    out = episodes_with_skill(skill_id="x", episodes=[])
    for k in ("skill_id", "n_total", "episodes",
                "n_success", "n_failure"):
        assert k in out
