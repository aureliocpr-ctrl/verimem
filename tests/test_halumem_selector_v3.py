"""LLM/embedding-free logic of the v3 learned update-target discriminator."""
from __future__ import annotations

import copy

from benchmark.halumem_selector_v3 import (
    FEATURE_NAMES,
    build_dataset,
    build_idf,
    classify_items,
    crossval_select,
    featurize_item,
)


def _cand(text, retrieval=0.5, contra=0.0, entail_ba=0.0):
    return {"text": text, "retrieval": retrieval,
            "ab": {"contradiction": contra, "entailment": 0.0},
            "ba": {"contradiction": contra, "entailment": entail_ba}}


def _item(user, update, cands, gts):
    return {"user": user, "update": update, "candidates": cands,
            "gt_originals": gts}


def test_featurize_shapes_and_names() -> None:
    it = _item(0, "salary changed from 50k to 60k",
               [_cand("salary is 50k"), _cand("likes tea")], ["salary is 50k"])
    idf = build_idf([it])
    rows = featurize_item(it, idf)
    assert len(rows) == 2
    assert all(len(r) == len(FEATURE_NAMES) for r in rows)


def test_features_are_runtime_legal_no_gt_leak() -> None:
    """Changing ONLY gt_originals must not change any feature value."""
    it = _item(0, "pet updated from Labradors to Retrievers",
               [_cand("Martin loves his Labradors", retrieval=0.7),
                _cand("Martin works at Acme", retrieval=0.9)],
               ["Martin loves his Labradors"])
    idf = build_idf([it])
    rows_a = featurize_item(it, idf)
    it2 = copy.deepcopy(it)
    it2["gt_originals"] = ["a completely different ground truth"]
    rows_b = featurize_item(it2, idf)
    assert rows_a == rows_b


def test_overlap_and_number_features_discriminate() -> None:
    upd = "Martin runs 5 sessions per week now instead of 3"
    target = _cand("Martin runs 3 sessions per week")
    offtopic = _cand("Daniel enjoys healthcare consulting work")
    it = _item(0, upd, [target, offtopic], ["Martin runs 3 sessions per week"])
    idf = build_idf([it])
    rows = featurize_item(it, idf)
    feats = dict(zip(FEATURE_NAMES, rows[0], strict=True))
    feats_off = dict(zip(FEATURE_NAMES, rows[1], strict=True))
    assert feats["jaccard"] > feats_off["jaccard"]
    assert feats["num_shared"] > feats_off["num_shared"]


def test_build_dataset_labels_groups_and_reachability() -> None:
    exact = lambda a, b: a == b  # noqa: E731
    reachable = _item(1, "u1", [_cand("the truth"), _cand("noise")],
                      ["the truth"])
    unreachable = _item(2, "u2", [_cand("noise a"), _cand("noise b")],
                        ["the truth"])
    ds = build_dataset([reachable, unreachable], exact)
    # only the reachable item contributes training rows
    assert ds["item_of_row"] == [0, 0]
    assert ds["y"] == [1, 0]
    assert ds["groups"] == [1, 1]
    assert ds["reachable_items"] == [0]


def test_crossval_no_user_leakage_and_learns_separable_signal() -> None:
    """4 users, GT always the high-jaccard candidate: out-of-fold selection
    must recover it on held-out users, and no fold may train on its own
    test users."""
    exact = lambda a, b: a == b  # noqa: E731
    items = []
    for u in range(4):
        for i in range(6):
            gt = f"user{u} fact {i} value alpha beta gamma"
            upd = f"user{u} fact {i} value alpha beta gamma updated"
            items.append(_item(u, upd,
                               [_cand(gt, retrieval=0.4),
                                _cand("totally unrelated noise text",
                                      retrieval=0.9)],
                               [gt]))
    res = crossval_select(items, exact, n_splits=2, seed=7)
    for fold in res["folds"]:
        assert not (set(fold["train_users"]) & set(fold["test_users"]))
    picked = [res["selected"][i] for i in range(len(items))]
    correct = sum(sel == it["gt_originals"][0]
                  for sel, it in zip(picked, items, strict=True))
    # retrieval alone would pick the noise every time (0/24)
    assert correct >= 20


def test_classify_items_judge_compatible_records() -> None:
    exact = lambda a, b: a == b  # noqa: E731
    items = [
        _item(1, "u1", [_cand("the truth"), _cand("noise")], ["the truth"]),
        _item(1, "u2", [_cand("noise a"), _cand("noise b")], ["the truth"]),
        _item(2, "u3", [_cand("the truth"), _cand("noise")], ["the truth"]),
    ]
    picks = {"u1": "the truth", "u2": "noise a", "u3": None}
    records, counts = classify_items(items, lambda it: picks[it["update"]],
                                     exact)
    assert [r["outcome"] for r in records] == ["correct", "wrong", "missed"]
    assert counts == {"correct": 1, "wrong": 1, "missed": 1,
                      "missed_unreachable": 0}
    # judge-pass consumes these exact keys with FULL texts
    assert all({"outcome", "update", "gt_originals", "selected"} <= set(r)
               for r in records)
    assert records[2]["selected"] == ""
