"""Unit tests for benchmark/local_gate_finetune.py — data plumbing only (the torch
training loop is exercised by the real run, not unit-tested)."""
from __future__ import annotations

import json

from benchmark.local_gate_finetune import build_training_pairs, split_train_val


def _mini_jsonl(tmp_path, n_users=6):
    p = tmp_path / "mini.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for ui in range(n_users):
            sessions = []
            for si in range(2):
                sessions.append({
                    "dialogue": [
                        {"role": "user", "content": f"I adopted a dog named Rex{ui}{si}."},
                        {"role": "assistant", "content": "Nice!"},
                    ],
                    "memory_points": [
                        {"memory_source": "secondary",
                         "memory_content": f"User {ui} has a dog named Rex{ui}{si}."},
                        {"memory_source": "interference",
                         "memory_content": f"User {ui} has a cat named Felix{ui}{si}."},
                    ],
                })
            f.write(json.dumps({"sessions": sessions}) + "\n")
    return p


def test_training_pairs_only_from_train_users(tmp_path):
    src = _mini_jsonl(tmp_path)
    train_users = {0, 1, 2}
    items = build_training_pairs(src, train_users, seed=7, budget=400,
                                 speakers=False, foreign_per_user=2)
    assert items, "no training items built"
    for it in items:
        assert it["span_user"] in train_users
        if it["kind"] == "foreign":
            assert it["fact_user"] in train_users, "foreign donor leaked from heldout"
            assert it["fact_user"] != it["span_user"]
        else:
            assert it["fact_user"] == it["span_user"]
        assert it["label"] == (1 if it["kind"] == "clean" else 0)


def test_training_pairs_balanced_and_deterministic(tmp_path):
    src = _mini_jsonl(tmp_path, n_users=6)
    a = build_training_pairs(src, {0, 1, 2, 3}, seed=7, budget=400,
                             speakers=False, foreign_per_user=1)
    b = build_training_pairs(src, {0, 1, 2, 3}, seed=7, budget=400,
                             speakers=False, foreign_per_user=1)
    assert a == b
    n_pos = sum(1 for x in a if x["label"] == 1)
    n_neg = sum(1 for x in a if x["label"] == 0)
    assert n_pos <= 2 * n_neg, "positives capped at 2x negatives"


def test_split_train_val_stratified_no_overlap():
    items = ([{"fact": f"p{i}", "label": 1} for i in range(20)]
             + [{"fact": f"n{i}", "label": 0} for i in range(10)])
    tr, va = split_train_val(items, seed=7, val_frac=0.2)
    assert len(tr) + len(va) == 30
    assert {id(x) for x in tr}.isdisjoint({id(x) for x in va})
    # stratified: both labels present in val
    assert {x["label"] for x in va} == {0, 1}
    va_pos = sum(1 for x in va if x["label"] == 1)
    assert 2 <= va_pos <= 6  # ~20% of 20 positives
