"""R37: Find contradictory facts via negation marker heuristic.

If two facts share most tokens BUT one contains a negation marker
(not/no/never/patched/fixed) and the other doesn't → likely
contradicting each other.

Limited heuristic, not NLI. Surfaces candidates for human review.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = ""
    confidence: float = 0.9


def test_empty_returns_no_disagreement():
    from engram.facts_disagreement import find_disagreements
    out = find_disagreements([])
    assert out["pairs"] == []


def test_negation_pair_flagged():
    from engram.facts_disagreement import find_disagreements
    facts = [
        _Fact("f1", "WordPress 5.8 is vulnerable to CVE-X"),
        _Fact("f2", "WordPress 5.8 is not vulnerable to CVE-X anymore"),
    ]
    out = find_disagreements(facts, sim_threshold=0.5)
    assert len(out["pairs"]) >= 1


def test_no_negation_no_pair():
    from engram.facts_disagreement import find_disagreements
    facts = [
        _Fact("f1", "WordPress 5.8 vulnerable"),
        _Fact("f2", "Linux kernel update available"),
    ]
    out = find_disagreements(facts)
    assert out["pairs"] == []


def test_patched_marker_recognized():
    from engram.facts_disagreement import find_disagreements
    facts = [
        _Fact("f1", "WordPress 5.8 vulnerable to CVE-X"),
        _Fact("f2", "WordPress 5.8 patched against CVE-X"),
    ]
    out = find_disagreements(facts, sim_threshold=0.4)
    # patched is a negation-like marker
    assert len(out["pairs"]) >= 1


def test_payload_shape():
    from engram.facts_disagreement import find_disagreements
    out = find_disagreements([])
    for k in ("pairs", "n_facts_scanned", "n_pairs"):
        assert k in out


def test_entry_keys():
    from engram.facts_disagreement import find_disagreements
    facts = [
        _Fact("f1", "X is true"),
        _Fact("f2", "X is not true"),
    ]
    out = find_disagreements(facts, sim_threshold=0.4)
    if out["pairs"]:
        for k in ("fact_a", "fact_b", "similarity", "rationale"):
            assert k in out["pairs"][0]
