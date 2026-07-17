"""R28: Agent workload balance — who's doing the most work.

Aggregate facts + episodes per agent_id. Identify imbalance.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Fact:
    id: str
    topic: str
    proposition: str = ""
    confidence: float = 0.9


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str = "success"


def test_empty_returns_no_load():
    from verimem.agent_workload import compute_workload
    out = compute_workload(facts=[], episodes=[])
    assert out["per_agent"] == []


def test_facts_attributed_by_agent_prefix():
    from verimem.agent_workload import compute_workload
    facts = [
        _Fact("f1", "agent:A/x"),
        _Fact("f2", "agent:A/y"),
        _Fact("f3", "agent:B/x"),
        _Fact("f4", "shared/x"),
    ]
    out = compute_workload(facts=facts, episodes=[])
    by_id = {a["agent_id"]: a for a in out["per_agent"]}
    assert by_id["A"]["n_facts"] == 2
    assert by_id["B"]["n_facts"] == 1


def test_top_loaded_agent_first():
    from verimem.agent_workload import compute_workload
    facts = [
        _Fact("f1", "agent:A/x"),
        _Fact("f2", "agent:A/y"),
        _Fact("f3", "agent:A/z"),
        _Fact("f4", "agent:B/x"),
    ]
    out = compute_workload(facts=facts, episodes=[])
    # A has more → first
    assert out["per_agent"][0]["agent_id"] == "A"


def test_imbalance_score():
    from verimem.agent_workload import compute_workload
    facts = [
        _Fact("f1", "agent:A/x"),
        _Fact("f2", "agent:A/y"),
        _Fact("f3", "agent:A/z"),
        _Fact("f4", "agent:B/x"),
    ]
    out = compute_workload(facts=facts, episodes=[])
    assert "imbalance" in out
    assert 0.0 <= out["imbalance"] <= 1.0


def test_payload_shape():
    from verimem.agent_workload import compute_workload
    out = compute_workload(facts=[], episodes=[])
    for k in ("per_agent", "imbalance", "n_agents"):
        assert k in out


def test_perfect_balance_low_imbalance():
    from verimem.agent_workload import compute_workload
    facts = [
        _Fact("f1", "agent:A/x"),
        _Fact("f2", "agent:B/x"),
        _Fact("f3", "agent:C/x"),
    ]
    out = compute_workload(facts=facts, episodes=[])
    # All same load → imbalance ~0
    assert out["imbalance"] < 0.2
