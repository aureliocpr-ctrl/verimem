"""LLM-free logic of the updating judge pass: sampling, parsing, correction."""
from __future__ import annotations

from benchmark.halumem_updating_judge_pass import (
    agreement_and_correction,
    parse_verdict,
    stratified_sample,
)


def _items(cls, n):
    return [{"outcome": cls, "update": f"u{cls}{i}", "gt_originals": ["g"],
             "selected": "s"} for i in range(n)]


def test_stratified_sample_caps_each_class_and_is_deterministic() -> None:
    items = _items("correct", 30) + _items("wrong", 3) + _items("missed", 10)
    s1 = stratified_sample(items, 5, seed=7)
    s2 = stratified_sample(items, 5, seed=7)
    assert s1 == s2
    by = {}
    for it in s1:
        by[it["outcome"]] = by.get(it["outcome"], 0) + 1
    assert by == {"correct": 5, "wrong": 3, "missed": 5}


def test_parse_verdict_tolerates_case_and_noise_but_not_garbage() -> None:
    assert parse_verdict("CORRECT") == "correct"
    assert parse_verdict(" hallucinated.") == "hallucinated"
    assert parse_verdict("Omitted — no target") == "omitted"
    assert parse_verdict("the system did well") == "error"
    assert parse_verdict("") == "error"


def test_correction_reweights_full_counts_by_sampled_agreement() -> None:
    # judge confirms 80% of sampled local-correct and rescues 50% of sampled
    # local-wrong; full run: 100 correct, 40 wrong, 60 missed (never sampled →
    # local claim: omitted contributes 0).
    judged = (
        [{"local_outcome": "correct", "judge": "correct"}] * 8
        + [{"local_outcome": "correct", "judge": "hallucinated"}] * 2
        + [{"local_outcome": "wrong", "judge": "correct"}] * 5
        + [{"local_outcome": "wrong", "judge": "hallucinated"}] * 5
    )
    per_class, corrected = agreement_and_correction(
        judged, {"correct": 100, "wrong": 40, "missed": 60})
    assert per_class["correct"]["judge_correct"] == 8
    assert per_class["wrong"]["agree"] == 5
    # (100*0.8 + 40*0.5 + 60*0.0) / 200 = 0.5
    assert abs(corrected - 0.5) < 1e-9


def test_correction_with_no_sample_falls_back_to_local_claim() -> None:
    _, corrected = agreement_and_correction([], {"correct": 70, "missed": 30})
    assert abs(corrected - 0.7) < 1e-9
