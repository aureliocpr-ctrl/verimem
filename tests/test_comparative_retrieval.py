"""Comparative bench harness (Engram vs vanilla RAG): wiring correctness.

The harness must be trustworthy before its numbers are: identical ingest
per arm, a vanilla baseline that actually ranks by cosine, the engram arm
flipping the rerank flag per-call, and aggregation keyed by arm.
"""
from __future__ import annotations

from benchmark.comparative_retrieval import (
    ARMS,
    VanillaRAG,
    eval_question_arms,
)


def _question() -> dict:
    return {
        "question_id": "q1",
        "question_type": "single-session-user",
        "question": "where does the production database live",
        "haystack_session_ids": ["s-gold", "s-noise1", "s-noise2"],
        "haystack_sessions": [
            [{"role": "user",
              "content": "the production database lives in eu-west-1"}],
            [{"role": "user",
              "content": "carbonara needs guanciale eggs pecorino pepper"}],
            [{"role": "user",
              "content": "the dream stage consolidates skills at night"}],
        ],
        "answer_session_ids": ["s-gold"],
    }


def test_vanilla_ranks_gold_first():
    rag = VanillaRAG()
    q = _question()
    for sid, sess in zip(q["haystack_session_ids"], q["haystack_sessions"],
                         strict=True):
        rag.store(sid, sess[0]["content"])
    out = rag.retrieve(q["question"], k=3)
    assert out[0] == "s-gold", f"cosine must rank the gold session first: {out}"
    assert len(out) == 3


def test_vanilla_k_caps_results():
    rag = VanillaRAG()
    for i in range(5):
        rag.store(f"s{i}", f"document number {i} about topic {i}")
    assert len(rag.retrieve("topic", k=2)) == 2
    assert rag.retrieve("anything", k=0) == []


def test_empty_vanilla_returns_empty():
    assert VanillaRAG().retrieve("query", k=5) == []


def test_eval_question_runs_all_arms(tmp_path):
    res = eval_question_arms(_question(), k=3, workdir=tmp_path)
    assert set(res["arms"]) == set(ARMS)
    for arm, m in res["arms"].items():
        assert m["recall_at_k"] is not None, arm
        assert 0.0 <= m["recall_at_k"] <= 1.0
        assert m["latency_ms"] >= 0
    # On this trivial corpus every arm must find the gold session.
    for arm in ARMS:
        assert res["arms"][arm]["hit_at_k"] == 1.0, (
            f"{arm} failed a 3-doc sanity corpus: {res['arms'][arm]}"
        )


def test_arm_subset_respected(tmp_path):
    res = eval_question_arms(_question(), k=3, workdir=tmp_path,
                             arms=("vanilla",))
    assert set(res["arms"]) == {"vanilla"}
