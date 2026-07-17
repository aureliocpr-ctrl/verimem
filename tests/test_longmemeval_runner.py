"""TDD for the LongMemEval retrieval harness (benchmark/longmemeval_runner.py).

Pure metric functions (recall@k / hit@k / MRR) + one end-to-end hermetic check
that the real Engram recall retrieves the gold evidence session above a
distractor. Zero external API, zero ~/.verimem.
"""
from __future__ import annotations

from benchmark.longmemeval_runner import (
    eval_question,
    hit_at_k,
    mrr,
    recall_at_k,
    run_dataset,
    session_to_text,
)


def test_recall_at_k():
    assert recall_at_k(["a", "b", "c"], {"a", "c"}, 3) == 1.0
    assert recall_at_k(["a", "x", "y"], {"a", "c"}, 3) == 0.5
    assert recall_at_k(["x", "y"], {"a"}, 2) == 0.0
    assert recall_at_k(["a"], set(), 3) is None  # no gold -> excluded from metric


def test_hit_at_k():
    assert hit_at_k(["x", "a"], {"a"}, 2) == 1.0
    assert hit_at_k(["x", "a"], {"a"}, 1) == 0.0  # gold at rank 2, k=1
    assert hit_at_k(["x", "y"], {"a"}, 5) == 0.0


def test_mrr_uses_first_gold_rank():
    assert mrr(["x", "a", "b"], {"a"}) == 0.5
    assert mrr(["a", "x"], {"a"}) == 1.0
    assert mrr(["x", "y"], {"a"}) == 0.0


def test_recall_dedupes_repeated_session_ids():
    # same session id retrieved twice must not inflate recall past 1.0
    assert recall_at_k(["a", "a", "a"], {"a"}, 5) == 1.0


def test_session_to_text_joins_roles():
    txt = session_to_text([
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
        {"role": "user", "content": ""},  # empty dropped
    ])
    assert "user: hello" in txt and "assistant: hi there" in txt
    assert txt.count("\n") == 1  # the empty turn was dropped


def test_eval_question_retrieves_gold_above_distractor(tmp_path):
    q = {
        "question_id": "t1",
        "question_type": "single-session-user",
        "question": "what problem did I have with my car after the first service",
        "answer": "GPS not working",
        "haystack_session_ids": ["s_gold", "s_distract"],
        "answer_session_ids": ["s_gold"],
        "haystack_sessions": [
            [{"role": "user", "content": "After my car's first service the GPS navigation system stopped working correctly"}],
            [{"role": "user", "content": "I really enjoy cooking fresh pasta with my family on sundays"}],
        ],
    }
    r = eval_question(q, k=2, workdir=tmp_path)
    assert r["n_gold"] == 1 and r["n_haystack"] == 2 and r["n_stored"] == 2
    assert r["hit_at_k"] == 1.0, "real Engram recall failed to retrieve the gold evidence session"
    assert r["mrr"] in (1.0, 0.5)


def test_run_dataset_aggregates_by_type(tmp_path):
    ds = tmp_path / "mini.json"
    import json
    json_data = [
        {
            "question_id": "q1", "question_type": "single-session-user",
            "question": "what car issue after first service",
            "answer_session_ids": ["g1"],
            "haystack_session_ids": ["g1", "d1"],
            "haystack_sessions": [
                [{"role": "user", "content": "the car GPS broke after the first service appointment"}],
                [{"role": "user", "content": "my favourite holiday destination is the mountains in winter"}],
            ],
        },
    ]
    ds.write_text(json.dumps(json_data), encoding="utf-8")
    res = run_dataset(ds, k=2)
    assert res["n_questions"] == 1
    assert "single-session-user" in res["per_type"]
    assert 0.0 <= res["overall"]["recall_at_k"] <= 1.0


def test_run_dataset_records_embedding_model(tmp_path):
    # Results MUST be self-documenting: which embedding model produced them?
    # We hit exactly this gap — a saved 0.857 result with no model tag, so we
    # could not tell if it was e5 or the old model without re-running.
    import json

    from verimem.config import CONFIG
    ds = tmp_path / "mini.json"
    ds.write_text(json.dumps([{
        "question_id": "q1", "question_type": "single-session-user",
        "question": "x", "answer_session_ids": ["g1"],
        "haystack_session_ids": ["g1"],
        "haystack_sessions": [[{"role": "user", "content": "hello world"}]],
    }]), encoding="utf-8")
    res = run_dataset(ds, k=1)
    assert res["embedding_model"] == CONFIG.embedding_model
    assert res["embedding_dim"] == CONFIG.embedding_dim
