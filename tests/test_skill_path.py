"""FORGIA pezzo #234 — Wave 33: per-skill path analysis.

For target skill X, returns:
  - predecessors: which skills tend to come BEFORE X
  - successors: which skills tend to come AFTER X

Both with absolute counts and fractions of X's total appearances.
A more focused, per-skill view of the transition statistics.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _FakeEp:
    skills_used: list[str] = field(default_factory=list)


def test_empty_returns_empty_path():
    from engram.skill_path import skill_path

    out = skill_path(skill_id="x", episodes=[])
    assert out["n_total_appearances"] == 0
    assert out["predecessors"] == []
    assert out["successors"] == []


def test_skill_never_seen():
    from engram.skill_path import skill_path

    eps = [_FakeEp(["A", "B"]), _FakeEp(["C"])]
    out = skill_path(skill_id="Z", episodes=eps)
    assert out["n_total_appearances"] == 0


def test_predecessors_ranked():
    from engram.skill_path import skill_path

    eps = [
        _FakeEp(["A", "X"]),
        _FakeEp(["A", "X"]),
        _FakeEp(["A", "X"]),
        _FakeEp(["B", "X"]),
    ]
    out = skill_path(skill_id="X", episodes=eps)
    # A appears 3 times, B 1 time as predecessor of X.
    pre_ids = [p["skill_id"] for p in out["predecessors"]]
    assert pre_ids[0] == "A"
    assert "B" in pre_ids


def test_successors_ranked():
    from engram.skill_path import skill_path

    eps = [
        _FakeEp(["X", "Y"]),
        _FakeEp(["X", "Y"]),
        _FakeEp(["X", "Z"]),
    ]
    out = skill_path(skill_id="X", episodes=eps)
    suc_ids = [s["skill_id"] for s in out["successors"]]
    assert suc_ids[0] == "Y"  # 2 occurrences
    assert "Z" in suc_ids


def test_first_in_chain_no_predecessors():
    from engram.skill_path import skill_path

    eps = [_FakeEp(["X", "Y"]), _FakeEp(["X"])]
    out = skill_path(skill_id="X", episodes=eps)
    assert out["predecessors"] == []


def test_last_in_chain_no_successors():
    from engram.skill_path import skill_path

    eps = [_FakeEp(["A", "X"]), _FakeEp(["B", "X"])]
    out = skill_path(skill_id="X", episodes=eps)
    assert out["successors"] == []


def test_fraction_correct():
    from engram.skill_path import skill_path

    eps = [
        _FakeEp(["A", "X"]),
        _FakeEp(["A", "X"]),
        _FakeEp(["B", "X"]),
        _FakeEp(["B", "X"]),
    ]
    # X appears 4 times. A predeces 2/4 = 0.5, B 2/4 = 0.5.
    out = skill_path(skill_id="X", episodes=eps)
    for pre in out["predecessors"]:
        assert abs(pre["fraction"] - 0.5) < 1e-9


def test_top_k_respected():
    from engram.skill_path import skill_path

    eps = [
        _FakeEp([letter, "X"]) for letter in "ABCDEFGH"
    ]
    out = skill_path(skill_id="X", episodes=eps, top_k=3)
    assert len(out["predecessors"]) == 3


def test_payload_shape_complete():
    from engram.skill_path import skill_path

    out = skill_path(skill_id="x", episodes=[])
    for k in ("skill_id", "n_total_appearances",
                "predecessors", "successors"):
        assert k in out
