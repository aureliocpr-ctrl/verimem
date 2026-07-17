"""R22: Cross-agent consensus on facts.

When facts from different agents converge on the same proposition,
that's strong evidence. Cluster similar facts, count distinct
agent_ids per cluster.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str
    confidence: float = 0.9


def test_empty_returns_empty():
    from verimem.cross_agent_consensus import find_consensus_facts
    out = find_consensus_facts([])
    assert out["consensus"] == []


def test_multiple_agents_agree():
    from verimem.cross_agent_consensus import find_consensus_facts
    facts = [
        _Fact("f1", "WordPress 5.8 vulnerable to CVE-X",
              "agent:pentester/vuln"),
        _Fact("f2", "WordPress 5.8 vulnerable to CVE-X",
              "agent:reviewer/security"),
        _Fact("f3", "WordPress 5.8 vulnerable to CVE-X",
              "agent:architect/risk"),
    ]
    out = find_consensus_facts(facts, min_agents=2)
    assert len(out["consensus"]) >= 1
    c = out["consensus"][0]
    assert c["n_agents"] >= 2


def test_single_agent_no_consensus():
    from verimem.cross_agent_consensus import find_consensus_facts
    facts = [
        _Fact("f1", "X claim", "agent:A/x"),
        _Fact("f2", "X claim", "agent:A/y"),  # same agent
    ]
    out = find_consensus_facts(facts, min_agents=2)
    assert out["consensus"] == []


def test_payload_keys():
    from verimem.cross_agent_consensus import find_consensus_facts
    out = find_consensus_facts([])
    for k in ("consensus", "n_facts_scanned"):
        assert k in out


def test_consensus_keys():
    from verimem.cross_agent_consensus import find_consensus_facts
    facts = [
        _Fact("f1", "common fact one", "agent:A/x"),
        _Fact("f2", "common fact one", "agent:B/x"),
    ]
    out = find_consensus_facts(facts, min_agents=2)
    if out["consensus"]:
        for k in ("representative", "n_agents", "agent_ids", "fact_ids"):
            assert k in out["consensus"][0]


def test_dissenting_facts_excluded():
    from verimem.cross_agent_consensus import find_consensus_facts
    facts = [
        _Fact("f1", "claim X is true", "agent:A/x"),
        _Fact("f2", "claim X is true", "agent:B/x"),
        _Fact("f3", "totally different", "agent:C/x"),
    ]
    out = find_consensus_facts(facts, min_agents=2)
    # Only the cluster of 2 should make consensus
    for c in out["consensus"]:
        assert c["n_agents"] >= 2
