"""R19: Success factor analysis — quale skill correlato con outcome.

Per ogni skill che appare in episodi, calcola success_rate quando
quella skill è presente. Skill con success_rate alto + n alto =
"high value" skill.

Pure-local, no LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Ep:
    id: str
    outcome: str
    skills_used: list[str] = field(default_factory=list)


def test_empty_returns_empty():
    from verimem.success_factor import analyze_success_factors

    out = analyze_success_factors([])
    assert out["factors"] == []


def test_skill_with_high_success():
    from verimem.success_factor import analyze_success_factors

    eps = [
        _Ep("e1", "success", ["skill_winner"]),
        _Ep("e2", "success", ["skill_winner"]),
        _Ep("e3", "success", ["skill_winner"]),
        _Ep("e4", "failure", ["skill_loser"]),
        _Ep("e5", "failure", ["skill_loser"]),
    ]
    out = analyze_success_factors(eps, min_uses=2)
    factors = {f["skill_id"]: f for f in out["factors"]}
    assert factors["skill_winner"]["success_rate"] == 1.0
    assert factors["skill_loser"]["success_rate"] == 0.0


def test_skill_below_min_uses_excluded():
    from verimem.success_factor import analyze_success_factors

    eps = [_Ep("e1", "success", ["rare_skill"])]
    out = analyze_success_factors(eps, min_uses=2)
    factor_ids = [f["skill_id"] for f in out["factors"]]
    assert "rare_skill" not in factor_ids


def test_sorting_by_success_rate_desc():
    from verimem.success_factor import analyze_success_factors

    eps = (
        [_Ep(f"s{i}", "success", ["hi"]) for i in range(8)]
        + [_Ep("fs", "failure", ["hi"])]
        + [_Ep(f"m{i}", "success", ["mid"]) for i in range(3)]
        + [_Ep(f"fm{i}", "failure", ["mid"]) for i in range(3)]
        + [_Ep(f"l{i}", "failure", ["lo"]) for i in range(4)]
    )
    out = analyze_success_factors(eps, min_uses=2)
    rates = [f["success_rate"] for f in out["factors"]]
    # First skill rate >= subsequent
    for i in range(len(rates) - 1):
        assert rates[i] >= rates[i + 1]


def test_payload_keys():
    from verimem.success_factor import analyze_success_factors
    out = analyze_success_factors([])
    for k in ("factors", "n_episodes_scanned", "n_unique_skills"):
        assert k in out


def test_factor_entry_keys():
    from verimem.success_factor import analyze_success_factors
    eps = [_Ep("e", "success", ["s1"]), _Ep("e2", "success", ["s1"])]
    out = analyze_success_factors(eps, min_uses=1)
    if out["factors"]:
        for k in ("skill_id", "n_uses", "n_success", "success_rate"):
            assert k in out["factors"][0]
