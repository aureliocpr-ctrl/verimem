"""R31: Oracle query — combine all memory tiers into one answer.

Single call returning episodes + facts + skills relevant to a query.
Plus aggregated confidence verdict (from metacognition).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str
    final_answer: str = ""
    created_at: float = 0.0


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = ""
    confidence: float = 0.9


@dataclass
class _Skill:
    id: str
    name: str = ""
    trigger: str = ""
    status: str = "promoted"


def test_empty_returns_empty_answer():
    from verimem.oracle import oracle_query
    out = oracle_query(query="x", episodes=[], facts=[], skills=[])
    for k in ("episodes", "facts", "skills"):
        assert out[k] == []


def test_finds_relevant_episodes():
    from verimem.oracle import oracle_query
    eps = [
        _Ep("e1", "WordPress RCE on acme.io", "success"),
        _Ep("e2", "Linux kernel update", "success"),
    ]
    out = oracle_query(query="WordPress RCE", episodes=eps,
                       facts=[], skills=[])
    ids = [e["id"] for e in out["episodes"]]
    assert "e1" in ids


def test_finds_relevant_facts():
    from verimem.oracle import oracle_query
    facts = [
        _Fact("f1", "WordPress 5.8 vulnerable to CVE-X"),
        _Fact("f2", "Aurelio prefers TypeScript"),
    ]
    out = oracle_query(query="WordPress CVE", episodes=[],
                       facts=facts, skills=[])
    ids = [f["id"] for f in out["facts"]]
    assert "f1" in ids


def test_finds_relevant_skills():
    from verimem.oracle import oracle_query
    skills = [
        _Skill("s1", trigger="WordPress RCE exploit"),
        _Skill("s2", trigger="firmware fuzzing"),
    ]
    out = oracle_query(query="WordPress RCE", episodes=[],
                       facts=[], skills=skills)
    ids = [s["id"] for s in out["skills"]]
    assert "s1" in ids


def test_confidence_aggregated():
    from verimem.oracle import oracle_query
    out = oracle_query(query="x", episodes=[], facts=[], skills=[])
    assert "confidence" in out


def test_payload_shape():
    from verimem.oracle import oracle_query
    out = oracle_query(query="x", episodes=[], facts=[], skills=[])
    for k in ("query", "episodes", "facts", "skills", "confidence",
              "n_results"):
        assert k in out
