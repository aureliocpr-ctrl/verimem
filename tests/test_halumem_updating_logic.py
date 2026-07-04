"""Pure decision logic of the HaluMem official UPDATING slice (task #5, 2026-07-03).

Protocol (arXiv 2511.03506 + eval/ repo): for each memory point labeled update,
retrieve the top-10 most relevant live memories; the system must pick WHICH
existing memory to update; outcomes are Correct / Wrong (hallucinated update) /
Missed (omission). Leaderboard "Updating" = correct rate (MemOS self-reported
62.1). The official judge is gpt-4o — our run will carry a declared
Claude-judge asterisk; this module's LOCAL classification is the development
signal and is judge-free by construction.
"""
from __future__ import annotations

from benchmark.halumem_updating_bench import (
    classify_update_outcome,
    select_update_target,
)


def _scorer(table: dict[tuple[str, str], dict[str, float]]):
    """NLI-classifier stand-in: returns the given {label: prob} per pair,
    NEUTRAL-ish zeros for anything not listed."""
    def score(pairs):
        return [table.get(p, {"contradiction": 0.0, "entailment": 0.0,
                              "neutral": 1.0}) for p in pairs]
    return score


def test_select_picks_the_contradicted_candidate() -> None:
    cands = [("f1", "likes tea"), ("f2", "salary is 50k"), ("f3", "lives in Rome")]
    scorer = _scorer({("salary is 50k", "salary is 60k"): {"contradiction": 0.95}})
    assert select_update_target(cands, "salary is 60k", scorer) == "f2"


def test_select_picks_the_refined_candidate_via_update_entails_it() -> None:
    # the dominant HaluMem pattern: the update REFINES the original — the
    # update entails the candidate, no contradiction anywhere.
    cands = [("f1", "likes tea"), ("f2", "considering a career change")]
    scorer = _scorer({("considering a career change due to mental health",
                       "considering a career change"): {"entailment": 0.93}})
    assert select_update_target(
        cands, "considering a career change due to mental health", scorer) == "f2"


def test_candidate_entailing_the_update_is_not_a_target() -> None:
    # one-way entailment in the WRONG direction (candidate ⊨ update) means the
    # candidate is BROADER — updating it would overwrite information.
    cands = [("f1", "works at Acme in Rome")]
    scorer = _scorer({("works at Acme in Rome", "works at Acme"):
                      {"entailment": 0.95}})
    assert select_update_target(cands, "works at Acme", scorer) is None


def test_select_returns_none_when_nothing_scores() -> None:
    cands = [("f1", "likes tea")]
    assert select_update_target(cands, "moved to Paris", _scorer({})) is None


def test_select_takes_the_argmax_not_the_first_above_threshold() -> None:
    cands = [("f1", "salary was 50k last year"), ("f2", "salary is 50k")]
    scorer = _scorer({
        ("salary was 50k last year", "salary is 60k"): {"contradiction": 0.75},
        ("salary is 50k", "salary is 60k"): {"contradiction": 0.97},
    })
    assert select_update_target(cands, "salary is 60k", scorer) == "f2"


def test_outcome_correct_when_selection_matches_a_gt_original() -> None:
    out = classify_update_outcome(
        selected_text="salary is 50k",
        gt_originals=["salary is 50k"],
        candidates_texts=["salary is 50k", "likes tea"])
    assert out == "correct"


def test_outcome_wrong_when_selection_is_not_a_gt_original() -> None:
    out = classify_update_outcome(
        selected_text="likes tea",
        gt_originals=["salary is 50k"],
        candidates_texts=["salary is 50k", "likes tea"])
    assert out == "wrong"


def test_outcome_missed_when_nothing_selected_but_gt_was_reachable() -> None:
    out = classify_update_outcome(
        selected_text=None,
        gt_originals=["salary is 50k"],
        candidates_texts=["salary is 50k", "likes tea"])
    assert out == "missed"


def test_outcome_unreachable_when_gt_not_in_candidates() -> None:
    # retrieval failed to surface the GT original at all: counted as missed in
    # the official protocol, but reported separately for diagnosis.
    out = classify_update_outcome(
        selected_text=None,
        gt_originals=["salary is 50k"],
        candidates_texts=["likes tea", "lives in Rome"])
    assert out == "missed_unreachable"


def test_gt_matching_is_whitespace_case_insensitive() -> None:
    out = classify_update_outcome(
        selected_text="  Salary is 50K ",
        gt_originals=["salary is 50k"],
        candidates_texts=["salary is 50k"])
    assert out == "correct"
