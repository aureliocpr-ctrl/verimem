"""Batch LEXICAL-conflict scan — retroactive twin of the expanded write-gate.

The 0.7.0 lexical moat catches numeric / version / sub-year date changes at
write time (``validate_claim``); this scans what is ALREADY stored with the
SAME ``quantity_match`` primitives, so the two views agree by construction
(the module's stated design goal). Negation flips stay with the dedicated
polarity scanner (``find_conflicting_pairs``).
"""
from __future__ import annotations

from verimem.facts_conflict import (
    LexicalConflictPair,
    find_lexical_conflicts,
)
from verimem.semantic import Fact


def _f(prop: str, topic: str = "eng/component", confidence: float = 1.0) -> Fact:
    return Fact(proposition=prop, topic=topic, confidence=confidence)


def test_empty_and_single_pool_return_empty() -> None:
    assert find_lexical_conflicts([]) == []
    assert find_lexical_conflicts([_f("Orion ships on version 2.3.1.")]) == []


def test_version_conflict_detected() -> None:
    facts = [
        _f("Orion ships on version 2.3.1.", topic="eng/orion"),
        _f("Orion ships on version 4.0.0.", topic="eng/orion"),
    ]
    pairs = find_lexical_conflicts(facts)
    assert len(pairs) == 1
    p = pairs[0]
    assert isinstance(p, LexicalConflictPair)
    assert p.kind == "version"


def test_version_different_named_subjects_no_conflict() -> None:
    facts = [
        _f("Orion ships on version 2.3.1.", topic="eng/mixed"),
        _f("Zephyr ships on version 4.0.0.", topic="eng/mixed"),
    ]
    assert find_lexical_conflicts(facts) == []


def test_date_conflict_same_year_detected() -> None:
    facts = [
        _f("Project Aurora launches in March 2025.", topic="eng/aurora"),
        _f("Project Aurora launches in September 2025.", topic="eng/aurora"),
    ]
    pairs = find_lexical_conflicts(facts)
    assert len(pairs) == 1
    assert pairs[0].kind == "date"


def test_numeric_conflict_included_with_kind() -> None:
    facts = [
        _f("Sessions are stored with a TTL of 30 minutes.", topic="eng/session"),
        _f("Sessions expire after 45 minutes of inactivity.", topic="eng/session"),
    ]
    pairs = find_lexical_conflicts(facts)
    assert len(pairs) == 1
    assert pairs[0].kind == "numeric"
    assert "30" in pairs[0].detail and "45" in pairs[0].detail


def test_unrelated_topics_do_not_pair() -> None:
    facts = [
        _f("Orion ships on version 2.3.1.", topic="eng/orion"),
        _f("The gateway defaults to version 4.0.0 of the schema.", topic="ops/gw"),
    ]
    # no shared distinctive subject word -> no conflict
    assert find_lexical_conflicts(facts) == []


def test_as_dict_round_trip() -> None:
    facts = [
        _f("Orion ships on version 2.3.1.", topic="eng/orion"),
        _f("Orion ships on version 4.0.0.", topic="eng/orion"),
    ]
    d = find_lexical_conflicts(facts)[0].as_dict()
    assert d["kind"] == "version"
    assert d["fact_a"]["id"] and d["fact_b"]["id"]
