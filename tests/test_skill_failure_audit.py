"""FORGIA pezzo #231 — Wave 30: per-skill failure audit.

For a target skill, returns the episodes where it was used AND the
outcome was failure. Useful debugging tool: "perché questo skill
sta fallendo?".
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _FakeEp:
    id: str
    task_text: str = ""
    outcome: str = "success"
    created_at: float = 0.0
    skills_used: list[str] = field(default_factory=list)


def test_empty_returns_empty_list():
    from engram.skill_failure_audit import skill_failure_audit

    out = skill_failure_audit(skill_id="x", episodes=[])
    assert out["failures"] == []
    assert out["n_total_uses"] == 0


def test_only_failures_returned():
    from engram.skill_failure_audit import skill_failure_audit

    eps = [
        _FakeEp("e1", "task1", outcome="success", skills_used=["x"]),
        _FakeEp("e2", "task2", outcome="failure", skills_used=["x"]),
        _FakeEp("e3", "task3", outcome="failure", skills_used=["x"]),
        _FakeEp("e4", "task4", outcome="failure", skills_used=["other"]),
    ]
    out = skill_failure_audit(skill_id="x", episodes=eps)
    ids = [e["id"] for e in out["failures"]]
    assert "e2" in ids
    assert "e3" in ids
    assert "e1" not in ids  # was success
    assert "e4" not in ids  # didn't use x


def test_n_total_uses_correct():
    from engram.skill_failure_audit import skill_failure_audit

    eps = [
        _FakeEp("e1", "task1", outcome="success", skills_used=["x"]),
        _FakeEp("e2", "task2", outcome="failure", skills_used=["x"]),
        _FakeEp("e3", "task3", outcome="success", skills_used=["other"]),
    ]
    out = skill_failure_audit(skill_id="x", episodes=eps)
    assert out["n_total_uses"] == 2
    assert out["n_failures"] == 1


def test_sorted_recent_first():
    from engram.skill_failure_audit import skill_failure_audit

    eps = [
        _FakeEp("old", outcome="failure", created_at=100.0,
                skills_used=["x"]),
        _FakeEp("new", outcome="failure", created_at=300.0,
                skills_used=["x"]),
    ]
    out = skill_failure_audit(skill_id="x", episodes=eps)
    ids = [e["id"] for e in out["failures"]]
    assert ids == ["new", "old"]


def test_top_k_respected():
    from engram.skill_failure_audit import skill_failure_audit

    eps = [
        _FakeEp(f"e{i}", outcome="failure", created_at=float(i),
                skills_used=["x"])
        for i in range(10)
    ]
    out = skill_failure_audit(skill_id="x", episodes=eps, top_k=3)
    assert len(out["failures"]) == 3


def test_payload_shape_complete():
    from engram.skill_failure_audit import skill_failure_audit

    out = skill_failure_audit(skill_id="x", episodes=[])
    for k in ("skill_id", "n_total_uses", "n_failures",
                "failure_rate", "failures"):
        assert k in out
