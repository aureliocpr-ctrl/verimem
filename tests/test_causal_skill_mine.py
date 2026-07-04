"""R2.2: Mine skill candidates from N causal extractions.

Take a list of causal signals (output of causal_extract), find rules
that recur ≥min_evidence times → propose skill candidates with
preconditions/postconditions derived from the divergences.
"""
from __future__ import annotations


def _signal(rule: str, tool_s: str | None = None, tool_f: str | None = None,
            div: int = 1, conf: float = 0.8):
    return {
        "divergence_step": div,
        "cause": f"[action] tool={tool_f}" if tool_f else "(none)",
        "alternative": f"[action] tool={tool_s}" if tool_s else "(none)",
        "rule": rule,
        "confidence": conf,
        "evidence": {"success_id": "s", "failure_id": "f"},
    }


def test_empty_returns_empty_candidates():
    from engram.causal_skill_mine import causal_skill_mine
    out = causal_skill_mine([])
    assert out["candidates"] == []


def test_single_signal_below_threshold():
    from engram.causal_skill_mine import causal_skill_mine
    sigs = [_signal("Prefer `crtsh` over `nmap` in this context")]
    out = causal_skill_mine(sigs, min_evidence=2)
    # Only 1 instance, threshold is 2 → no candidate
    assert out["candidates"] == []


def test_recurring_rule_becomes_candidate():
    from engram.causal_skill_mine import causal_skill_mine
    rule = "Prefer `crtsh` over `nmap` in this context"
    sigs = [_signal(rule) for _ in range(3)]
    out = causal_skill_mine(sigs, min_evidence=2)
    assert len(out["candidates"]) == 1
    c = out["candidates"][0]
    assert c["rule"] == rule
    assert c["evidence_count"] == 3


def test_multiple_rules_each_above_threshold():
    from engram.causal_skill_mine import causal_skill_mine
    sigs = [
        _signal("Rule A"), _signal("Rule A"),
        _signal("Rule B"), _signal("Rule B"), _signal("Rule B"),
    ]
    out = causal_skill_mine(sigs, min_evidence=2)
    assert len(out["candidates"]) == 2
    # Sorted by evidence_count desc
    assert out["candidates"][0]["evidence_count"] == 3
    assert out["candidates"][1]["evidence_count"] == 2


def test_candidate_carries_avg_confidence():
    from engram.causal_skill_mine import causal_skill_mine
    sigs = [
        _signal("Rule X", conf=0.9),
        _signal("Rule X", conf=0.7),
    ]
    out = causal_skill_mine(sigs, min_evidence=2)
    c = out["candidates"][0]
    assert 0.7 <= c["avg_confidence"] <= 0.9


def test_signals_with_empty_rule_ignored():
    from engram.causal_skill_mine import causal_skill_mine
    sigs = [_signal(""), _signal(""), _signal("real rule"), _signal("real rule")]
    out = causal_skill_mine(sigs, min_evidence=2)
    # Empty rules don't become candidates
    rules = [c["rule"] for c in out["candidates"]]
    assert "" not in rules
    assert "real rule" in rules


def test_payload_shape():
    from engram.causal_skill_mine import causal_skill_mine
    out = causal_skill_mine([])
    for k in ("candidates", "n_total_signals", "n_candidates"):
        assert k in out
