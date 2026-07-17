"""FORGIA pezzo #221 — Wave 20: per-skill outcome distribution.

For each skill, count how often it appears in episodes broken down
by outcome (success / failure). Useful for:
  - "which skills produce failures even when promoted?"
  - "what's the empirical success rate of skill X across all uses?"
  - cross-checking the Beta-posterior fitness with raw data

Output: list of records with `n_episodes, n_success, n_failure,
success_rate`, sorted by `n_episodes` descending.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from verimem.skill import Skill


@dataclass
class _FakeEp:
    outcome: str = "success"
    skills_used: list[str] = field(default_factory=list)


def test_empty_returns_empty_list():
    from verimem.outcome_by_skill import outcomes_by_skill

    out = outcomes_by_skill([], [])
    assert out == []


def test_skill_never_used_zero_episodes():
    from verimem.outcome_by_skill import outcomes_by_skill

    skills = [Skill(id="never", name="unused")]
    eps = [_FakeEp("success", ["other"])]
    out = outcomes_by_skill(skills, eps)
    assert len(out) == 1
    assert out[0]["skill_id"] == "never"
    assert out[0]["n_episodes"] == 0
    assert out[0]["success_rate"] is None  # no data


def test_skill_only_successes():
    from verimem.outcome_by_skill import outcomes_by_skill

    skills = [Skill(id="x", name="x")]
    eps = [
        _FakeEp("success", ["x"]),
        _FakeEp("success", ["x"]),
        _FakeEp("success", ["x"]),
    ]
    out = outcomes_by_skill(skills, eps)
    rec = next(r for r in out if r["skill_id"] == "x")
    assert rec["n_success"] == 3
    assert rec["n_failure"] == 0
    assert rec["success_rate"] == 1.0


def test_skill_mixed_outcomes():
    from verimem.outcome_by_skill import outcomes_by_skill

    skills = [Skill(id="x", name="x")]
    eps = [
        _FakeEp("success", ["x"]),
        _FakeEp("success", ["x"]),
        _FakeEp("failure", ["x"]),
        _FakeEp("failure", ["x"]),
    ]
    out = outcomes_by_skill(skills, eps)
    rec = next(r for r in out if r["skill_id"] == "x")
    assert rec["n_success"] == 2
    assert rec["n_failure"] == 2
    assert abs(rec["success_rate"] - 0.5) < 1e-9


def test_sorted_by_n_episodes_desc():
    from verimem.outcome_by_skill import outcomes_by_skill

    skills = [
        Skill(id="hi", name="hi"),
        Skill(id="lo", name="lo"),
    ]
    eps = [
        _FakeEp("success", ["hi"]),
        _FakeEp("success", ["hi"]),
        _FakeEp("success", ["hi"]),
        _FakeEp("success", ["lo"]),
    ]
    out = outcomes_by_skill(skills, eps)
    assert out[0]["skill_id"] == "hi"
    assert out[1]["skill_id"] == "lo"


def test_top_k_respected():
    from verimem.outcome_by_skill import outcomes_by_skill

    skills = [Skill(id=f"s{i}", name=f"s{i}") for i in range(10)]
    eps = [_FakeEp("success", [f"s{i}"]) for i in range(10)]
    out = outcomes_by_skill(skills, eps, top_k=3)
    assert len(out) == 3


def test_payload_shape_complete():
    from verimem.outcome_by_skill import outcomes_by_skill

    skills = [Skill(id="x", name="x")]
    eps = [_FakeEp("success", ["x"])]
    out = outcomes_by_skill(skills, eps)
    rec = out[0]
    for k in ("skill_id", "name", "n_episodes",
                "n_success", "n_failure", "success_rate"):
        assert k in rec


def test_skill_in_multiple_episodes_counted_once_per_episode():
    """If skill appears multiple times in same episode (retry pattern),
    we still count one outcome per episode (not per appearance)."""
    from verimem.outcome_by_skill import outcomes_by_skill

    skills = [Skill(id="x", name="x")]
    eps = [
        _FakeEp("success", ["x", "x", "x"]),
    ]
    out = outcomes_by_skill(skills, eps)
    rec = out[0]
    assert rec["n_episodes"] == 1
    assert rec["n_success"] == 1
