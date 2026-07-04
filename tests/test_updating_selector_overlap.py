"""Iter 6 — precision floor on the HaluMem update selector.

A WRONG update (selecting an unrelated memory to overwrite) corrupts truth. The
NLI selector sometimes gives a high refine/contradiction score to a candidate that
shares little content with the update. A content-overlap floor rejects those.
Measured frontier (HaluMem 5 users / 726 updates, local e5 scoring): floor 0.10
lifts accuracy 0.664->0.674 AND cuts update-hallucination 0.194->0.167 (Pareto);
0.15 cuts it to 0.138 at flat accuracy. Default 0.0 = unchanged.
"""
from __future__ import annotations

from benchmark.halumem_updating_bench import select_from_scored

_E = {"contradiction": 0.0, "entailment": 0.0}


def _refine(p):
    return {"contradiction": 0.0, "entailment": p}


def test_overlap_floor_rejects_low_overlap_high_score() -> None:
    update = "the capital of Zorvia is Brantol now"
    scored = [
        # high refine score but UNRELATED content -> a wrong update
        ("a", "Tom likes coffee in the morning", _E, _refine(0.9)),
        # lower score but same subject/attribute -> the real target
        ("b", "the capital of Zorvia is Helmsford", _E, _refine(0.75)),
    ]
    # no floor: the higher score (a) wins even though it is unrelated
    assert select_from_scored(scored, update, select_thr=0.7, min_overlap=0.0) == "a"
    # floor: a is filtered on overlap, the real same-attribute candidate wins
    assert select_from_scored(scored, update, select_thr=0.7, min_overlap=0.15) == "b"


def test_floor_can_reject_all_and_return_none() -> None:
    update = "the capital of Zorvia is Brantol"
    scored = [("a", "Tom likes coffee", _E, _refine(0.9))]
    assert select_from_scored(scored, update, select_thr=0.7, min_overlap=0.3) is None


def test_default_no_floor_is_unchanged() -> None:
    scored = [("a", "anything at all", _E, _refine(0.9))]
    # no new_content, no floor -> pure score policy, byte-identical to before
    assert select_from_scored(scored, select_thr=0.7) == "a"
