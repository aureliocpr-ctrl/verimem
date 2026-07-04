"""LLM/embedding-free logic of the offline selector sweep."""
from __future__ import annotations

from benchmark.halumem_selector_sweep import (
    extract_old_value,
    old_value_hit,
    policy_oldvalue_then_v1,
    policy_v1,
    score_policy,
)


def test_extract_old_value_from_quoted_and_bare_forms() -> None:
    assert extract_old_value(
        "company_name updated from 'Global Nutrition Initiative' to 'World "
        "Nutrition Organization'.") == "Global Nutrition Initiative"
    assert extract_old_value(
        "Martin has modified his pet preference from Labradors to Golden "
        "Retrievers") == "Labradors"
    assert extract_old_value("Martin now prefers tea.") is None


def test_old_value_hit_is_token_containment_not_substring() -> None:
    assert old_value_hit("Global Nutrition Initiative",
                         "Taylor David works at Global Nutrition Initiative")
    assert old_value_hit("Labradors", "Martin's favorite dogs are labradors!")
    assert not old_value_hit("Labradors", "Martin likes Golden Retrievers")
    assert not old_value_hit(None, "anything")


def _cand(text, contra=0.0, entail_ba=0.0, retrieval=0.5):
    return {"text": text, "retrieval": retrieval,
            "ab": {"contradiction": contra, "entailment": 0.0},
            "ba": {"contradiction": contra, "entailment": entail_ba}}


def test_policy_v1_argmax_over_threshold() -> None:
    item = {"update": "salary is 60k",
            "candidates": [_cand("salary is 50k", contra=0.95),
                           _cand("likes tea", entail_ba=0.75)]}
    assert policy_v1(item, 0.8) == "salary is 50k"
    assert policy_v1(item, 0.99) is None


def test_oldvalue_policy_overrides_v1_on_unique_hit() -> None:
    item = {"update": "pet preference updated from Labradors to Retrievers",
            "candidates": [_cand("record of a change from poodles", contra=0.9),
                           _cand("Martin loves his Labradors", entail_ba=0.1)]}
    # v1 would pick the high-contradiction record; old-value containment
    # (unique hit) must win.
    assert policy_oldvalue_then_v1(item, 0.7) == "Martin loves his Labradors"


def test_score_policy_uses_matcher_and_reachability() -> None:
    items = [{"update": "u", "gt_originals": ["the truth"],
              "candidates": [_cand("the truth", entail_ba=0.9),
                             _cand("noise", contra=0.0)]}]
    exact = lambda a, b: a == b  # noqa: E731
    res = score_policy(items, lambda it: policy_v1(it, 0.7), exact)
    assert res["outcomes"]["correct"] == 1
    res2 = score_policy(items, lambda it: None, exact)
    assert res2["outcomes"]["missed"] == 1
