"""R8: Symbolic-neural bridge — inference on facts without LLM.

Detects rule-shaped facts ("if X then Y", "X → Y", "X implies Y")
and chains them with state facts to deduce new propositions.

Limited to short forward-chaining (≤max_depth). Doesn't replace LLM
reasoning — complements it for cheap deductions.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = "t"
    confidence: float = 0.9


def test_detect_implication_arrow():
    from verimem.symbolic_inference import parse_rule

    out = parse_rule("WordPress 5.8 -> vulnerable to CVE-2023-X")
    assert out is not None
    assert "WordPress 5.8" in out["antecedent"]
    assert "vulnerable to CVE-2023-X" in out["consequent"]


def test_detect_if_then():
    from verimem.symbolic_inference import parse_rule

    out = parse_rule("If vendor is cloudflare then WAF is present")
    assert out is not None


def test_non_rule_returns_none():
    from verimem.symbolic_inference import parse_rule

    assert parse_rule("Just a regular fact") is None
    assert parse_rule("Aurelio is the CEO") is None


def test_forward_chain_simple():
    from verimem.symbolic_inference import forward_chain

    rules = [
        _Fact("r1", "WordPress 5.8 -> vulnerable to CVE-2023-X"),
        _Fact("r2", "vulnerable to CVE-2023-X -> RCE available"),
    ]
    state = [
        _Fact("s1", "target acme.io runs WordPress 5.8"),
    ]
    out = forward_chain(rules=rules, state_facts=state, max_depth=3)
    deduced_propositions = [d["proposition"] for d in out["deductions"]]
    # Should deduce CVE-2023-X then RCE
    assert any("CVE-2023-X" in d for d in deduced_propositions)


def test_no_match_no_deduction():
    from verimem.symbolic_inference import forward_chain

    rules = [_Fact("r1", "Linux kernel 5.x -> patched")]
    state = [_Fact("s1", "Windows server 2019")]
    out = forward_chain(rules=rules, state_facts=state)
    assert out["deductions"] == []


def test_chain_depth_limit():
    """Max_depth=1 should stop after 1 inference layer."""
    from verimem.symbolic_inference import forward_chain

    rules = [
        _Fact("r1", "A -> B"),
        _Fact("r2", "B -> C"),
        _Fact("r3", "C -> D"),
    ]
    state = [_Fact("s1", "A is present")]
    out = forward_chain(rules=rules, state_facts=state, max_depth=1)
    # Only B should be deduced (not C, not D)
    props = " ".join(d["proposition"] for d in out["deductions"])
    assert "B" in props


def test_deduction_carries_provenance():
    from verimem.symbolic_inference import forward_chain

    rules = [_Fact("r_main", "X -> Y")]
    state = [_Fact("s_seed", "X is true")]
    out = forward_chain(rules=rules, state_facts=state)
    assert out["deductions"]
    d = out["deductions"][0]
    assert "rule_id" in d
    assert "depth" in d
    assert d["rule_id"] == "r_main"


def test_payload_keys():
    from verimem.symbolic_inference import forward_chain

    out = forward_chain(rules=[], state_facts=[])
    for k in ("deductions", "n_rules", "n_state", "max_depth_reached"):
        assert k in out
