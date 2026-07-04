"""R35: Agent specialization score.

For each agent, compute "specialization" = entropy of topic distribution.
Low entropy → highly specialised. High entropy → generalist.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Fact:
    id: str
    topic: str
    proposition: str = ""
    confidence: float = 0.9


def test_empty_returns_no_agents():
    from engram.agent_specialization import compute_specialization
    out = compute_specialization([])
    assert out["per_agent"] == []


def test_highly_specialized_agent_low_entropy():
    from engram.agent_specialization import compute_specialization
    facts = [
        _Fact("f1", "agent:specialist/cve"),
        _Fact("f2", "agent:specialist/cve"),
        _Fact("f3", "agent:specialist/cve"),
    ]
    out = compute_specialization(facts)
    by_id = {a["agent_id"]: a for a in out["per_agent"]}
    # All same sub-topic → low entropy → "specialist"
    assert by_id["specialist"]["entropy"] < 0.5


def test_generalist_high_entropy():
    from engram.agent_specialization import compute_specialization
    facts = [
        _Fact("f1", "agent:gen/cve"),
        _Fact("f2", "agent:gen/lessons"),
        _Fact("f3", "agent:gen/lint"),
        _Fact("f4", "agent:gen/perf"),
        _Fact("f5", "agent:gen/auth"),
    ]
    out = compute_specialization(facts)
    by_id = {a["agent_id"]: a for a in out["per_agent"]}
    # Many different sub-topics → high entropy
    assert by_id["gen"]["entropy"] > 1.0


def test_payload_shape():
    from engram.agent_specialization import compute_specialization
    out = compute_specialization([])
    for k in ("per_agent", "n_agents"):
        assert k in out


def test_entry_keys():
    from engram.agent_specialization import compute_specialization
    facts = [_Fact("f1", "agent:A/topic1")]
    out = compute_specialization(facts)
    if out["per_agent"]:
        for k in ("agent_id", "n_facts", "entropy", "specialization"):
            assert k in out["per_agent"][0]


def test_specialization_classification():
    from engram.agent_specialization import compute_specialization
    facts = [
        _Fact("f1", "agent:S/x"),
        _Fact("f2", "agent:S/x"),
        _Fact("f3", "agent:S/x"),
    ]
    out = compute_specialization(facts)
    for a in out["per_agent"]:
        assert a["specialization"] in {"specialist", "balanced", "generalist"}
