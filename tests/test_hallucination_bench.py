"""Deterministic scorers for the SQuAD-v2 hallucination bench (no LLM, no network)."""
from __future__ import annotations

from benchmark.hallucination_bench import contains_gold, is_abstention


def test_is_abstention_positive() -> None:
    assert is_abstention("NO ANSWER")
    assert is_abstention("The context does not mention her salary.")
    assert is_abstention("That information is not in the passage.")
    assert is_abstention("I don't know based on the given text.")
    assert is_abstention("This question is unanswerable from the context.")


def test_is_abstention_negative() -> None:
    assert not is_abstention("Berlin")
    assert not is_abstention("She lives in Berlin.")
    assert not is_abstention("France")


def test_contains_gold_squad_normalized() -> None:
    assert contains_gold("She lives in Berlin.", ["Berlin"])
    assert contains_gold("The answer is France.", ["France"])
    assert contains_gold("the 10th and 11th centuries", ["10th and 11th centuries"])
    assert not contains_gold("Paris", ["Berlin"])
    assert not contains_gold("", ["Berlin"])
