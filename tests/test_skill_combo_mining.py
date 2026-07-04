"""R26: Skill combo mining — pairs frequently used together.

For each pair of skills, count co-occurrences in episodes.skills_used.
Pairs above min_cooccurrence threshold are candidates for super-skill
compilation.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Ep:
    id: str
    skills_used: list[str] = field(default_factory=list)
    outcome: str = "success"


def test_empty_returns_no_combos():
    from engram.skill_combo_mining import mine_skill_combos
    out = mine_skill_combos([])
    assert out["combos"] == []


def test_pair_co_occurs():
    from engram.skill_combo_mining import mine_skill_combos
    eps = [
        _Ep("e1", ["a", "b"]),
        _Ep("e2", ["a", "b"]),
        _Ep("e3", ["a", "b"]),
    ]
    out = mine_skill_combos(eps, min_cooccurrence=2)
    pairs = [tuple(sorted(c["pair"])) for c in out["combos"]]
    assert ("a", "b") in pairs


def test_singleton_excluded():
    from engram.skill_combo_mining import mine_skill_combos
    eps = [_Ep(f"e{i}", ["only_one"]) for i in range(5)]
    out = mine_skill_combos(eps, min_cooccurrence=2)
    assert out["combos"] == []


def test_min_cooccurrence_filter():
    from engram.skill_combo_mining import mine_skill_combos
    eps = [_Ep("e1", ["a", "b"])]  # only 1 occurrence
    out = mine_skill_combos(eps, min_cooccurrence=3)
    assert out["combos"] == []


def test_success_rate_per_pair():
    from engram.skill_combo_mining import mine_skill_combos
    eps = [
        _Ep("s1", ["a", "b"], outcome="success"),
        _Ep("s2", ["a", "b"], outcome="success"),
        _Ep("f1", ["a", "b"], outcome="failure"),
    ]
    out = mine_skill_combos(eps, min_cooccurrence=2)
    if out["combos"]:
        c = out["combos"][0]
        # 2 success of 3 = 0.67
        assert 0.5 <= c["success_rate"] <= 0.9


def test_payload_shape():
    from engram.skill_combo_mining import mine_skill_combos
    out = mine_skill_combos([])
    for k in ("combos", "n_episodes_scanned"):
        assert k in out


def test_entry_keys():
    from engram.skill_combo_mining import mine_skill_combos
    eps = [_Ep(f"e{i}", ["a", "b"]) for i in range(3)]
    out = mine_skill_combos(eps, min_cooccurrence=2)
    if out["combos"]:
        for k in ("pair", "count", "success_rate"):
            assert k in out["combos"][0]
