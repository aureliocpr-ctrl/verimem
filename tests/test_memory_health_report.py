"""R33: Comprehensive memory health report.

Single high-level metric + breakdown:
  - overall_score (0..100)
  - episodes health (success ratio)
  - skills health (promoted ratio + retired ratio)
  - facts health (avg confidence, stale ratio)
  - balance score (multi-agent)
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Ep:
    id: str
    outcome: str
    created_at: float = 0.0


@dataclass
class _Skill:
    id: str
    status: str = "candidate"


@dataclass
class _Fact:
    id: str
    confidence: float = 0.9
    created_at: float = 0.0
    topic: str = ""


def test_empty_returns_zero_score():
    from verimem.memory_health_report import generate_health_report
    out = generate_health_report(episodes=[], skills=[], facts=[])
    assert out["overall_score"] == 0
    assert "verdict" in out


def test_full_inputs_score_above_zero():
    from verimem.memory_health_report import generate_health_report
    now = time.time()
    eps = [_Ep(f"e{i}", "success", created_at=now - 86400) for i in range(10)]
    skills = (
        [_Skill(f"p{i}", "promoted") for i in range(3)]
        + [_Skill(f"c{i}", "candidate") for i in range(5)]
    )
    facts = [_Fact(f"f{i}", confidence=0.9, created_at=now - 86400 * 10) for i in range(5)]
    out = generate_health_report(episodes=eps, skills=skills, facts=facts)
    assert out["overall_score"] > 0


def test_payload_keys():
    from verimem.memory_health_report import generate_health_report
    out = generate_health_report(episodes=[], skills=[], facts=[])
    for k in ("overall_score", "verdict", "components", "recommendations"):
        assert k in out


def test_components_keys():
    from verimem.memory_health_report import generate_health_report
    out = generate_health_report(episodes=[], skills=[], facts=[])
    for k in ("episodes_score", "skills_score", "facts_score"):
        assert k in out["components"]


def test_verdict_classification():
    from verimem.memory_health_report import generate_health_report
    now = time.time()
    eps = [_Ep(f"e{i}", "success", created_at=now) for i in range(100)]
    skills = [_Skill(f"p{i}", "promoted") for i in range(20)]
    facts = [_Fact(f"f{i}", confidence=1.0, created_at=now) for i in range(50)]
    out = generate_health_report(episodes=eps, skills=skills, facts=facts)
    assert out["verdict"] in {"Healthy", "Acceptable", "Needs attention",
                              "Poor", "Empty"}


def test_recommendations_returned():
    from verimem.memory_health_report import generate_health_report
    out = generate_health_report(episodes=[], skills=[], facts=[])
    assert isinstance(out["recommendations"], list)
