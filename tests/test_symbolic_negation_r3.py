"""Audit 3-round #24 (soundness): forward_chain's antecedent match must be a
whole-word, negation-aware match — not a raw substring.

`ant_lower in prop` fired on "cat" inside "category" and, worse, ignored
negation: "running" matched "service is NOT running", deducing the consequent
from a state fact that asserts the opposite. Both are unsound deductions. Fix:
word-boundary regex (re.escape + \\b) plus a guard that skips a match preceded
by a local negation token.
"""
from __future__ import annotations

from dataclasses import dataclass

from engram.symbolic_inference import forward_chain


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = "t"
    confidence: float = 0.9


def test_substring_does_not_match_inside_word() -> None:
    rules = [_Fact("r1", "cat -> meows")]
    state = [_Fact("s1", "the category is animals")]
    out = forward_chain(rules=rules, state_facts=state)
    assert out["deductions"] == [], \
        "'cat' non deve matchare dentro 'category' (substring non ancorato)"


def test_negated_antecedent_does_not_fire() -> None:
    rules = [_Fact("r1", "running -> healthy")]
    state = [_Fact("s1", "the service is not running")]
    out = forward_chain(rules=rules, state_facts=state)
    assert out["deductions"] == [], \
        "antecedente negato ('not running') non deve dedurre il consequent"


def test_whole_word_positive_still_fires() -> None:
    """Guard: a genuine whole-word, non-negated match must still deduce."""
    rules = [_Fact("r1", "running -> healthy")]
    state = [_Fact("s1", "the service is running")]
    out = forward_chain(rules=rules, state_facts=state)
    assert any("healthy" in d["proposition"] for d in out["deductions"]), \
        "match whole-word non negato deve dedurre il consequent"
