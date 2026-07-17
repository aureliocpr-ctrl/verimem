"""The semantic NLI judge wired into reconcile fixes BOTH lexical failure modes:
catches paraphrase/antonym value-conflicts (recall) AND rejects same-entity complementary
facts (precision). Hermetic — a stub RelationJudge, no model load, no LLM."""
from __future__ import annotations

from verimem.semantic_conflict import Relation
from verimem.truth_reconciliation import _is_conflict, looks_like_conflict


class _StubJudge:
    """Returns the relation from a {(a,b)->Relation} map; NEUTRAL otherwise."""

    def __init__(self, verdicts):
        self._v = verdicts

    def classify(self, a, b):
        return self._v.get((a, b), Relation.NEUTRAL)


def test_nli_catches_paraphrase_conflict_lexical_misses():
    a, b = "Donald Brown dislikes techno music", "Donald Brown now appreciates techno music"
    # lexical heuristic misses it (filler 'now' + antonym, only_b > max_diff)
    assert looks_like_conflict(a, b) is False
    # the NLI judge catches it -> _is_conflict True
    judge = _StubJudge({(a, b): Relation.CONTRADICTION})
    assert _is_conflict(a, b, judge) is True


def test_nli_rejects_complementary_lexical_would_overmatch():
    a, b = "config X is 5s", "config X owner is Bob"  # value vs owner = complementary
    judge = _StubJudge({(a, b): Relation.NEUTRAL})
    assert _is_conflict(a, b, judge) is False  # NLI keeps precision


def test_is_conflict_falls_back_to_lexical_without_judge():
    # same-attribute different-value, ≤1 token diff each side -> lexical True
    assert _is_conflict("the port is 8080", "the port is 9090", None) is True
    assert _is_conflict("a b c d e", "x y z w v", None) is False


def test_judge_error_falls_back_to_lexical():
    class _Boom:
        def classify(self, a, b):
            raise RuntimeError("nli down")

    # judge raises -> _is_conflict must not crash, falls back to lexical
    assert _is_conflict("the port is 8080", "the port is 9090", _Boom()) is True
